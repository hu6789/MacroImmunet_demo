# cell_master/owner_utils.py
"""
OwnerUtils: helper wrapper for claiming/transferring/releasing ownership of labels.

Design:
 - Prefer feedback.apply_claim/claim_label/transfer_label/release_label if available.
 - Fall back to space-level APIs (claim_label, set_label_owner) if present.
 - Last-resort: mutate label dict obtained via space.get_label / space.get_labels and attempt to write back
   via space.update_label or space.set_label_owner if available.
 - Always returns a dict:
     {
       "ok": bool,
       "prev_owner": <owner or None>,
       "new_owner": <owner or None>,
       "action": "claim"/"transfer"/"release",
       "detail": "human-readable explanation"
     }
 - Defensive: never raise; on exception include detail.
"""

from typing import Any, Dict, Optional
import traceback

class OwnerUtils:
    def __init__(self, space: Any, feedback: Optional[Any] = None, verbose: bool = False):
        self.space = space
        self.feedback = feedback
        self.verbose = verbose

    def _fetch_label(self, label_id: str) -> Optional[Dict[str, Any]]:
        """Try common ways to fetch a label by id."""
        try:
            # prefer direct space.get_label
            if hasattr(self.space, "get_label"):
                return self.space.get_label(label_id)
        except Exception:
            if self.verbose:
                traceback.print_exc()
        try:
            # fallback: many spaces expose get_labels(region) only; try scanning if available
            if hasattr(self.space, "get_all_labels") and callable(self.space.get_all_labels):
                for l in self.space.get_all_labels() or []:
                    if l.get("id") == label_id:
                        return l
        except Exception:
            if self.verbose:
                traceback.print_exc()
        # last resort: try get_labels(None) or get_labels with region unknown
        try:
            if hasattr(self.space, "get_labels"):
                # try calling without region or with common region names isn't reliable;
                # so try both calling with None and without args
                try:
                    vals = self.space.get_labels(None)
                except TypeError:
                    vals = self.space.get_labels()
                for l in vals or []:
                    if l.get("id") == label_id:
                        return l
        except Exception:
            if self.verbose:
                traceback.print_exc()
        return None

    def get_owner(self, label_id: str) -> Optional[str]:
        """Return current owner if available (or None)."""
        try:
            # try feedback first
            if self.feedback is not None and hasattr(self.feedback, "get_label_owner"):
                return self.feedback.get_label_owner(label_id)
        except Exception:
            if self.verbose:
                traceback.print_exc()
        try:
            if hasattr(self.space, "get_label_owner"):
                return self.space.get_label_owner(label_id)
        except Exception:
            if self.verbose:
                traceback.print_exc()
        # fallback: fetch label and inspect owner key
        lbl = self._fetch_label(label_id)
        if lbl is None:
            return None
        return lbl.get("owner") or lbl.get("claimed_by") or None

    def claim(self, label_id: str, owner_id: str) -> Dict[str, Any]:
        """
        Attempt to claim `label_id` for `owner_id`.
        Returns standardized result dict.
        """
        res = {"action": "claim", "label_id": label_id, "requested_owner": owner_id, "prev_owner": None, "new_owner": None, "ok": False, "detail": ""}
        try:
            # 1) feedback-level atomic claim
            if self.feedback is not None and hasattr(self.feedback, "claim_label"):
                ok = self.feedback.claim_label(label_id, owner_id)
                prev = self.get_owner(label_id)
                res.update({"ok": bool(ok), "prev_owner": prev, "new_owner": owner_id if ok else prev, "detail": "feedback.claim_label"})
                return res
        except Exception:
            if self.verbose:
                traceback.print_exc()

        # 2) space-level atomic claim
        try:
            if hasattr(self.space, "claim_label"):
                ok = self.space.claim_label(label_id, owner_id)
                prev = self.get_owner(label_id)
                res.update({"ok": bool(ok), "prev_owner": prev, "new_owner": owner_id if ok else prev, "detail": "space.claim_label"})
                return res
        except Exception:
            if self.verbose:
                traceback.print_exc()

        # 3) best-effort: fetch label, set owner if None
        try:
            lbl = self._fetch_label(label_id)
            prev_owner = lbl.get("owner") if lbl else None
            res["prev_owner"] = prev_owner
            if prev_owner:
                res["ok"] = False
                res["new_owner"] = prev_owner
                res["detail"] = "already owned"
                return res
            # try to write owner back
            success = False
            # try feedback.set_label_owner
            if self.feedback is not None and hasattr(self.feedback, "set_label_owner"):
                try:
                    self.feedback.set_label_owner(label_id, owner_id)
                    success = True
                except Exception:
                    if self.verbose:
                        traceback.print_exc()
            # try space.set_label_owner
            if not success and hasattr(self.space, "set_label_owner"):
                try:
                    self.space.set_label_owner(label_id, owner_id)
                    success = True
                except Exception:
                    if self.verbose:
                        traceback.print_exc()
            # try space.update_label by mutating fetched label and pushing back
            if not success and lbl is not None and hasattr(self.space, "update_label"):
                try:
                    newlbl = dict(lbl)
                    newlbl["owner"] = owner_id
                    self.space.update_label(newlbl)
                    success = True
                except Exception:
                    if self.verbose:
                        traceback.print_exc()
            if success:
                res["ok"] = True
                res["new_owner"] = owner_id
                res["detail"] = "set via fallback update"
                return res
            res["ok"] = False
            res["detail"] = "no claim API available and fallback failed"
            res["new_owner"] = prev_owner
            return res
        except Exception as e:
            if self.verbose:
                traceback.print_exc()
            res["ok"] = False
            res["detail"] = f"exception: {str(e)}"
            return res

    def transfer(self, label_id: str, new_owner: str, force: bool = False) -> Dict[str, Any]:
        """
        Transfer ownership to new_owner. If force==False, attempt to respect existing owner.
        """
        res = {"action": "transfer", "label_id": label_id, "requested_owner": new_owner, "prev_owner": None, "new_owner": None, "ok": False, "detail": ""}
        try:
            # feedback-level transfer
            if self.feedback is not None and hasattr(self.feedback, "transfer_label"):
                ok = self.feedback.transfer_label(label_id, new_owner, force=force)
                prev = self.get_owner(label_id)
                res.update({"ok": bool(ok), "prev_owner": prev, "new_owner": new_owner if ok else prev, "detail": "feedback.transfer_label"})
                return res
        except Exception:
            if self.verbose:
                traceback.print_exc()

        # space-level transfer
        try:
            if hasattr(self.space, "transfer_label"):
                ok = self.space.transfer_label(label_id, new_owner, force=force)
                prev = self.get_owner(label_id)
                res.update({"ok": bool(ok), "prev_owner": prev, "new_owner": new_owner if ok else prev, "detail": "space.transfer_label"})
                return res
        except Exception:
            if self.verbose:
                traceback.print_exc()

        # fallback: set owner unconditionally if force, else require previous owner None
        try:
            lbl = self._fetch_label(label_id)
            prev = lbl.get("owner") if lbl else None
            res["prev_owner"] = prev
            if prev and not force:
                res.update({"ok": False, "new_owner": prev, "detail": "owned and force==False"})
                return res
            # try setting via feedback/space setters
            success = False
            if self.feedback is not None and hasattr(self.feedback, "set_label_owner"):
                try:
                    self.feedback.set_label_owner(label_id, new_owner)
                    success = True
                except Exception:
                    if self.verbose:
                        traceback.print_exc()
            if not success and hasattr(self.space, "set_label_owner"):
                try:
                    self.space.set_label_owner(label_id, new_owner)
                    success = True
                except Exception:
                    if self.verbose:
                        traceback.print_exc()
            if not success and lbl is not None and hasattr(self.space, "update_label"):
                try:
                    nl = dict(lbl)
                    nl["owner"] = new_owner
                    self.space.update_label(nl)
                    success = True
                except Exception:
                    if self.verbose:
                        traceback.print_exc()
            if success:
                res.update({"ok": True, "new_owner": new_owner, "detail": "transferred via fallback setter"})
                return res
            res.update({"ok": False, "new_owner": prev, "detail": "no transfer API available and fallback failed"})
            return res
        except Exception as e:
            if self.verbose:
                traceback.print_exc()
            res.update({"ok": False, "detail": f"exception: {str(e)}"})
            return res

    def release(self, label_id: str, owner_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Release a claim. If owner_id provided, only release when it matches (best-effort).
        """
        res = {"action": "release", "label_id": label_id, "owner_id": owner_id, "prev_owner": None, "new_owner": None, "ok": False, "detail": ""}
        try:
            # try feedback.release_label
            if self.feedback is not None and hasattr(self.feedback, "release_label"):
                ok = self.feedback.release_label(label_id, owner_id)
                prev = self.get_owner(label_id)
                res.update({"ok": bool(ok), "prev_owner": prev, "new_owner": None if ok else prev, "detail": "feedback.release_label"})
                return res
        except Exception:
            if self.verbose:
                traceback.print_exc()
        # space-level
        try:
            if hasattr(self.space, "release_label"):
                ok = self.space.release_label(label_id, owner_id)
                prev = self.get_owner(label_id)
                res.update({"ok": bool(ok), "prev_owner": prev, "new_owner": None if ok else prev, "detail": "space.release_label"})
                return res
        except Exception:
            if self.verbose:
                traceback.print_exc()

        # fallback: fetch label and set owner to None if matches (or unconditional)
        try:
            lbl = self._fetch_label(label_id)
            prev = lbl.get("owner") if lbl else None
            res["prev_owner"] = prev
            if prev is None:
                res.update({"ok": True, "new_owner": None, "detail": "already free"})
                return res
            if owner_id is not None and prev != owner_id:
                res.update({"ok": False, "new_owner": prev, "detail": "owner mismatch; not releasing"})
                return res
            # attempt to clear
            success = False
            if self.feedback is not None and hasattr(self.feedback, "set_label_owner"):
                try:
                    self.feedback.set_label_owner(label_id, None)
                    success = True
                except Exception:
                    if self.verbose:
                        traceback.print_exc()
            if not success and hasattr(self.space, "set_label_owner"):
                try:
                    self.space.set_label_owner(label_id, None)
                    success = True
                except Exception:
                    if self.verbose:
                        traceback.print_exc()
            if not success and lbl is not None and hasattr(self.space, "update_label"):
                try:
                    nl = dict(lbl)
                    nl["owner"] = None
                    self.space.update_label(nl)
                    success = True
                except Exception:
                    if self.verbose:
                        traceback.print_exc()
            if success:
                res.update({"ok": True, "new_owner": None, "detail": "released via fallback setter"})
                return res
            res.update({"ok": False, "new_owner": prev, "detail": "no release API and fallback failed"})
            return res
        except Exception as e:
            if self.verbose:
                traceback.print_exc()
            res.update({"ok": False, "detail": f"exception: {str(e)}"})
            return res

