# nifty-satvik

## Dependency map maintenance

After editing any `nq/**` module or root `config.py`, regenerate the import map and
commit the result:

```
python scripts/gen_depgraph.py
```

This rewrites [docs/DEPENDENCY_MAP.md](docs/DEPENDENCY_MAP.md) (a Mermaid graph of
first-party `nq/` ↔ `config` wiring). The regenerator is stdlib-only and deterministic,
so re-running produces byte-identical output. A committed pre-commit hook in `.githooks/`
does this automatically when `core.hooksPath` is set — enable once per clone with:

```
git config core.hooksPath .githooks
```
