# Recruiter Summary

## Project

Supply Chain Network Optimization using MILP in Python, with a hybrid RAG decision copilot for executive explanations.

## Core Result

The optimized network reduced total logistics cost by 20.60% versus a greedy nearest-warehouse baseline and 19.00% versus an open-all baseline across a 65-node synthetic network.

## Technical Stack

- Python
- PuLP and CBC
- NumPy and pandas
- scikit-learn
- matplotlib
- pytest
- GitHub Actions
- Hybrid TF-IDF retrieval / RAG copilot
- Streamlit decision interface
- Scenario memory and retrieval evaluation
- Executive memo generation

## Operations Concepts Demonstrated

- Facility location
- Transportation optimization
- Capacity constraints
- Demand satisfaction
- Branch-and-bound intuition
- Baseline benchmarking
- Sensitivity analysis
- Service-level tradeoffs
- Sustainability-aware planning
- Safety-stock approximation
- Multi-period network planning
- Demand aggregation for scaling
- Monte Carlo demand robustness
- Interactive scenario re-optimization
- Retrieval-augmented decision explanation
- Evidence-cited recommendations
- Scenario memory for what-if runs
- Retrieval benchmark for supply-chain questions

## Best Resume Bullets

- Formulated a 65-node two-stage capacitated facility location MILP with 10 binary open/close decisions and 2,500 continuous flow variables in PuLP.
- Reduced total logistics cost by 20.60% versus greedy nearest-warehouse assignment and 19.00% versus an open-all baseline across 50 demand nodes.
- Sensitivity-tested the network under +/-20%, +/-30%, and +/-50% demand shocks; identified 4 robust warehouse locations and 2 marginal locations.
- Added max-distance service-level constraints and quantified cost-of-service tradeoffs across 2 feasible thresholds.
- Built hybrid RAG decision copilot over reports, model assumptions, policy notes, scenario memory, and optimizer outputs to explain warehouse choices, cost-service tradeoffs, emissions constraints, and rollout risks with citations.
- Added retrieval benchmark and executive memo generator, turning MILP outputs into audited management recommendations for supply-chain stakeholders.
