import numpy as np
import pandas as pd

import config
from model import solve_network


def demand_shock_analysis(suppliers, warehouses, demand, arcs_sw, arcs_wd):
    rows = []
    open_sets = {}
    for shock in config.DEMAND_SHOCKS:
        result = solve_network(
            suppliers,
            warehouses,
            demand,
            arcs_sw,
            arcs_wd,
            demand_multiplier=1 + shock,
        )
        open_sets[shock] = set(result.opened_warehouses)
        rows.append(
            {
                "scenario": f"demand_{shock:+.0%}",
                "shock": shock,
                "status": result.status,
                "total_cost": result.objective,
                "fixed_cost": result.fixed_cost,
                "variable_cost": result.variable_cost,
                "opened_warehouses": ",".join(result.opened_warehouses),
            }
        )

    if open_sets:
        robust = sorted(set.intersection(*open_sets.values())) if all(open_sets.values()) else []
        ever_open = sorted(set.union(*open_sets.values()))
    else:
        robust, ever_open = [], []
    marginal = sorted(set(ever_open) - set(robust))
    return pd.DataFrame(rows), robust, marginal


def fixed_cost_sweep(suppliers, warehouses, demand, arcs_sw, arcs_wd):
    rows = []
    base_fixed = warehouses.set_index("warehouse_id")["fixed_cost"].to_dict()
    for warehouse_id in warehouses["warehouse_id"]:
        for multiplier in config.FIXED_COST_MULTIPLIERS:
            scenario_warehouses = warehouses.copy()
            scenario_warehouses["fixed_cost"] = scenario_warehouses["fixed_cost"].astype(float)
            mask = scenario_warehouses["warehouse_id"] == warehouse_id
            scenario_warehouses.loc[mask, "fixed_cost"] = base_fixed[warehouse_id] * multiplier
            result = solve_network(suppliers, scenario_warehouses, demand, arcs_sw, arcs_wd)
            rows.append(
                {
                    "warehouse_id": warehouse_id,
                    "fixed_cost_multiplier": multiplier,
                    "scenario_fixed_cost": base_fixed[warehouse_id] * multiplier,
                    "status": result.status,
                    "total_cost": result.objective,
                    "is_open": warehouse_id in result.opened_warehouses,
                    "opened_warehouses": ",".join(result.opened_warehouses),
                }
            )
    sweep = pd.DataFrame(rows)
    thresholds = []
    for warehouse_id, group in sweep.groupby("warehouse_id"):
        open_rows = group[group["is_open"]]
        closed_rows = group[~group["is_open"]]
        thresholds.append(
            {
                "warehouse_id": warehouse_id,
                "lowest_open_cost": open_rows["scenario_fixed_cost"].min() if not open_rows.empty else np.nan,
                "highest_open_cost": open_rows["scenario_fixed_cost"].max() if not open_rows.empty else np.nan,
                "first_closed_cost": closed_rows["scenario_fixed_cost"].min() if not closed_rows.empty else np.nan,
            }
        )
    return sweep, pd.DataFrame(thresholds)


def capacity_sensitivity(suppliers, warehouses, demand, arcs_sw, arcs_wd, base_cost):
    result = solve_network(
        suppliers,
        warehouses,
        demand,
        arcs_sw,
        arcs_wd,
        capacity_multiplier=0.8,
    )
    increase = None
    if result.objective and base_cost:
        increase = 100 * (result.objective - base_cost) / base_cost
    return pd.DataFrame(
        [
            {
                "scenario": "warehouse_capacity_-20%",
                "status": result.status,
                "total_cost": result.objective,
                "cost_increase_pct": increase,
                "opened_warehouses": ",".join(result.opened_warehouses),
            }
        ]
    )


def service_level_sweep(suppliers, warehouses, demand, arcs_sw, arcs_wd):
    rows = []
    for distance_limit in config.SERVICE_DISTANCE_LIMITS:
        result = solve_network(
            suppliers,
            warehouses,
            demand,
            arcs_sw,
            arcs_wd,
            service_distance_limit=distance_limit,
        )
        rows.append(
            {
                "max_distance": distance_limit,
                "status": result.status,
                "total_cost": result.objective,
                "fixed_cost": result.fixed_cost,
                "variable_cost": result.variable_cost,
                "opened_warehouses": ",".join(result.opened_warehouses),
            }
        )
    return pd.DataFrame(rows)


def pareto_emissions(suppliers, warehouses, demand, arcs_sw, arcs_wd):
    rows = []
    for price in config.EMISSION_PRICE_GRID:
        result = solve_network(
            suppliers,
            warehouses,
            demand,
            arcs_sw,
            arcs_wd,
            emission_price=price,
        )
        emissions = None
        if result.flows:
            sw_em = arcs_sw.set_index(["supplier_id", "warehouse_id"])["emission_kg_per_unit"].to_dict()
            wd_em = arcs_wd.set_index(["warehouse_id", "demand_id"])["emission_kg_per_unit"].to_dict()
            emissions = sum(
                row["flow"] * (sw_em[(row["supplier_id"], row["warehouse_id"])] + wd_em[(row["warehouse_id"], row["demand_id"])])
                for row in result.flows
            )
        rows.append(
            {
                "emission_price_per_ton": price,
                "status": result.status,
                "total_cost": result.objective,
                "emissions_kg": emissions,
                "opened_warehouses": ",".join(result.opened_warehouses),
            }
        )
    return pd.DataFrame(rows)


def safety_stock_by_open_warehouse(demand, flows):
    if not flows:
        return pd.DataFrame()
    flow_df = pd.DataFrame(flows)
    warehouse_demand = flow_df.groupby("warehouse_id")["flow"].sum().reset_index(name="assigned_demand")
    warehouse_demand["daily_mean"] = warehouse_demand["assigned_demand"] / 30
    warehouse_demand["daily_std"] = warehouse_demand["daily_mean"] * config.DEMAND_CV
    warehouse_demand["safety_stock"] = (
        config.SAFETY_STOCK_SERVICE_Z
        * warehouse_demand["daily_std"]
        * np.sqrt(config.LEAD_TIME_DAYS)
    )
    return warehouse_demand


def run_sensitivity_suite(suppliers, warehouses, demand, arcs_sw, arcs_wd, optimal_result):
    demand_df, robust, marginal = demand_shock_analysis(suppliers, warehouses, demand, arcs_sw, arcs_wd)
    fixed_sweep_df, fixed_threshold_df = fixed_cost_sweep(suppliers, warehouses, demand, arcs_sw, arcs_wd)
    capacity_df = capacity_sensitivity(suppliers, warehouses, demand, arcs_sw, arcs_wd, optimal_result.objective)
    service_df = service_level_sweep(suppliers, warehouses, demand, arcs_sw, arcs_wd)
    emissions_df = pareto_emissions(suppliers, warehouses, demand, arcs_sw, arcs_wd)
    safety_stock_df = safety_stock_by_open_warehouse(demand, optimal_result.flows)

    return {
        "demand_shocks": demand_df,
        "robust_warehouses": robust,
        "marginal_warehouses": marginal,
        "fixed_cost_sweep": fixed_sweep_df,
        "fixed_cost_thresholds": fixed_threshold_df,
        "capacity": capacity_df,
        "service_level": service_df,
        "emissions": emissions_df,
        "safety_stock": safety_stock_df,
    }
