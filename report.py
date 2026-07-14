import json
import shutil
from pathlib import Path

import pandas as pd

import config


ASSET_DIR = config.BASE_DIR / "docs" / "assets"


def _money(value):
    return f"${value:,.0f}"


def _pct(value):
    if abs(value) < 0.005:
        value = 0.0
    return f"{value:.2f}%"


def _copy_plot_assets():
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    copied = {}
    for plot_name in [
        "network_map.png",
        "cost_breakdown.png",
        "service_cost_tradeoff.png",
        "sensitivity_tornado.png",
        "cost_emissions_pareto.png",
    ]:
        source = config.PLOTS_DIR / plot_name
        target = ASSET_DIR / plot_name
        if source.exists():
            shutil.copy2(source, target)
            copied[plot_name] = f"docs/assets/{plot_name}"
    return copied


def _markdown_table(df, columns):
    table = df[columns].copy()
    rows = [[str(value) for value in row] for row in table.to_numpy()]
    header = [str(column) for column in columns]
    widths = [
        max(len(header[idx]), *(len(row[idx]) for row in rows)) if rows else len(header[idx])
        for idx in range(len(header))
    ]
    header_line = "| " + " | ".join(header[idx].ljust(widths[idx]) for idx in range(len(header))) + " |"
    sep_line = "| " + " | ".join("-" * widths[idx] for idx in range(len(header))) + " |"
    row_lines = [
        "| " + " | ".join(row[idx].ljust(widths[idx]) for idx in range(len(header))) + " |"
        for row in rows
    ]
    return "\n".join([header_line, sep_line, *row_lines])


