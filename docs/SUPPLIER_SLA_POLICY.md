# Supplier And Warehouse SLA Policy

## Purpose

This policy document gives the RAG copilot realistic operating context for supply-chain recommendations. It is a synthetic policy for portfolio demonstration and should not be represented as a real company contract.

## Service Commitments

- Standard customer demand nodes should be served within the baseline network unless a scenario explicitly tightens the maximum warehouse-to-demand distance.
- High-priority customer zones should be reviewed under service-level constraints before finalizing warehouse openings.
- A facility that is optimal only in one narrow scenario should be treated as a marginal warehouse and reviewed before long-term investment.

## Capacity Governance

- Warehouse utilization above the modeled capacity limit is not allowed in the MILP.
- A capacity-tightening scenario should trigger management review if it changes the open warehouse set or materially increases cost.
- Supplier and warehouse capacity assumptions must be validated before production deployment.

## Operating Cadence

- Review demand-shock scenarios before approving network expansion.
- Compare the optimized network against greedy, open-all, and k-means baselines.
- Use the RAG copilot only to explain cited model evidence; do not let it override the optimizer.

## Rollout Risks

- Synthetic distance and cost assumptions may not capture real road constraints, tolls, lead-time variability, or carrier contracts.
- Service-distance constraints can increase cost or make some scenarios infeasible.
- Marginal warehouses should be monitored through scenario memory before being treated as stable strategic choices.
