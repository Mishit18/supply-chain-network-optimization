import pandas as pd

import config
from model import solve_network


def save_solution(result, prefix="optimal"):
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    summary = pd.DataFrame(
        [
            {
                "scenario": prefix,
                "status": result.status,
                "objective": result.objective,
                "fixed_cost": result.fixed_cost,
                "variable_cost": result.variable_cost,
                "opened_count": len(result.opened_warehouses),
                "opened_warehouses": ",".join(result.opened_warehouses),
            }
        ]
    )
    summary.to_csv(config.RESULTS_DIR / f"{prefix}_summary.csv", index=False)

    pd.DataFrame(
        [{"warehouse_id": j, "open_value": value} for j, value in result.warehouse_decisions.items()]
    ).to_csv(config.RESULTS_DIR / f"{prefix}_warehouse_decisions.csv", index=False)

    pd.DataFrame(result.flows).to_csv(config.RESULTS_DIR / f"{prefix}_flows.csv", index=False)
    pd.DataFrame(
        [{"demand_id": k, "shadow_price": value} for k, value in result.demand_duals.items()]
    ).to_csv(config.RESULTS_DIR / f"{prefix}_demand_duals.csv", index=False)

    return summary


def run_optimal(suppliers, warehouses, demand, arcs_sw, arcs_wd, msg=False):
    result = solve_network(suppliers, warehouses, demand, arcs_sw, arcs_wd, msg=msg)
    save_solution(result, "optimal")
    return result
