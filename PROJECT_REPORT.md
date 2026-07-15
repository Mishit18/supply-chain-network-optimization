# Project Report: Supply Chain Network Optimization

## Executive Summary

This project formulates and solves a two-stage capacitated facility location problem for a synthetic supply chain network with 5 suppliers, 10 candidate warehouses, and 50 demand nodes. The model uses binary warehouse-open decisions and continuous supplier-to-warehouse-to-demand flow variables to minimize fixed facility cost and variable transportation cost.

The optimized network opens 5 warehouses (W01, W02, W05, W06, W08) at a total logistics cost of $2,235,627. Against operational baselines, the MILP reduces cost by 20.60% versus greedy nearest-warehouse assignment, 19.00% versus opening all facilities, and 14.34% versus a k-means location heuristic.

## Optimized Network

![Optimized supply chain network](docs/assets/network_map.png)

## Model Scale

| Metric | Value |
|---|---:|
| Total nodes | 65 |
| Candidate warehouses | 10 |
| Demand nodes | 50 |
| Binary variables | 10 |
| Continuous flow variables | 2500 |
| Solver variables | 2510 |
| Solver constraints | 2565 |
| Optimal fixed cost | $545,982 |
| Optimal variable cost | $1,689,645 |
| Optimal total cost | $2,235,627 |

## Baseline Comparison

| method         | status  | total_cost | opened_count | optimal_cost_reduction_pct |
| -------------- | ------- | ---------- | ------------ | -------------------------- |
| greedy_nearest | Optimal | $2,815,728 | 10           | 20.60%                     |
| open_all       | Optimal | $2,759,999 | 10           | 19.00%                     |
| kmeans         | Optimal | $2,609,846 | 4            | 14.34%                     |

![Cost breakdown by method](docs/assets/cost_breakdown.png)

## Robustness Analysis

Demand-shock experiments identify 4 robust warehouses (W01, W05, W06, W08) and 2 marginal warehouses (W02, W10). Robust warehouses remain open across all tested demand scenarios; marginal warehouses switch open or closed depending on scenario pressure.

| scenario    | status  | total_cost | opened_warehouses       |
| ----------- | ------- | ---------- | ----------------------- |
| demand_-50% | Optimal | $1,190,421 | W01,W05,W06,W08         |
| demand_-30% | Optimal | $1,591,798 | W01,W02,W05,W06,W08     |
| demand_-20% | Optimal | $1,790,393 | W01,W02,W05,W06,W08     |
| demand_+20% | Optimal | $2,775,429 | W01,W02,W05,W06,W08,W10 |
| demand_+30% | Optimal | $3,016,433 | W01,W02,W05,W06,W08,W10 |
| demand_+50% | Optimal | $3,527,266 | W01,W02,W05,W06,W08,W10 |

![Sensitivity tornado chart](docs/assets/sensitivity_tornado.png)

## Service-Level Tradeoff

The service-level extension constrains each demand node to be served within a maximum warehouse-to-demand distance. The resulting cost-of-service tradeoff is: 300 km: 6.18%, 400 km: 1.84%.

| max_distance | status     | total_cost | opened_warehouses           |
| ------------ | ---------- | ---------- | --------------------------- |
| 200          | Infeasible | Infeasible | nan                         |
| 300          | Optimal    | $2,373,720 | W01,W02,W03,W05,W06,W07,W08 |
| 400          | Optimal    | $2,276,682 | W01,W02,W05,W06,W07,W08     |

![Service level cost tradeoff](docs/assets/service_cost_tradeoff.png)

## Sustainability Extension

The emissions extension adds a carbon-price penalty to each km-unit shipped. This creates a cost-versus-emissions sweep that can be used as a Pareto-style planning discussion for sustainability-aware network design.

![Cost emissions Pareto sweep](docs/assets/cost_emissions_pareto.png)

## Multi-Period Extension

The repository includes a three-period extension with demand growth and warehouse switching costs. Run `python main.py --multi-period` to solve it and export `results/multi_period_summary.csv` and `results/multi_period_transitions.csv`.

| period | demand_growth | opened_count | opened_warehouses       | total_flow |
| ------ | ------------- | ------------ | ----------------------- | ---------- |
| 1      | 1.0           | 5            | W01,W02,W05,W06,W08     | 5038.0     |
| 2      | 1.12          | 5            | W01,W02,W05,W06,W08     | 5642.56    |
| 3      | 1.25          | 6            | W01,W02,W05,W06,W08,W10 | 6297.5     |

