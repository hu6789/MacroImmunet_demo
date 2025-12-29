MacroImmunet_demo — Phase 1 (Label Center)

Research demo: a semantically explicit immune orchestration layer (Label Center) + minimal Scan/Cell orches辑 for integration tests.

Status: v0.1.0-alpha (Phase 1 complete — Label Center frozen)

One-liner

MacroImmunet_demo implements a transaction-consistent, ownership-aware Label Center for spatial immune simulation and a lightweight Scan/Cell orchestration scaffold — designed as a stable infra layer for plugin-driven decision modules.

What’s in this repo (short)

label_center/ — LabelCenterBase and API (transactional field, ownership, cooldown/hysteresis, deterministic conflict arbitration). Frozen semantics for Phase 1.

scan_master/ — Scan and node generation logic (default implementations).

cell_master/ — CellMaster scaffold, behaviour library (reference implementations).

test/ — Extensive pytest suite verifying Phase1 semantics (Step1–5.14).

tools/, demo scripts and small utilities.

Phase 1 — Completed (what we verified)

Phase 1 focused on building a stable, test-locked Label Center and proving its semantics.

Completed and tested items (key highlights):

Tick-level transaction semantics (Step5.12)

Writes (intents) are staged and only become visible after apply()/tick boundary.

Reads inside a tick are snapshot-consistent.

Ownership & cooldown (Step5.7 / Step5.13)

claim / release semantics.

claim_cooldown prevents immediate re-claim; same-tick reclaims are disallowed.

Hysteresis / anti-thrashing (Step5.13)

Labels cannot oscillate across adjacent ticks; pruning and re-emission follow time-gated rules.

Deterministic conflict arbitration (Step5.14)

Same-tick conflicting claims resolved deterministically (first-come wins).

Owned labels prevent library emits; release does not retroactively change same-tick outcomes.

Field label lifecycle

Emission, merging, decay, prune rules verified (Step5.8, Step5.9).

Test coverage

Tests for Step5.1 → Step5.14 in test/ assert the above semantics.

Result: Label Center is now a reliable infra layer — behavior is specified by tests and can be safely depended on by higher layers.

What Phase 1 does not provide (current limitations)

No high-fidelity per-cell ODE/kinetics (PerCell engine is scaffolded but not implemented).

Behaviour library is a reference set — intended to be replaced by plugin-backed InternalNet in Phase 2.

Antibody/B-cell dynamics are not modelled beyond a placeholder API; antibody is currently planned as a field-level effect.

SIO/HIR (macro controllers) are not implemented — only the contract is defined.

No GUI / visualization beyond textual demos.

These are deliberate choices: Phase 1 froze semantics before adding complexity.

Roadmap (Phase 2 — integration & pluginization)

Planned high-level steps (Phase 2, Phase 3 follow):

Phase 2 (integration):

Introduce plugin contracts (InternalNet, PerCellEngine, VirusSkill, pMHC, AntibodyEffect, TherapeuticAgent, SIO/HIR).

Provide PluginBase and NullPlugin placeholders; allow pluggable decision layers.

Integration tests: Scan → Cell → LabelCenter workflows; plugin registration & invocation tests.

Phase 3 (extensions & models):

Concrete InternalNet implementations, PerCell ODE-based engines.

Antigen / virus skill library and drug intervention modules.

B-cell & antibody module (field-level antibody models + simple kinetics).

SIO/HIR policy modules and simple demonstration strategies.

Quick start (for developers)
# setup (python 3.8+)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt    # (create as needed)

# run unit tests
python3 -m pytest test/test_step5_12_apply_commits_atomically.py
# or run full test suite
python3 -m pytest -q

Useful commands (git & release)

Tagging release:

git add .
git commit -m "Phase1: freeze LabelCenter semantics, add plugin contracts"
git tag -a v0.1.0-alpha -m "LabelCenter frozen; Phase1 complete"
git push origin main --tags


Suggested release title: v0.1.0-alpha — LabelCenter frozen (Phase 1 complete)

Release description: use the “Phase 1 — Completed” plus “Roadmap” section above (shortened).

Contributing & code of conduct

Please open issues / PRs against main.

Tests must accompany any change that affects LabelCenter semantics.

If you propose a refactor to LabelCenter internals, the external semantics must stay unchanged (tests should be updated/kept).

Files to check first

label_center/label_center_base.py — core semantics

label_center/label_center.py — orchestration / intent apply

test/ — tests that assert the guarantees

License & attribution

We recommend MIT for research demo permissiveness — include LICENSE if you agree.

Release notes (text for GitHub Release)

Title: v0.1.0-alpha — LabelCenter frozen (Phase 1 complete)

Body:
Phase 1 complete: LabelCenter semantics frozen. This release provides a transaction-consistent, ownership-aware Label Center for spatial immunological orchestration, along with Scan/Cell scaffolding and a comprehensive test suite (Steps 5.1–5.14). Phase 2 will introduce plugin contracts (InternalNet, PerCellEngine, VirusSkill, pMHC, AntibodyEffect, TherapeuticAgent, SIO/HIR) to allow pluggable decision & effect layers.

Short social / project blurb 

MacroImmunet_demo v0.1.0-alpha: Phase 1 complete — a transactionally consistent, ownership-aware Label Center for immune orchestration. We’ve frozen semantics (tick atomicity, ownership, hysteresis, deterministic arbitration) and prepared plugin contracts for Phase 2. Repo: <your-repo-url> — PRs and collaborators welcome!

Recommended additional docs to include in repo

freeze_readme.md (short legal-style semantics snapshot — you already have freeze_readme)

docs/plugins.md — plugin spec (base classes + Null implementations)

CONTRIBUTING.md & CODE_OF_CONDUCT.md


small EXAMPLES.md showing simple run commands and demo flows

Note: Some inline comments are bilingual due to development environment constraints during early prototyping.
Some refactoring and consistency checks were assisted by an AI-based coding assistant.
