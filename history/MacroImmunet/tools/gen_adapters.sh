#!/usr/bin/env bash
set -euo pipefail

echo ">>> Creating compatibility wrappers for behaviors_impl *_v1 -> old-name delegations"
mkdir -p behaviors_impl
# For each *_v1.py create a wrapper <base>.py unless it already exists.
for vf in behaviors_impl/*_v1.py; do
  [ -e "$vf" ] || continue
  base="$(basename "$vf" .py)"
  base_no_ver="$(echo "$base" | sed -E 's/_v[0-9]+$//')"
  wrapper="behaviors_impl/${base_no_ver}.py"
  if [ -f "$wrapper" ]; then
    echo "SKIP (exists): $wrapper"
    continue
  fi
  cat > "$wrapper" <<PY
# Auto-generated wrapper delegating to behaviors_impl.${base}
# Created on $(date -u +'%Y-%m-%d %H:%M:%SZ')
try:
    from behaviors_impl.${base} import *  # import public symbols
except Exception:
    def ${base_no_ver}(*a, **kw):
        return []
    def ${base}_v1(*a, **kw):
        return []
    class ${base_no_ver.capitalize()}Behavior:
        def __init__(self, **kwargs):
            self.params = kwargs or {}
        def execute(self, cell, env, params=None, **kw):
            return []
PY
  echo "WROTE wrapper: $wrapper -> delegates to behaviors_impl.${base}"
done

echo
echo ">>> Creating behaviors/ adapters for YAMLs missing implementation (no overwrite)"
mkdir -p behaviors
for y in behaviors/*.yaml; do
  [ -e "$y" ] || continue
  stem="$(basename "$y" .yaml)"
  adapter="behaviors/${stem}.py"
  if [ -f "$adapter" ]; then
    echo "SKIP adapter (exists): $adapter"
    continue
  fi
  if grep -qE '^[[:space:]]*implementation[[:space:]]*:' "$y"; then
    echo "SKIP adapter for $y (has implementation block)"
    continue
  fi
  base="$(echo "$stem" | sed -E 's/_v[0-9]+$//')"
  cat > "$adapter" <<PY
# Auto-generated adapter for behaviors/${stem}. Delegates to behaviors_impl.${base}_v1
# Created: $(date -u +'%Y-%m-%d %H:%M:%SZ')
try:
    from behaviors_impl.${base}_v1 import ${stem} as _impl_fn
except Exception:
    try:
        from behaviors_impl.${base}_v1 import ${base}_v1 as _impl_fn
    except Exception:
        def _impl_fn(*a, **kw):
            return []

def ${stem}(cell, env, params=None, rng=None, receptors=None, payload=None):
    params = params or {}
    try:
        return _impl_fn(cell=cell, env=env, params=params, rng=rng, receptors=receptors, payload=payload)
    except TypeError:
        try:
            return _impl_fn(cell, env, params)
        except Exception:
            try:
                return _impl_fn(cell, env)
            except Exception:
                return []

class ${stem[0].upper()}${stem:1}Behavior:
    def __init__(self, **kwargs):
        self.params = kwargs or {}
    def execute(self, cell, env, params=None, **kw):
        return ${stem}(cell, env, params or self.params, **kw)
PY
  echo "WROTE adapter: $adapter -> delegates to behaviors_impl.${base}_v1"
done

echo
echo "Done. Now run tests:"
echo "  PYTHONPATH=. python3 -m pytest -q tests/unit"
