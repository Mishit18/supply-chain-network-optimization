# Supply Chain Network Optimization

This project builds a reproducible two-stage capacitated facility location and transportation MILP for a synthetic supply chain network. It decides which warehouses to open and how to route supplier flow through those warehouses to demand nodes while minimizing fixed opening cost plus variable transportation cost.

## Quick Start

```bash
cd supply_chain_network_optimization
python -m pip install -r requirements.txt
python main.py
```

Generated artifacts:

- `data/`: reproducible synthetic CSV inputs.
- `results/`: optimal solution, baseline comparisons, sensitivity tables, duals, resume metrics.
- `plots/`: network map, cost breakdown, tornado chart, service tradeoff, emissions Pareto sweep.

## Mathematical Formulation

Sets:

- `I`: suppliers.
- `J`: potential warehouse or DC locations.
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

The implementation solves the capacitated facility location problem (CFLP). In an uncapacitated facility location problem (UFL), open facilities can serve unlimited demand, so facility capacity constraints are absent or non-binding. CFLP is more realistic for operations roles because capacity forces tradeoffs between fixed cost, geographic proximity, and service feasibility.

## Why MILP?

This is not just a transportation problem because the model must choose facilities before routing flow. Binary variables make it a mixed-integer linear program. Facility location is NP-hard because it contains the fixed-charge location choice problem: selecting the best subset of warehouses among `2^|J|` possible open/closed combinations. Solvers such as CBC use branch-and-bound and cutting-plane methods to search this combinatorial space while solving LP relaxations at nodes.

The LP relaxation can produce fractional `y_j` values because the model may prefer opening 0.37 of a warehouse to avoid paying a full fixed cost. Natural integrality is more likely in pure transportation or assignment models with totally unimodular constraint matrices and integral right-hand sides. The fixed-charge linking constraints break that structure.

## Baselines

The project compares the MILP optimum against:

- Greedy nearest warehouse: assign each demand node to its nearest potential warehouse, then solve the best supplier routing under that assignment.
- Open all: open every candidate warehouse and optimize transportation.
- K-means: cluster demand nodes, select warehouses nearest to cluster centers, then optimize routing through those warehouses.

The baseline costs are saved to `results/baseline_comparison.csv`.

## Sensitivity Analyses

Implemented experiments:

- Demand shocks: `-50%, -30%, -20%, +20%, +30%, +50%`.
- Fixed cost sweep: warehouse-by-warehouse open/closed threshold behavior.
- Capacity tightening: reduce warehouse capacity by 20%.
- Service-level constraints: force demand nodes to be served within `D = 200, 300, 400` distance units.
- Shadow prices: demand-constraint dual values from the LP solve are exported for economic interpretation.
- Emissions extension: solve a cost-plus-carbon-price sweep and plot a cost/emissions frontier.
- Safety stock: compute open-warehouse safety stock using a normal approximation and service factor.

## Interpreting Shadow Prices

The dual value of a demand constraint approximates the marginal increase in objective cost from one extra unit of demand at that node in the LP relaxation. A high shadow price usually means the node is expensive to serve because it is far from open warehouses, close to constrained capacity, or both. For the MILP itself, duals are not directly meaningful at integer nodes, so the code exports duals from the solved relaxation/subproblem context.

## Infeasibility Checklist

If CBC reports infeasibility:

- Check `sum supplier capacity >= sum demand`.
- Check `sum warehouse capacity >= sum demand`.
- Check service distance limits; a tight `D` can leave some demand nodes unreachable.
- Check fixed-open baselines; selected warehouses may not have enough capacity.
- Avoid huge big-M values. This project uses `x_ijk <= d_k y_j`, a tight link based on demand.

## Common Mistakes

- Missing the warehouse capacity-linking constraint, which allows flow through closed warehouses.
- Using an oversized big-M and causing numerical instability.
- Comparing MILP against an unrealistically weak baseline.
- Forgetting supplier capacity, which turns the project into a location-only exercise.
- Treating LP relaxation duals as exact MILP economics without qualification.

## Interview Depth

Strong answers should explain:

- MILP is needed because warehouse opening decisions are binary fixed-charge decisions.
- CBC solves by exploring a branch-and-bound tree of LP relaxations and pruning dominated nodes.
- CFLP differs from a transportation problem because facility selection is endogenous.
- Scaling to 10,000 demand nodes needs aggregation, decomposition, candidate pruning, heuristics, column generation, or commercial solvers.
- Robustness matters because a single deterministic demand forecast can overfit the network design.

After running `python main.py`, use `results/resume_metrics.json` to fill resume bullets with actual numbers from your generated experiment.
