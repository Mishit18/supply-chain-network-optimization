from dataclasses import dataclass

import pulp

import config


@dataclass
class OptimizationResult:
    status: str
    objective: float | None
    fixed_cost: float | None
    variable_cost: float | None
    opened_warehouses: list[str]
    warehouse_decisions: dict[str, float]
    flows: list[dict]
    demand_duals: dict[str, float]
    model: pulp.LpProblem


def _solver(solver_name="CBC", msg=False, time_limit=config.CBC_TIME_LIMIT_SECONDS):
    if solver_name.upper() == "GUROBI":
        return pulp.GUROBI_CMD(msg=msg, timeLimit=time_limit)
    return pulp.PULP_CBC_CMD(
        msg=msg,
        timeLimit=time_limit,
        gapRel=config.CBC_MIP_GAP,
    )


def solve_network(
    suppliers,
    warehouses,
    demand,
    arcs_sw,
    arcs_wd,
    solver_name="CBC",
    msg=False,
    time_limit=config.CBC_TIME_LIMIT_SECONDS,
    fixed_open=None,
    assigned_warehouse_by_demand=None,
    demand_multiplier=1.0,
    capacity_multiplier=1.0,
    fixed_cost_multiplier=1.0,
    service_distance_limit=None,
    emission_price=0.0,
    relax_integrality=False,
):
    supplier_ids = suppliers["supplier_id"].tolist()
    warehouse_ids = warehouses["warehouse_id"].tolist()
    demand_ids = demand["demand_id"].tolist()

    demand_map = {
        row.demand_id: float(row.demand) * demand_multiplier
        for row in demand.itertuples(index=False)
    }
    supplier_capacity = {
        row.supplier_id: float(row.capacity)
        for row in suppliers.itertuples(index=False)
    }
    warehouse_capacity = {
        row.warehouse_id: float(row.capacity) * capacity_multiplier
        for row in warehouses.itertuples(index=False)
    }
    fixed_cost = {
        row.warehouse_id: float(row.fixed_cost) * fixed_cost_multiplier
        for row in warehouses.itertuples(index=False)
    }

    sw_cost = arcs_sw.set_index(["supplier_id", "warehouse_id"])["unit_cost"].to_dict()
    wd_cost = arcs_wd.set_index(["warehouse_id", "demand_id"])["unit_cost"].to_dict()
    sw_emission = arcs_sw.set_index(["supplier_id", "warehouse_id"])["emission_kg_per_unit"].to_dict()
    wd_emission = arcs_wd.set_index(["warehouse_id", "demand_id"])["emission_kg_per_unit"].to_dict()
    wd_distance = arcs_wd.set_index(["warehouse_id", "demand_id"])["distance"].to_dict()

    problem = pulp.LpProblem("capacitated_facility_location_transportation", pulp.LpMinimize)
    y_category = pulp.LpContinuous if relax_integrality else pulp.LpBinary
    y = pulp.LpVariable.dicts("open", warehouse_ids, lowBound=0, upBound=1, cat=y_category)
    x = pulp.LpVariable.dicts("flow", (supplier_ids, warehouse_ids, demand_ids), lowBound=0, cat=pulp.LpContinuous)

    route_terms = []
    for i in supplier_ids:
        for j in warehouse_ids:
            for k in demand_ids:
                route_cost = sw_cost[(i, j)] + wd_cost[(j, k)]
                emission_cost = emission_price * (sw_emission[(i, j)] + wd_emission[(j, k)]) / 1000
                route_terms.append((route_cost + emission_cost) * x[i][j][k])

    problem += (
        pulp.lpSum(fixed_cost[j] * y[j] for j in warehouse_ids) + pulp.lpSum(route_terms),
        "total_cost",
    )

    for k in demand_ids:
        problem += (
            pulp.lpSum(x[i][j][k] for i in supplier_ids for j in warehouse_ids) == demand_map[k],
            f"demand_{k}",
        )

    for i in supplier_ids:
        problem += (
            pulp.lpSum(x[i][j][k] for j in warehouse_ids for k in demand_ids) <= supplier_capacity[i],
            f"supplier_capacity_{i}",
        )

    for j in warehouse_ids:
        problem += (
            pulp.lpSum(x[i][j][k] for i in supplier_ids for k in demand_ids) <= warehouse_capacity[j] * y[j],
            f"warehouse_capacity_{j}",
        )

    for i in supplier_ids:
        for j in warehouse_ids:
            for k in demand_ids:
                problem += x[i][j][k] <= demand_map[k] * y[j], f"link_{i}_{j}_{k}"
                if assigned_warehouse_by_demand and assigned_warehouse_by_demand.get(k) != j:
                    problem += x[i][j][k] == 0, f"assignment_{i}_{j}_{k}"
                if service_distance_limit is not None and wd_distance[(j, k)] > service_distance_limit:
                    problem += x[i][j][k] == 0, f"service_limit_{i}_{j}_{k}"

    if fixed_open is not None:
        fixed_open = set(fixed_open)
        for j in warehouse_ids:
            problem += y[j] == (1 if j in fixed_open else 0), f"fix_open_{j}"

    status_code = problem.solve(_solver(solver_name, msg=msg, time_limit=time_limit))
    status = pulp.LpStatus[status_code]

    if status not in {"Optimal", "Feasible"}:
        return OptimizationResult(status, None, None, None, [], {}, [], {}, problem)

    y_values = {j: float(pulp.value(y[j])) for j in warehouse_ids}
    opened = [j for j, value in y_values.items() if value > 0.5]

    flow_records = []
    variable_cost = 0.0
    for i in supplier_ids:
        for j in warehouse_ids:
            for k in demand_ids:
                value = float(pulp.value(x[i][j][k]) or 0)
                if value > 1e-6:
                    unit_route_cost = sw_cost[(i, j)] + wd_cost[(j, k)]
                    variable_cost += unit_route_cost * value
                    flow_records.append(
                        {
                            "supplier_id": i,
                            "warehouse_id": j,
                            "demand_id": k,
                            "flow": value,
                            "unit_cost": unit_route_cost,
                            "route_cost": unit_route_cost * value,
                        }
                    )

    fixed_total = sum(fixed_cost[j] * y_values[j] for j in warehouse_ids)
    demand_duals = {
        name.replace("demand_", ""): float(constraint.pi)
        for name, constraint in problem.constraints.items()
        if name.startswith("demand_") and constraint.pi is not None
    }

    return OptimizationResult(
        status=status,
        objective=float(pulp.value(problem.objective)),
        fixed_cost=float(fixed_total),
        variable_cost=float(variable_cost),
        opened_warehouses=opened,
        warehouse_decisions=y_values,
        flows=flow_records,
        demand_duals=demand_duals,
        model=problem,
    )


def diagnose_feasibility(suppliers, warehouses, demand, capacity_multiplier=1.0):
    total_supply = float(suppliers["capacity"].sum())
    total_demand = float(demand["demand"].sum())
    total_warehouse_capacity = float(warehouses["capacity"].sum()) * capacity_multiplier
    return {
        "total_supply": total_supply,
        "total_demand": total_demand,
        "total_warehouse_capacity": total_warehouse_capacity,
        "supply_surplus": total_supply - total_demand,
        "warehouse_capacity_surplus": total_warehouse_capacity - total_demand,
        "basic_feasible": total_supply >= total_demand and total_warehouse_capacity >= total_demand,
    }
