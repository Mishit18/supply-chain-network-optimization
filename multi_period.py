from dataclasses import dataclass

import pandas as pd
import pulp

import config
from model import _solver


@dataclass
class MultiPeriodResult:
    status: str
    objective: float | None
    period_summary: pd.DataFrame
    transition_summary: pd.DataFrame
    variable_count: int
    constraint_count: int


def solve_multi_period_network(
    suppliers,
    warehouses,
    demand,
    arcs_sw,
    arcs_wd,
    demand_growth=None,
    opening_switch_cost_rate=config.WAREHOUSE_OPENING_SWITCH_COST_RATE,
    closing_switch_cost_rate=config.WAREHOUSE_CLOSING_SWITCH_COST_RATE,
    time_limit=config.CBC_TIME_LIMIT_SECONDS,
    msg=False,
):
    demand_growth = demand_growth or config.MULTIPERIOD_DEMAND_GROWTH
    periods = list(range(len(demand_growth)))
    supplier_ids = suppliers["supplier_id"].tolist()
    warehouse_ids = warehouses["warehouse_id"].tolist()
    demand_ids = demand["demand_id"].tolist()

    demand_base = demand.set_index("demand_id")["demand"].to_dict()
    supplier_capacity = suppliers.set_index("supplier_id")["capacity"].to_dict()
    warehouse_capacity = warehouses.set_index("warehouse_id")["capacity"].to_dict()
    fixed_cost = warehouses.set_index("warehouse_id")["fixed_cost"].to_dict()
    sw_cost = arcs_sw.set_index(["supplier_id", "warehouse_id"])["unit_cost"].to_dict()
    wd_cost = arcs_wd.set_index(["warehouse_id", "demand_id"])["unit_cost"].to_dict()

    problem = pulp.LpProblem("multi_period_facility_location", pulp.LpMinimize)
    y = pulp.LpVariable.dicts("open", (warehouse_ids, periods), 0, 1, cat=pulp.LpBinary)
    open_switch = pulp.LpVariable.dicts("switch_open", (warehouse_ids, periods), 0, 1, cat=pulp.LpBinary)
    close_switch = pulp.LpVariable.dicts("switch_close", (warehouse_ids, periods), 0, 1, cat=pulp.LpBinary)
    x = pulp.LpVariable.dicts("flow", (supplier_ids, warehouse_ids, demand_ids, periods), lowBound=0)

    transport_terms = []
    for i in supplier_ids:
        for j in warehouse_ids:
            for k in demand_ids:
                for t in periods:
                    transport_terms.append((sw_cost[(i, j)] + wd_cost[(j, k)]) * x[i][j][k][t])

    fixed_terms = [fixed_cost[j] * y[j][t] for j in warehouse_ids for t in periods]
    switching_terms = []
    for j in warehouse_ids:
        for t in periods:
            switching_terms.append(fixed_cost[j] * opening_switch_cost_rate * open_switch[j][t])
            switching_terms.append(fixed_cost[j] * closing_switch_cost_rate * close_switch[j][t])

    problem += pulp.lpSum(fixed_terms + transport_terms + switching_terms), "total_multi_period_cost"

    for t, growth in enumerate(demand_growth):
        for k in demand_ids:
            period_demand = float(demand_base[k]) * growth
            problem += (
                pulp.lpSum(x[i][j][k][t] for i in supplier_ids for j in warehouse_ids) == period_demand,
                f"demand_{k}_period_{t}",
            )
            for i in supplier_ids:
                for j in warehouse_ids:
                    problem += x[i][j][k][t] <= period_demand * y[j][t], f"link_{i}_{j}_{k}_{t}"

        for i in supplier_ids:
            problem += (
                pulp.lpSum(x[i][j][k][t] for j in warehouse_ids for k in demand_ids)
                <= float(supplier_capacity[i]) * growth,
                f"supplier_capacity_{i}_period_{t}",
            )

        for j in warehouse_ids:
            problem += (
                pulp.lpSum(x[i][j][k][t] for i in supplier_ids for k in demand_ids)
                <= float(warehouse_capacity[j]) * y[j][t],
                f"warehouse_capacity_{j}_period_{t}",
            )

            if t == 0:
                problem += open_switch[j][t] >= y[j][t], f"initial_open_switch_{j}"
                problem += close_switch[j][t] == 0, f"initial_close_switch_{j}"
            else:
                problem += open_switch[j][t] >= y[j][t] - y[j][t - 1], f"open_switch_{j}_{t}"
                problem += close_switch[j][t] >= y[j][t - 1] - y[j][t], f"close_switch_{j}_{t}"

    status_code = problem.solve(_solver(msg=msg, time_limit=time_limit))
    status = pulp.LpStatus[status_code]
    if status not in {"Optimal", "Feasible"}:
        return MultiPeriodResult(status, None, pd.DataFrame(), pd.DataFrame(), len(problem.variables()), len(problem.constraints))

    period_rows = []
    transition_rows = []
    for t in periods:
        opened = [j for j in warehouse_ids if (pulp.value(y[j][t]) or 0) > 0.5]
        flow_total = sum(
            pulp.value(x[i][j][k][t]) or 0
            for i in supplier_ids
            for j in warehouse_ids
            for k in demand_ids
        )
        period_rows.append(
            {
                "period": t + 1,
                "demand_growth": demand_growth[t],
                "opened_count": len(opened),
                "opened_warehouses": ",".join(opened),
                "total_flow": flow_total,
            }
        )
        for j in warehouse_ids:
            transition_rows.append(
                {
                    "period": t + 1,
                    "warehouse_id": j,
                    "is_open": int((pulp.value(y[j][t]) or 0) > 0.5),
                    "opened_this_period": int((pulp.value(open_switch[j][t]) or 0) > 0.5),
                    "closed_this_period": int((pulp.value(close_switch[j][t]) or 0) > 0.5),
                }
            )

    return MultiPeriodResult(
        status=status,
        objective=float(pulp.value(problem.objective)),
        period_summary=pd.DataFrame(period_rows),
        transition_summary=pd.DataFrame(transition_rows),
        variable_count=len(problem.variables()),
        constraint_count=len(problem.constraints),
    )
