# Interview Guide

## 30-Second Pitch

I built a capacitated facility location model for supply chain network design. The model chooses which warehouses to open and how to route supplier flow through those warehouses to demand nodes. I compared the MILP optimum against greedy, open-all, and k-means baselines, then stress-tested the network under demand, capacity, fixed-cost, service-level, and emissions scenarios.

## What Makes The Project Strong

- It is a decision model, not just a dashboard: the warehouse network is optimized end to end.
- It uses binary decisions for facility opening and continuous variables for shipment flows.
- It benchmarks the optimization result against reasonable heuristics instead of reporting an isolated optimum.
- It tests robustness under demand shocks and capacity pressure.
- It links operations cost, service levels, and sustainability in one reproducible workflow.

## Questions To Expect

### Why MILP instead of LP?

Warehouse openings are fixed-charge yes/no decisions. A pure LP could open fractional warehouses, which is not operationally meaningful. The flow variables are continuous, but facility decisions are binary, so the model is a MILP.

### How is this different from a transportation problem?

A transportation problem assumes facilities are already available. This project decides the facility set first and then optimizes flow through that selected network.

### What does the linking constraint do?

The constraint `x_ijk <= d_k y_j` prevents any flow through warehouse `j` unless `y_j = 1`. It also keeps the big-M value tight because the largest useful shipment to demand node `k` is its demand.

### Why is facility location NP-hard?

With 10 candidate warehouses there are `2^10` possible open/closed subsets. With hundreds of candidates, enumerating all subsets becomes impossible. Branch-and-bound searches this space intelligently using LP relaxations and pruning.

### What does a demand dual mean?

In the LP relaxation, the demand dual approximates the marginal cost of serving one additional unit at a demand node. Higher values usually indicate poor proximity to open warehouses or tight capacity.

### How would this scale to 10,000 demand nodes?

I would aggregate demand into zones, prune weak candidate warehouses, warm-start with heuristics, and consider decomposition methods such as Benders decomposition. For production use, I would also evaluate a commercial solver.

## Strong Talking Points

- The baseline comparison matters because an optimization result without a benchmark has weak business meaning.
- Robust warehouses are better candidates for long-term investment because they stay open across demand shocks.
- Marginal warehouses are useful managerial signals: they are sensitive to demand contraction, expansion, or fixed-cost assumptions.
- Service-level constraints create a direct cost-of-service curve, useful for negotiation between operations and customer-experience teams.

## Red Flags To Avoid

- Saying the solver "just finds the minimum" without explaining binary decisions and constraints.
- Treating the LP relaxation as the real solution when `y_j` values are fractional.
- Comparing the MILP only to a weak baseline to inflate savings.
- Ignoring infeasibility caused by capacity or service-distance constraints.
- Claiming the synthetic data is real business data.
