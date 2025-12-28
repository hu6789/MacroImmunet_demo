# cell_master/gene_gate.py
"""
GeneGate: demo-friendly gene gating utility.

Provides:
 - class GeneGate(...) with methods allow, batch_filter, sample_fraction
 - module-level convenience wrappers: evaluate_cell, evaluate_batch, sample_fraction

Robust custom_pred handling:
 - tries multiple plausible call signatures (cell,obj / meta-dict / with node_meta / no-arg)
 - accepts bool or (bool, details) returns
 - continues trying other signatures when a call raises (don't treat non-TypeError exceptions as final failure)
"""
from typing import Any, Dict, List, Optional, Tuple
import random

def _as_meta(cell_or_meta: Optional[Any]) -> Dict[str, Any]:
    if cell_or_meta is None:
        return {}
    if isinstance(cell_or_meta, dict):
        mm = cell_or_meta.get("meta")
        if isinstance(mm, dict):
            return dict(mm)
        return dict(cell_or_meta)
    try:
        mm = getattr(cell_or_meta, "meta", None)
        if isinstance(mm, dict):
            return dict(mm)
    except Exception:
        pass
    try:
        if hasattr(cell_or_meta, "__dict__"):
            return dict(vars(cell_or_meta))
    except Exception:
        pass
    return {}

def _try_float(v):
    try:
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        return float(str(v))
    except Exception:
        return None

class GeneGate:
    def __init__(self, genotype_or_config: Optional[Any] = None, seed: Optional[Any] = None):
        # Accept either a config dict or a seed scalar as first arg.
        if isinstance(genotype_or_config, dict):
            self.config: Dict[str, Any] = dict(genotype_or_config)
            if seed is None and "seed" in self.config:
                seed = self.config.get("seed")
        elif genotype_or_config is None:
            self.config = {}
        else:
            # scalar passed as first arg -> treat as seed
            self.config = {}
            if seed is None:
                seed = genotype_or_config

        # avoid unhashable seeds
        if isinstance(seed, (dict, list, set)):
            seed = None
        try:
            self._rng = random.Random(seed)
        except Exception:
            self._rng = random.Random()

    def allow(self, cell_or_meta: Optional[Any], node_meta: Optional[Dict[str, Any]]) -> Tuple[bool, Dict[str, Any]]:
        node_meta = node_meta or {}
        cell_meta = _as_meta(cell_or_meta)

        # required genes
        req = node_meta.get("required_genes") or node_meta.get("require_genes")
        if req:
            for g in (req or []):
                if not self._has_gene(cell_meta, g):
                    return False, {"reason": "missing_required_gene", "gene": g}

        # forbidden genes
        forb = node_meta.get("forbidden_genes")
        if forb:
            for g in (forb or []):
                if self._has_gene(cell_meta, g):
                    return False, {"reason": "forbidden_gene_present", "gene": g}

        # min_expression: mapping key->threshold
        mex = node_meta.get("min_expression")
        if isinstance(mex, dict):
            for k, thr in mex.items():
                try:
                    val = float(cell_meta.get(k, 0.0) or 0.0)
                    if val < float(thr):
                        return False, {"reason": "min_expression_failed", "key": k, "value": val, "threshold": thr}
                except Exception:
                    return False, {"reason": "min_expression_eval_error", "key": k}

        # custom predicate callable -- robust calling
        custom = node_meta.get("custom_pred")
        if custom and callable(custom):
            # Try several plausible invocation styles in this order:
            # 1) (cell_obj, node_meta)      -- most explicit, nice for object-style custom preds
            # 2) (cell_obj,)                -- simple object-only pred
            # 3) (cell_meta, node_meta)     -- dict-style pred expecting meta dict + node_meta
            # 4) (cell_meta,)               -- dict-style only
            # 5) (node_meta,)               -- node_meta-only
            # 6) ()                         -- zero-arg pred
            # Each attempt: if call succeeds, examine result:
            #   - if bool -> use truthiness
            #   - if (bool, details) tuple -> use bool part
            # If call raises or returns None/False, try next signature.
            call_signatures = [
                ( (cell_or_meta, node_meta), {} ),
                ( (cell_or_meta,), {} ),
                ( (cell_meta, node_meta), {} ),
                ( (cell_meta,), {} ),
                ( (node_meta,), {} ),
                ( (), {} ),
            ]
            last_exc = None
            passed = False
            details = None
            for args, kwargs in call_signatures:
                try:
                    res = custom(*args, **kwargs)
                    # allow (bool, details) pattern
                    if isinstance(res, tuple) and len(res) >= 1:
                        ok = bool(res[0])
                        det = res[1] if len(res) > 1 else None
                        if ok:
                            passed = True
                            details = det if det is not None else {"info": "custom_pred_true"}
                            break
                        else:
                            # explicitly False -> not allowed
                            passed = False
                            details = det if det is not None else {"info": "custom_pred_false"}
                            break
                    else:
                        # non-tuple: interpret truthiness
                        if bool(res):
                            passed = True
                            details = {"info": "custom_pred_truthy", "value": res}
                            break
                        else:
                            # returned falsy -> treat as fail for this signature but try others
                            last_exc = None
                            continue
                except TypeError as te:
                    # signature mismatch; try next
                    last_exc = te
                    continue
                except Exception as e:
                    # predicate raised; record and try next signature (do not immediately fail)
                    last_exc = e
                    continue

            if not passed:
                # if any attempt produced an explicit details (e.g., custom returned False tuple) prefer that
                if isinstance(details, dict):
                    return False, {"reason": "custom_pred_failed", "details": details}
                # otherwise provide signature mismatch / last exception
                return False, {"reason": "custom_pred_no_signature_matched", "error": str(last_exc) if last_exc else None}

        # probabilistic allow
        prob = node_meta.get("allow_probability")
        if prob is not None:
            try:
                p = float(prob)
                if p < 1.0:
                    if self._rng.random() >= p:
                        return False, {"reason": "probabilistic_block", "prob": p}
            except Exception:
                pass

        return True, {"reason": "allowed"}

    def batch_filter(self, items: List[Any], node_meta: Optional[Dict[str, Any]] = None) -> List[Any]:
        """
        Optionally filter items list according to node_meta keys.
        - Supports older filter_key/filter_min/filter_max pattern.
        - Also supports 'min_expression': {key: threshold, ...}
        - Also honors 'required_genes' and 'forbidden_genes' for batch-level gating.
        Keeps items without the inspected key (conservative).
        """
        node_meta = node_meta or {}

        # quick passthrough
        if not items:
            return []

        out = []

        # helper to decide per-item
        def item_passes(it) -> bool:
            try:
                # normalize meta for the item
                meta = _as_meta(it)

                # required / forbidden genes at batch level
                req = node_meta.get("required_genes") or node_meta.get("require_genes")
                if req:
                    for g in req:
                        if not self._has_gene(meta, g):
                            return False

                forb = node_meta.get("forbidden_genes")
                if forb:
                    for g in forb:
                        if self._has_gene(meta, g):
                            return False

                # min_expression mapping (key -> threshold)
                mex = node_meta.get("min_expression")
                if isinstance(mex, dict):
                    for k, thr in mex.items():
                        try:
                            val = float(meta.get(k, 0.0) or 0.0)
                            if val < float(thr):
                                return False
                        except Exception:
                            # if we can't evaluate, be conservative and treat as failing
                            return False

                # legacy pattern: filter_key / filter_min / filter_max
                fk = node_meta.get("filter_key")
                fmin = node_meta.get("filter_min")
                fmax = node_meta.get("filter_max")
                if fk and (fmin is not None or fmax is not None):
                    # try top-level then meta
                    v = None
                    if isinstance(it, dict):
                        v = it.get(fk, None)
                        if v is None:
                            v = (it.get("meta") or {}).get(fk)
                    else:
                        meta2 = getattr(it, "meta", {}) or {}
                        v = meta2.get(fk, None) if isinstance(meta2, dict) else getattr(it, fk, None)
                    if v is not None:
                        try:
                            vf = float(v)
                            if fmin is not None and vf < float(fmin):
                                return False
                            if fmax is not None and vf > float(fmax):
                                return False
                        except Exception:
                            # parsing error -> keep item (conservative)
                            pass

                return True
            except Exception:
                # on unexpected error keep the item (don't drop silently)
                return True

        for it in items:
            if item_passes(it):
                out.append(it)

        return out


    def sample_fraction(self, items: List[Any], fraction: float = 1.0, rng: Optional[random.Random] = None, max_select: Optional[int] = None) -> List[Any]:
        if not items:
            return []
        rng = rng or self._rng or random.Random()
        n = len(items)
        try:
            f = float(fraction)
        except Exception:
            f = 1.0

        if f < 0:
            k = 0
        elif f < 1.0:
            k = int(round(n * f))
        else:
            if abs(f - 1.0) < 1e-9:
                k = n
            else:
                k = int(round(f))

        if k < 0:
            k = 0
        if k > n:
            k = n

        if max_select is not None:
            try:
                cap = int(max_select)
                if cap < k:
                    k = max(0, cap)
            except Exception:
                pass

        if k <= 0:
            return []

        if k >= n:
            return list(items)

        try:
            return rng.sample(list(items), k)
        except Exception:
            tmp = list(items)
            rng.shuffle(tmp)
            return tmp[:k]

    def _has_gene(self, cell_meta: Dict[str, Any], gene_name: str) -> bool:
        if not cell_meta:
            return False
        try:
            if gene_name in cell_meta:
                return bool(cell_meta.get(gene_name))
            nested = cell_meta.get("genes") or {}
            if isinstance(nested, dict) and gene_name in nested:
                return bool(nested.get(gene_name))
        except Exception:
            return False
        return False

