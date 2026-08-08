# Interview Guide

## 30-Second Pitch

I built a capacitated facility location model for supply chain network design. The model chooses which warehouses to open and how to route supplier flow through those warehouses to demand nodes. I compared the MILP optimum against greedy, open-all, and k-means baselines, then stress-tested the network under demand, capacity, fixed-cost, service-level, and emissions scenarios. I also added a hybrid RAG decision copilot with scenario memory, retrieval evaluation, and executive memo generation to explain recommendations with citations.

## What Makes The Project Strong

- It is a decision model, not just a dashboard: the warehouse network is optimized end to end.
- It uses binary decisions for facility opening and continuous variables for shipment flows.
- It benchmarks the optimization result against reasonable heuristics instead of reporting an isolated optimum.
- It tests robustness under demand shocks and capacity pressure.
- It links operations cost, service levels, and sustainability in one reproducible workflow.
- It adds a modern RAG layer that turns optimizer outputs into cited executive explanations without changing the mathematical source of truth.
- It logs what-if scenarios into retrievable memory and benchmarks retrieval quality against supply-chain decision questions.

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

### What does the RAG copilot do?

It ingests the project report, assumptions, recruiter notes, policy notes, sensitivity CSVs, service-level tables, baseline comparison, scenario memory, and generated metrics. When asked a question, it retrieves the most relevant chunks and synthesizes a cited explanation. The optimizer decides the network; RAG explains the decision and surfaces supporting evidence.

### Why use TF-IDF retrieval instead of an external LLM or vector database?

For a portfolio project, offline reproducibility matters. The current version uses hybrid word and character TF-IDF retrieval because it is transparent, fast, deterministic, and requires no API key. The architecture can later swap in sentence-transformer embeddings or a vector database without changing the decision workflow.

### What is scenario memory?

Every dashboard what-if solve can be logged to `results/scenario_runs.csv` with assumptions, opened warehouses, objective value, copilot confidence, and top evidence. This lets the RAG system retrieve previous scenario decisions instead of treating each solve as an isolated event.

### How did you evaluate retrieval?

I added `docs/rag_eval_questions.csv`, a small benchmark of supply-chain decision questions with expected source files. Running `python rag_copilot.py --evaluate` reports source hit and recall@k, then exports `results/rag_eval_results.csv`.

### How would this scale to 10,000 demand nodes?

I would aggregate demand into zones, prune weak candidate warehouses, warm-start with heuristics, and consider decomposition methods such as Benders decomposition. The repository includes a coded scale demo that aggregates a larger customer cloud into demand zones before solving. For production use, I would also evaluate a commercial solver.

## Strong Talking Points

- The baseline comparison matters because an optimization result without a benchmark has weak business meaning.
- Robust warehouses are better candidates for long-term investment because they stay open across demand shocks.
- Monte Carlo node-level demand scenarios are stronger than only global demand multipliers because they test spatial demand redistribution.
- Marginal warehouses are useful managerial signals: they are sensitive to demand contraction, expansion, or fixed-cost assumptions.
- Service-level constraints create a direct cost-of-service curve, useful for negotiation between operations and customer-experience teams.
- RAG is valuable here because supply-chain decisions are evidence-heavy: stakeholders need to know which assumption, scenario table, policy note, or sensitivity result supports a recommendation.

## Red Flags To Avoid

- Saying the solver "just finds the minimum" without explaining binary decisions and constraints.
- Treating the LP relaxation as the real solution when `y_j` values are fractional.
- Comparing the MILP only to a weak baseline to inflate savings.
- Ignoring infeasibility caused by capacity or service-distance constraints.
- Claiming the synthetic data is real business data.
- Saying the RAG layer optimizes the network. It retrieves and explains evidence; the MILP optimizes the network.
