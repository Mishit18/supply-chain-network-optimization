# ATS Screening Pack

## Best-Fit Roles

This project is strongest for:

- Strategy and Operations
- Supply Chain Strategy
- Operations Research
- Product Operations
- Marketplace Operations
- Business Analyst
- Data Analyst / Operations Analytics
- Consulting case discussion

It should be used as the flagship project for operations-heavy resumes because it connects optimization, scenario analysis, baselines, executive recommendations, and a grounded RAG decision-copilot layer.

## Recruiter Summary

Built a capacitated facility-location MILP for supply-chain network design. The model chooses which distribution centers to open and routes supplier flow through selected facilities to demand nodes while minimizing fixed opening cost plus transportation cost. The optimized 65-node network uses 10 binary warehouse decisions and 2,500 continuous flow variables, reducing total logistics cost by 20.60% versus greedy nearest-warehouse assignment and 19.00% versus an open-all baseline. Added a RAG decision copilot that retrieves model assumptions, reports, sensitivity tables, and scenario outputs to explain recommendations with citations.

## ATS Keyword Coverage

| Area | Keywords |
|---|---|
| Optimization | MILP, PuLP, CBC, facility location, transportation optimization, binary decision variables |
| Supply Chain | warehouse network, distribution centers, capacity planning, demand nodes, supplier flow, logistics cost |
| Strategy/Ops | scenario analysis, sensitivity analysis, service-level tradeoff, sustainability planning, executive recommendation |
| Analytics | baselines, k-means heuristic, greedy heuristic, Monte Carlo demand uncertainty, demand aggregation |
| RAG / AI | RAG, hybrid retrieval, cited evidence, decision copilot, grounded answers, scenario memory, executive memo, retrieval evaluation |
| Technical Evidence | regression tests, Streamlit dashboard, solver workflow, reproducible pipeline, GitHub Actions |

## Resume Bullets - Strategy / Ops

- Formulated a 65-node capacitated facility-location MILP in PuLP with 10 binary warehouse-open decisions and 2,500 continuous flow variables to optimize warehouse selection and supplier-to-demand routing.
- Reduced modeled logistics cost by 20.60% versus greedy nearest-warehouse assignment and 19.00% versus open-all baseline; benchmarked against greedy, open-all, and k-means heuristics.
- Stress-tested the network under +/-20%, +/-30%, and +/-50% demand shocks, identifying 4 robust warehouse locations and 2 marginal facilities sensitive to demand pressure.
- Added service-level distance constraints, carbon-price sweeps, safety-stock approximation, multi-period switching-cost planning, and Monte Carlo demand robustness to convert the optimization into an executive planning tool.
- Built a hybrid RAG decision copilot over MILP reports, model assumptions, policy notes, sensitivity tables, and scenario memory to explain warehouse selection, cost-service tradeoffs, emissions constraints, and rollout risks with citations.
- Added retrieval benchmark and executive memo generator, turning MILP outputs into audited management recommendations for supply-chain stakeholders.

## Resume Bullets - Data / Ops Analytics

- Built reproducible Python optimization pipeline with data generation, validation checks, PuLP model solve, baseline comparison, sensitivity outputs, charts, and Streamlit scenario re-optimization dashboard.
- Created cost breakdown, network map, sensitivity tornado, service-cost tradeoff, and emissions Pareto plots to translate MILP outputs into operational decisions.
- Added retrieval-backed Q&A over reports, CSV outputs, scenario memory, and policy notes, enabling cited answers on robustness, service-level tradeoffs, carbon scenarios, and implementation risks.

## Interview Defense

### Why is this a MILP?

Warehouse opening is a yes/no fixed-charge decision, represented by binary variables. Shipment quantities are continuous. Combining binary facility decisions with continuous flow decisions makes the model a mixed-integer linear program.

### Why is this not just a transportation problem?

A transportation problem assumes facilities are already open. This model first chooses the warehouse network and then optimizes flow through the selected facilities.

### Why do baselines matter?

The optimized cost is only meaningful relative to reasonable alternatives. Greedy nearest-warehouse, open-all, and k-means heuristics show whether the MILP improves over simple operating policies.

### How would you scale this?

Aggregate demand into zones, prune weak warehouse candidates, warm-start with heuristic solutions, and consider decomposition or commercial solvers for production-scale networks.

### What is the biggest caveat?

The data is synthetic and uses simplified road-adjusted distances. The project proves modeling and decision-quality skills, not a direct operational result for a real company.

### Is the RAG layer a replacement for the optimizer?

No. The optimizer remains the source of truth for warehouse decisions and costs. The RAG layer retrieves evidence from reports, assumptions, policy notes, scenario memory, and result tables to explain the decision, cite supporting outputs, and translate the model into an executive recommendation.

## Claims To Avoid

- Do not claim the data came from a real company.
- Do not claim actual cost savings; say modeled cost reduction.
- Do not claim production deployment unless the dashboard is deployed.
- Do not imply the synthetic distances are real road-network distances.
- Do not overstate carbon planning as a full ESG model; it is a carbon-price sensitivity extension.
- Do not claim the RAG copilot creates new optimization results; it explains retrieved project evidence, scenario memory, and optimizer outputs.

## 30-Second Interview Pitch

I built a supply-chain network optimization project using a capacitated facility-location MILP. The model chooses which warehouses to open and routes supplier flow through the selected network to demand nodes. I benchmarked the MILP against greedy nearest-warehouse, open-all, and k-means heuristics, then stress-tested the result under demand shocks, service constraints, capacity pressure, and carbon-price scenarios. I also added a hybrid RAG decision copilot with scenario memory, retrieval evaluation, and executive memo generation to explain warehouse choices and rollout risks with citations. The key result is a 20.60% modeled cost reduction versus the greedy baseline, with robust warehouse choices identified across uncertainty scenarios.