# module-level convenience
_default_gate = GeneGate({})

def evaluate_cell(cell_like: Optional[Any], node_meta: Optional[Dict[str, Any]]) -> Tuple[bool, Dict[str, Any]]:
    ok, details = _default_gate.allow(cell_like, node_meta or {})
    if not isinstance(details, dict):
        details = {"info": details}
    return bool(ok), dict(details)

def evaluate_batch(items: List[Any], node_meta: Optional[Dict[str, Any]] = None) -> List[Any]:
    return _default_gate.batch_filter(items or [], node_meta or {})

# --- ADD THESE WRAPPERS to satisfy tests that call gene_gate.batch_filter / gene_gate.sample_fraction directly ---
def batch_filter(items: List[Any], node_meta: Optional[Dict[str, Any]] = None) -> List[Any]:
    """
    Module-level wrapper to filter a list of items using the default gate.
    Kept for backwards compatibility with older tests/code that call gene_gate.batch_filter(...)
    """
    return _default_gate.batch_filter(items or [], node_meta or {})

def sample_fraction(items: List[Any], fraction: float = 1.0, rng: Optional[random.Random] = None, max_select: Optional[int] = None) -> List[Any]:
    """
    Module-level sampling convenience that delegates to default gate.
    (kept for backward compatibility)
    """
    return _default_gate.sample_fraction(items or [], fraction=fraction, rng=rng, max_select=max_select)

# Export names (make sure these names include the wrappers)
__all__ = [
    "GeneGate",
    "evaluate_cell",
    "evaluate_batch",
    "batch_filter",
    "sample_fraction",
]