## Scaling Demonstration

The scale demo generates a larger synthetic customer cloud, aggregates customers into demand zones, and solves the zone-level MILP. Run `python main.py --scale-demo` to refresh this table.

| raw_customer_nodes | aggregated_zones | status  | opened_count | variables | constraints | solve_seconds |
| ------------------ | ---------------- | ------- | ------------ | --------- | ----------- | ------------- |
| 1000               | 75               | Optimal | 9            | 3760      | 3840        | 0.53          |

## Monte Carlo Demand Uncertainty

The Monte Carlo extension perturbs demand independently at each node, re-solves the MILP, and measures warehouse-opening stability. Run `python main.py --monte-carlo` to refresh these tables.

| scenario_id | status  | total_demand | total_cost | opened_count | opened_warehouses   |
| ----------- | ------- | ------------ | ---------- | ------------ | ------------------- |
| 1           | Optimal | 5,150        | $2,303,808 | 5            | W01,W02,W05,W06,W08 |
| 2           | Optimal | 4,804        | $2,138,269 | 5            | W01,W02,W05,W06,W08 |
| 3           | Optimal | 5,137        | $2,277,353 | 5            | W01,W02,W05,W06,W08 |
| 4           | Optimal | 4,971        | $2,186,062 | 5            | W01,W02,W05,W06,W08 |
| 5           | Optimal | 4,869        | $2,152,086 | 5            | W01,W02,W05,W06,W08 |
| 6           | Optimal | 5,013        | $2,227,564 | 5            | W01,W02,W05,W06,W08 |
| 7           | Optimal | 5,131        | $2,296,579 | 5            | W01,W02,W05,W06,W08 |
| 8           | Optimal | 4,963        | $2,208,223 | 5            | W01,W02,W05,W06,W08 |

| warehouse_id | open_frequency | open_count | scenario_count |
| ------------ | -------------- | ---------- | -------------- |
| W01          | 100.00%        | 8          | 8              |
| W02          | 100.00%        | 8          | 8              |
| W05          | 100.00%        | 8          | 8              |
| W06          | 100.00%        | 8          | 8              |
| W08          | 100.00%        | 8          | 8              |
| W03          | 0.00%          | 0          | 8              |
| W04          | 0.00%          | 0          | 8              |
| W07          | 0.00%          | 0          | 8              |
| W09          | 0.00%          | 0          | 8              |
| W10          | 0.00%          | 0          | 8              |

## Capacity Stress Test

When warehouse capacity is tightened by 20%, the model re-optimizes the facility mix and routing decisions. The stress-test summary is:

| scenario                | status  | total_cost | cost_increase_pct | opened_warehouses       |
| ----------------------- | ------- | ---------- | ----------------- | ----------------------- |
| warehouse_capacity_-20% | Optimal | $2,311,924 | 3.41%             | W01,W02,W05,W06,W08,W10 |

## Resume Bullets

- Formulated a 65-node two-stage capacitated facility location MILP with 10 binary open/close decisions and 2500 continuous flow variables in PuLP.
- Reduced total logistics cost by 20.60% versus greedy nearest-warehouse assignment and 19.00% versus an open-all baseline across 50 demand nodes.
- Sensitivity-tested the network under +/-20%, +/-30%, and +/-50% demand shocks; identified 4 robust warehouse locations and 2 marginal locations.
- Added service-level constraints and quantified max-distance cost tradeoffs across 2 feasible distance thresholds.

## Interview Talking Points

- The facility-opening decision creates fixed-charge binary variables, so this is a MILP rather than a pure transportation LP.
- The tight linking constraint `x_ijk <= d_k y_j` prevents flow through closed warehouses without using a numerically weak big-M.
- CBC solves the MILP by repeatedly solving LP relaxations inside a branch-and-bound search tree.
- LP relaxations often return fractional warehouse openings because the fixed-charge structure breaks the total unimodularity seen in pure transportation problems.
- For larger networks, practical scaling options include demand aggregation, candidate warehouse pruning, Benders decomposition, Lagrangian relaxation, and warm-start heuristics.
