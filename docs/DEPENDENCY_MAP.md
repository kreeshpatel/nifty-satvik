# nq dependency map

First-party module wiring of the `nq/` package (+ root `config.py`).
Granularity: **sub-package**. Edges point from importer to imported.

> Collapsed to sub-package granularity (file-level graph exceeded 40 nodes).

_Auto-generated — do not edit by hand._
regenerate with: `python scripts/gen_depgraph.py`

```mermaid
flowchart LR
    config["config"]
    nq_brain["nq/brain"]
    nq_data["nq/data"]
    nq_engine["nq/engine"]
    nq_lab["nq/lab"]
    nq_paper["nq/paper"]
    nq_research["nq/research"]
    nq_runner["nq/runner"]
    nq_strategy["nq/strategy"]
    nq_validation["nq/validation"]
    nq_brain --> nq_paper
    nq_data --> config
    nq_engine --> config
    nq_engine --> nq_data
    nq_lab --> nq_brain
    nq_lab --> nq_data
    nq_lab --> nq_runner
    nq_lab --> nq_validation
    nq_paper --> config
    nq_paper --> nq_engine
    nq_paper --> nq_research
    nq_research --> config
    nq_runner --> config
    nq_runner --> nq_data
    nq_runner --> nq_engine
    nq_runner --> nq_strategy
    nq_runner --> nq_validation
    nq_strategy --> config
    nq_strategy --> nq_data
    nq_strategy --> nq_engine
    nq_validation --> config
```
