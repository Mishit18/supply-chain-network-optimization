import numpy as np
import pandas as pd

import config
from model import solve_network


def generate_node_level_demand_scenarios(
    demand,
    n_scenarios=config.MONTE_CARLO_SCENARIOS,
    std=config.MONTE_CARLO_NODE_DEMAND_STD,
    seed=config.RANDOM_SEED + 303,
):
    rng = np.random.default_rng(seed)
    base = demand.set_index("demand_id")["demand"].astype(float)
    scenarios = []
    for scenario_id in range(1, n_scenarios + 1):
        shocks = rng.normal(loc=1.0, scale=std, size=len(base))
        shocks = np.clip(shocks, 0.55, 1.65)
        values = np.ceil(base.to_numpy() * shocks).astype(float)
        scenarios.append(
            {
                "scenario_id": scenario_id,
                "demand": dict(zip(base.index, values)),
                "total_demand": float(values.sum()),
                "min_multiplier": float(shocks.min()),
                "max_multiplier": float(shocks.max()),
            }
        )
    return scenarios


def run_monte_carlo_demand_analysis(
    suppliers,
    warehouses,
    demand,
    arcs_sw,
    arcs_wd,
    n_scenarios=config.MONTE_CARLO_SCENARIOS,
):
    scenarios = generate_node_level_demand_scenarios(demand, n_scenarios=n_scenarios)
    rows = []
    open_counts = {warehouse_id: 0 for warehouse_id in warehouses["warehouse_id"]}

    for scenario in scenarios:
        result = solve_network(
            suppliers,
            warehouses,
            demand,
            arcs_sw,
            arcs_wd,
            demand_override=scenario["demand"],
        )
        for warehouse_id in result.opened_warehouses:
            open_counts[warehouse_id] += 1
        rows.append(
            {
                "scenario_id": scenario["scenario_id"],
                "status": result.status,
                "total_demand": scenario["total_demand"],
                "min_node_multiplier": scenario["min_multiplier"],
                "max_node_multiplier": scenario["max_multiplier"],
                "total_cost": result.objective,
                "opened_count": len(result.opened_warehouses),
                "opened_warehouses": ",".join(result.opened_warehouses),
            }
        )

    scenario_summary = pd.DataFrame(rows)
    stability = pd.DataFrame(
        [
            {
                "warehouse_id": warehouse_id,
                "open_frequency": count / n_scenarios,
                "open_count": count,
                "scenario_count": n_scenarios,
            }
            for warehouse_id, count in open_counts.items()
        ]
    ).sort_values(["open_frequency", "warehouse_id"], ascending=[False, True])
    return scenario_summary, stability