def generate_project_report():
    metrics_path = config.RESULTS_DIR / "resume_metrics.json"
    if not metrics_path.exists():
        raise FileNotFoundError("Run main.py before generating the project report.")

    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    baseline = pd.read_csv(config.RESULTS_DIR / "baseline_comparison.csv")
    demand_shocks = pd.read_csv(config.RESULTS_DIR / "demand_shocks.csv")
    service_level = pd.read_csv(config.RESULTS_DIR / "service_level.csv")
    capacity = pd.read_csv(config.RESULTS_DIR / "capacity.csv")
    assets = _copy_plot_assets()

    baseline_view = baseline.assign(
        total_cost=baseline["total_cost"].map(_money),
        optimal_cost_reduction_pct=baseline["optimal_cost_reduction_pct"].map(_pct),
    )
    demand_view = demand_shocks.assign(
        total_cost=demand_shocks["total_cost"].map(lambda x: _money(x) if pd.notna(x) else "Infeasible")
    )
    service_view = service_level.assign(
        total_cost=service_level["total_cost"].map(lambda x: _money(x) if pd.notna(x) else "Infeasible")
    )
    capacity_view = capacity.assign(
        total_cost=capacity["total_cost"].map(lambda x: _money(x) if pd.notna(x) else "Infeasible"),
        cost_increase_pct=capacity["cost_increase_pct"].map(lambda x: _pct(x) if pd.notna(x) else "N/A"),
    )

    service_tradeoff = metrics.get("service_tradeoff_cost_increase_pct") or {}
    service_sentence = ", ".join(
        f"{distance} km: {_pct(increase)}"
        for distance, increase in service_tradeoff.items()
    )

    report = f"""# Project Report: Supply Chain Network Optimization

## Executive Summary

This project formulates and solves a two-stage capacitated facility location problem for a synthetic supply chain network with {metrics["suppliers"]} suppliers, {metrics["warehouses"]} candidate warehouses, and {metrics["demand_nodes"]} demand nodes. The model uses binary warehouse-open decisions and continuous supplier-to-warehouse-to-demand flow variables to minimize fixed facility cost and variable transportation cost.

The optimized network opens {len(metrics["opened_warehouses"])} warehouses ({", ".join(metrics["opened_warehouses"])}) at a total logistics cost of {_money(metrics["optimal_total_cost"])}. Against operational baselines, the MILP reduces cost by {_pct(metrics["cost_reduction_vs_greedy_pct"])} versus greedy nearest-warehouse assignment, {_pct(metrics["cost_reduction_vs_open_all_pct"])} versus opening all facilities, and {_pct(metrics["cost_reduction_vs_kmeans_pct"])} versus a k-means location heuristic.

## Optimized Network

![Optimized supply chain network]({assets.get("network_map.png", "plots/network_map.png")})

## Model Scale

| Metric | Value |
|---|---:|
| Total nodes | {metrics["nodes"]} |
| Candidate warehouses | {metrics["warehouses"]} |
| Demand nodes | {metrics["demand_nodes"]} |
| Binary variables | {metrics["binary_variables"]} |
| Continuous flow variables | {metrics["continuous_flow_variables"]} |
| Optimal fixed cost | {_money(metrics["optimal_fixed_cost"])} |
| Optimal variable cost | {_money(metrics["optimal_variable_cost"])} |
| Optimal total cost | {_money(metrics["optimal_total_cost"])} |

## Baseline Comparison

{_markdown_table(baseline_view, ["method", "status", "total_cost", "opened_count", "optimal_cost_reduction_pct"])}

![Cost breakdown by method]({assets.get("cost_breakdown.png", "plots/cost_breakdown.png")})

## Robustness Analysis

Demand-shock experiments identify {metrics["robust_warehouse_count"]} robust warehouses ({", ".join(metrics["robust_warehouses"])}) and {metrics["marginal_warehouse_count"]} marginal warehouses ({", ".join(metrics["marginal_warehouses"])}). Robust warehouses remain open across all tested demand scenarios; marginal warehouses switch open or closed depending on scenario pressure.

{_markdown_table(demand_view, ["scenario", "status", "total_cost", "opened_warehouses"])}

![Sensitivity tornado chart]({assets.get("sensitivity_tornado.png", "plots/sensitivity_tornado.png")})

## Service-Level Tradeoff

The service-level extension constrains each demand node to be served within a maximum warehouse-to-demand distance. The resulting cost-of-service tradeoff is: {service_sentence}.

{_markdown_table(service_view, ["max_distance", "status", "total_cost", "opened_warehouses"])}

![Service level cost tradeoff]({assets.get("service_cost_tradeoff.png", "plots/service_cost_tradeoff.png")})

## Sustainability Extension

The emissions extension adds a carbon-price penalty to each km-unit shipped. This creates a cost-versus-emissions sweep that can be used as a Pareto-style planning discussion for sustainability-aware network design.

![Cost emissions Pareto sweep]({assets.get("cost_emissions_pareto.png", "plots/cost_emissions_pareto.png")})

## Capacity Stress Test

When warehouse capacity is tightened by 20%, the model re-optimizes the facility mix and routing decisions. The stress-test summary is:

{_markdown_table(capacity_view, ["scenario", "status", "total_cost", "cost_increase_pct", "opened_warehouses"])}

## Resume Bullets

- Formulated a {metrics["nodes"]}-node two-stage capacitated facility location MILP with {metrics["binary_variables"]} binary open/close decisions and {metrics["continuous_flow_variables"]} continuous flow variables in PuLP.
- Reduced total logistics cost by {_pct(metrics["cost_reduction_vs_greedy_pct"])} versus greedy nearest-warehouse assignment and {_pct(metrics["cost_reduction_vs_open_all_pct"])} versus an open-all baseline across {metrics["demand_nodes"]} demand nodes.
- Sensitivity-tested the network under +/-20%, +/-30%, and +/-50% demand shocks; identified {metrics["robust_warehouse_count"]} robust warehouse locations and {metrics["marginal_warehouse_count"]} marginal locations.
- Added service-level constraints and quantified max-distance cost tradeoffs across {len(service_tradeoff)} feasible distance thresholds.

## Interview Talking Points

- The facility-opening decision creates fixed-charge binary variables, so this is a MILP rather than a pure transportation LP.
- The tight linking constraint `x_ijk <= d_k y_j` prevents flow through closed warehouses without using a numerically weak big-M.
- CBC solves the MILP by repeatedly solving LP relaxations inside a branch-and-bound search tree.
- LP relaxations often return fractional warehouse openings because the fixed-charge structure breaks the total unimodularity seen in pure transportation problems.
- For larger networks, practical scaling options include demand aggregation, candidate warehouse pruning, Benders decomposition, Lagrangian relaxation, and warm-start heuristics.
"""

    report_path = config.BASE_DIR / "PROJECT_REPORT.md"
    report_path.write_text(report, encoding="utf-8")
    return report_path
