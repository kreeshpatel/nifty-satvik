# nq dependency map

First-party module wiring of the `nq/` package (+ root `config.py`).
Granularity: **file-module**. Edges point from importer to imported.

_Auto-generated — do not edit by hand._
regenerate with: `python scripts/gen_depgraph.py`

```mermaid
flowchart LR
    config["config"]
    nq_data["nq/data"]
    nq_data_eligibility["nq/data/eligibility"]
    nq_data_features["nq/data/features"]
    nq_data_fundamentals["nq/data/fundamentals"]
    nq_data_membership["nq/data/membership"]
    nq_data_ohlcv["nq/data/ohlcv"]
    nq_engine["nq/engine"]
    nq_engine_exits["nq/engine/exits"]
    nq_engine_panel["nq/engine/panel"]
    nq_engine_portfolio["nq/engine/portfolio"]
    nq_paper_book["nq/paper/book"]
    nq_paper_forward_wall["nq/paper/forward_wall"]
    nq_paper_forward_wall_job["nq/paper/forward_wall_job"]
    nq_paper_wall_cron["nq/paper/wall_cron"]
    nq_research_conviction["nq/research/conviction"]
    nq_research_residual["nq/research/residual"]
    nq_runner["nq/runner"]
    nq_runner_research["nq/runner/research"]
    nq_runner_scan["nq/runner/scan"]
    nq_strategy["nq/strategy"]
    nq_strategy_long_horizon["nq/strategy/long_horizon"]
    nq_validation["nq/validation"]
    nq_validation_bootstrap["nq/validation/bootstrap"]
    nq_validation_cpcv["nq/validation/cpcv"]
    nq_validation_dsr["nq/validation/dsr"]
    nq_validation_metrics["nq/validation/metrics"]
    nq_data --> nq_data_eligibility
    nq_data --> nq_data_features
    nq_data --> nq_data_fundamentals
    nq_data --> nq_data_membership
    nq_data --> nq_data_ohlcv
    nq_data_eligibility --> config
    nq_data_features --> config
    nq_data_features --> nq_data_ohlcv
    nq_data_fundamentals --> config
    nq_data_membership --> config
    nq_data_ohlcv --> config
    nq_engine --> nq_engine_exits
    nq_engine --> nq_engine_panel
    nq_engine --> nq_engine_portfolio
    nq_engine_panel --> config
    nq_engine_panel --> nq_data_eligibility
    nq_engine_panel --> nq_data_features
    nq_engine_panel --> nq_data_fundamentals
    nq_engine_panel --> nq_data_membership
    nq_engine_panel --> nq_data_ohlcv
    nq_engine_portfolio --> config
    nq_engine_portfolio --> nq_engine_exits
    nq_paper_book --> nq_engine_exits
    nq_paper_book --> nq_engine_portfolio
    nq_paper_forward_wall --> config
    nq_paper_forward_wall_job --> config
    nq_paper_forward_wall_job --> nq_paper_forward_wall
    nq_paper_wall_cron --> config
    nq_paper_wall_cron --> nq_paper_book
    nq_paper_wall_cron --> nq_paper_forward_wall
    nq_paper_wall_cron --> nq_paper_forward_wall_job
    nq_paper_wall_cron --> nq_research_residual
    nq_research_conviction --> config
    nq_runner --> nq_runner_research
    nq_runner --> nq_runner_scan
    nq_runner_research --> nq_engine_portfolio
    nq_runner_research --> nq_validation_bootstrap
    nq_runner_research --> nq_validation_dsr
    nq_runner_research --> nq_validation_metrics
    nq_runner_scan --> config
    nq_runner_scan --> nq_data_features
    nq_runner_scan --> nq_data_fundamentals
    nq_runner_scan --> nq_data_membership
    nq_runner_scan --> nq_data_ohlcv
    nq_runner_scan --> nq_engine_panel
    nq_runner_scan --> nq_strategy_long_horizon
    nq_strategy --> nq_strategy_long_horizon
    nq_strategy_long_horizon --> config
    nq_strategy_long_horizon --> nq_data_features
    nq_strategy_long_horizon --> nq_engine_portfolio
    nq_validation --> nq_validation_bootstrap
    nq_validation --> nq_validation_cpcv
    nq_validation --> nq_validation_dsr
    nq_validation --> nq_validation_metrics
    nq_validation_dsr --> config
```
