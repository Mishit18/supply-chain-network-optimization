# Supply Chain Network Optimization

[![Tests](https://github.com/Mishit18/supply-chain-network-optimization/actions/workflows/tests.yml/badge.svg)](https://github.com/Mishit18/supply-chain-network-optimization/actions/workflows/tests.yml)

Two-stage supply chain network design using a capacitated facility location MILP. The model decides which distribution centers to open and how to route supplier flow through open facilities to demand nodes while minimizing fixed opening cost plus variable transportation cost.

## Results Snapshot

| Metric | Value |
|---|---:|
| Network size | 5 suppliers, 10 candidate warehouses, 50 demand nodes |
| MILP variables | 10 binary open/close variables, 2,500 continuous flow variables |
| Optimal total cost | $2,235,627 |
| Warehouses opened | W01, W02, W05, W06, W08 |
| Cost reduction vs greedy nearest | 20.60% |
| Cost reduction vs open-all network | 19.00% |
| Cost reduction vs k-means heuristic | 14.34% |
| Robust warehouses under demand shocks | W01, W05, W06, W08 |

![Optimized supply chain network](docs/assets/network_map.png)

## What This Project Covers

- Synthetic but realistic supply chain data generation with reproducible random seeds.
- Capacitated facility location and transportation formulation in PuLP.
- CBC solver workflow with optional Gurobi hook.
- Benchmarking against greedy nearest-warehouse, open-all, and k-means baselines.
- Sensitivity analysis for demand shocks, fixed costs, capacity tightening, and service-level distance constraints.
- Sustainability extension using carbon-price sweeps and cost/emissions tradeoff plots.
- Safety-stock calculation for open warehouses using a normal newsvendor-style approximation.
- Three-period facility-location extension with demand growth and warehouse switching costs.
- Scalable demand-zone aggregation demo for larger customer maps.
- Node-level Monte Carlo demand uncertainty with warehouse stability metrics.
- Interactive Streamlit dashboard that can re-solve custom demand, capacity, cost, service, and carbon scenarios.
- Exported CSV results, plots, generated report, optional dashboard, tests, and CI.

## Repository Structure

```text
.
|-- baselines.py           # Greedy, open-all, and k-means benchmark methods
|-- config.py              # Reproducible parameters and experiment settings
|-- dashboard.py           # Optional Streamlit dashboard
|-- data_generation.py     # Synthetic suppliers, warehouses, demand, and arc costs
|-- main.py                # End-to-end pipeline runner
|-- model.py               # PuLP MILP formulation and solution extraction
|-- report.py              # Generates PROJECT_REPORT.md and GitHub chart assets
|-- sensitivity.py         # Robustness and extension experiments
|-- validation.py          # Input validation checks
|-- visualize.py           # Network and tradeoff plots
|-- docs/                  # Interview, assumptions, and recruiter summaries
|-- tests/                 # Regression tests for data and model logic
|-- data/                  # Generated input CSVs after running main.py
|-- results/               # Generated solution and scenario CSVs
`-- plots/                 # Generated analysis charts
```

## Quick Start

```bash
python -m pip install -r requirements.txt
python main.py
```

Useful run modes:

```bash
python main.py --quick
python main.py --deep
python main.py --multi-period
python main.py --scale-demo
python main.py --monte-carlo
python main.py --solver-msg
```

Run the tests:

```bash
python -m pytest -q
```

Optional dashboard:

```bash
python -m pip install -r requirements-dashboard.txt
streamlit run dashboard.py
```

The dashboard displays generated results and includes a scenario solver with sliders for demand, capacity, fixed cost, service distance, and carbon price.

Generated artifacts:

- `data/`: reproducible synthetic input CSVs.
- `results/`: optimal solution, baseline comparisons, sensitivity tables, duals, and resume metrics.
- `plots/`: network map, cost breakdown, tornado chart, service tradeoff, and emissions Pareto sweep.
- `PROJECT_REPORT.md`: portfolio-style report with tables, charts, interpretation, and resume bullets.

Additional docs:

- `docs/INTERVIEW_GUIDE.md`: concise answers for common project interview questions.
- `docs/MODEL_ASSUMPTIONS.md`: assumptions, simplifications, and limitations.
- `docs/RECRUITER_SUMMARY.md`: short resume-oriented project summary.

The default run keeps the core benchmark, robustness, service-level, sustainability, and safety-stock outputs laptop-friendly. Use `--deep` when the slower fixed-cost threshold sweep is needed.

## Advanced Extension

Run the multi-period model:

```bash
python main.py --multi-period
```

This solves a three-period version of the facility-location problem with demand growth, warehouse opening switching costs, and warehouse closing switching costs. Outputs are written to `results/multi_period_summary.csv` and `results/multi_period_transitions.csv`.

Run the scale demo:

```bash
python main.py --scale-demo
```

This creates a larger synthetic customer cloud, aggregates customer points into demand zones, solves the zone-level MILP, and writes `results/scale_demo_summary.csv`.

Run node-level Monte Carlo demand uncertainty:

```bash
python main.py --monte-carlo
```

This perturbs demand independently by node, re-solves the network, and writes warehouse-opening stability tables.

## Mathematical Formulation

Sets:

- `I`: suppliers.
- `J`: potential warehouse or distribution-center locations.
- `K`: demand nodes.

Parameters:

- `d_k`: demand at node `k`.
- `S_i`: capacity of supplier `i`.
- `U_j`: capacity of warehouse `j`.
- `F_j`: fixed opening cost of warehouse `j`.
- `c_ij`: unit transportation cost from supplier `i` to warehouse `j`.
- `c_jk`: unit transportation cost from warehouse `j` to demand node `k`.

Decision variables:

- `y_j in {0,1}`: 1 if warehouse `j` is opened, else 0.
- `x_ijk >= 0`: flow shipped from supplier `i` through warehouse `j` to demand node `k`.

Objective:

```text
minimize sum_j F_j y_j + sum_i sum_j sum_k (c_ij + c_jk) x_ijk
```

Constraints:

```text
sum_i sum_j x_ijk = d_k                         for every demand node k
sum_j sum_k x_ijk <= S_i                        for every supplier i
sum_i sum_k x_ijk <= U_j y_j                    for every warehouse j
x_ijk <= d_k y_j                                for every i, j, k
x_ijk >= 0, y_j in {0,1}
```

The project implements the capacitated facility location problem (CFLP). Unlike an uncapacitated facility location model, CFLP limits flow through each open warehouse, making the network-design tradeoff closer to real operations planning.

## Baseline Comparison

![Cost breakdown by method](docs/assets/cost_breakdown.png)

| Method | Total Cost | Cost Reduction from MILP |
|---|---:|---:|
| Greedy nearest warehouse | $2,815,727 | 20.60% |
| Open all warehouses | $2,759,999 | 19.00% |
| K-means heuristic | $2,609,845 | 14.34% |

## Sensitivity and Robustness

The model is re-solved under demand shocks of `-50%, -30%, -20%, +20%, +30%, +50%`. Warehouses W01, W05, W06, and W08 remain open across all demand scenarios, while W02 and W10 are marginal and change with scenario pressure.

![Sensitivity tornado chart](docs/assets/sensitivity_tornado.png)

Service-level constraints require each demand node to be served within a maximum warehouse-to-demand distance. The tighter the maximum distance, the more expensive the network becomes.

![Service-level cost tradeoff](docs/assets/service_cost_tradeoff.png)

## Sustainability Extension

The emissions extension adds carbon cost per km-unit shipped and re-solves the network for a range of carbon prices. This produces a planning view of the cost-versus-emissions tradeoff.

![Cost emissions Pareto sweep](docs/assets/cost_emissions_pareto.png)

## Why MILP?

This is not only a transportation problem because facility-opening decisions are endogenous. The binary fixed-charge variables make the problem a mixed-integer linear program. Facility location is NP-hard because the solver must search over possible open/closed subsets of candidate warehouses.

CBC solves the model through branch-and-bound over LP relaxations. LP relaxation can produce fractional warehouse openings because opening 0.4 of a warehouse may look cheap in the relaxation, even though real facilities must be opened or closed.

## Scaling Discussion

For networks with thousands of demand nodes, practical options include:

- Aggregating demand into zones before solving. This repository includes a coded scale demo for that workflow.
- Pruning weak warehouse candidates using distance and capacity screens.
- Using warm-start heuristics from k-means or greedy construction.
- Applying decomposition methods such as Benders decomposition.
- Solving with commercial solvers for large production-scale instances.

## Resume Bullets

- Formulated a 65-node two-stage capacitated facility location MILP with 10 binary open/close decisions and 2,500 continuous flow variables in PuLP.
- Reduced total logistics cost by 20.60% versus greedy nearest-warehouse assignment and 19.00% versus an open-all baseline across 50 demand nodes.
- Sensitivity-tested the network under +/-20%, +/-30%, and +/-50% demand shocks; identified 4 robust warehouse locations and 2 marginal locations.
- Added max-distance service-level constraints and quantified cost-of-service tradeoffs across 2 feasible thresholds.
