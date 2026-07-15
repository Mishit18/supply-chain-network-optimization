# Model Assumptions

## Network Design

- Suppliers, candidate warehouses, and demand nodes are placed on a 1000 x 1000 synthetic coordinate grid.
- Supplier-to-warehouse and warehouse-to-demand costs are proportional to Euclidean distance with route-specific weight factors.
- Warehouse opening costs vary by tier: small, medium, and large.
- Warehouse capacities vary by tier and are generated with enough aggregate capacity to test demand expansion scenarios.

## Demand

- Demand is generated from a Poisson distribution.
- Each demand node receives a seasonal multiplier.
- Demand shocks are modeled by multiplying all node-level demands by scenario factors.

## Optimization

- The base model is a single-period deterministic MILP.
- The optional multi-period model adds demand growth and switching costs, but still uses deterministic period-level demand.
- Flows are continuous, representing aggregate shipment volume rather than individual orders.
- Warehouses have fixed opening costs and capacity limits.
- Supplier capacities are enforced.
- Demand must be fully satisfied.

## Baselines

- Greedy nearest warehouse assigns each demand node to the nearest candidate warehouse, then solves routing through that assignment.
- Open-all fixes every warehouse as open and optimizes transportation.
- K-means clusters demand nodes and opens warehouses nearest to cluster centroids.

## Extensions

- Service-level constraints restrict maximum warehouse-to-demand distance.
- Emissions are modeled as kg CO2e per km-unit and converted to cost through a carbon price.
- Safety stock is computed after network optimization using a normal approximation.
- Fixed-cost threshold sweeps are available through the deeper experiment mode.

## Limitations

- Travel distance is Euclidean, not road-network distance.
- The model does not include stochastic programming recourse decisions.
- Inventory holding, labor, and lease duration are simplified.
- Supplier lead times and product-level SKUs are not explicitly modeled.
- The synthetic data is designed for reproducible modeling depth, not for estimating real market costs.
