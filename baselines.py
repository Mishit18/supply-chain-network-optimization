import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

from model import solve_network


def _ensure_capacity(open_set, warehouses, total_demand):
    open_set = set(open_set)
    capacity = warehouses.set_index("warehouse_id")["capacity"].to_dict()
    fixed = warehouses.set_index("warehouse_id")["fixed_cost"].to_dict()
    while sum(capacity[j] for j in open_set) < total_demand:
        candidates = [j for j in capacity if j not in open_set]
        if not candidates:
            break
        best = min(candidates, key=lambda j: fixed[j] / max(capacity[j], 1))
        open_set.add(best)
    return sorted(open_set)


def greedy_nearest_warehouse(suppliers, warehouses, demand, arcs_sw, arcs_wd):
    distances = arcs_wd.set_index(["warehouse_id", "demand_id"])["distance"].to_dict()
    warehouse_ids = warehouses["warehouse_id"].tolist()
    assignment = {}
    for demand_id in demand["demand_id"]:
        assignment[demand_id] = min(warehouse_ids, key=lambda j: distances[(j, demand_id)])

    open_set = _ensure_capacity(set(assignment.values()), warehouses, demand["demand"].sum())
    result = solve_network(
        suppliers,
        warehouses,
        demand,
        arcs_sw,
        arcs_wd,
        fixed_open=open_set,
        assigned_warehouse_by_demand=assignment,
    )
    if result.status not in {"Optimal", "Feasible"}:
        result = solve_network(suppliers, warehouses, demand, arcs_sw, arcs_wd, fixed_open=open_set)
    return "greedy_nearest", result


def open_all(suppliers, warehouses, demand, arcs_sw, arcs_wd):
    return "open_all", solve_network(
        suppliers,
        warehouses,
        demand,
        arcs_sw,
        arcs_wd,
        fixed_open=warehouses["warehouse_id"].tolist(),
    )


def kmeans_baseline(suppliers, warehouses, demand, arcs_sw, arcs_wd, n_clusters=4):
    coordinates = demand[["x", "y"]].to_numpy()
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=20)
    kmeans.fit(coordinates, sample_weight=demand["demand"].to_numpy())

    wh_coords = warehouses.set_index("warehouse_id")[["x", "y"]]
    open_set = set()
    for center in kmeans.cluster_centers_:
        nearest = min(
            wh_coords.index,
            key=lambda j: np.linalg.norm(wh_coords.loc[j].to_numpy() - center),
        )
        open_set.add(nearest)

    open_set = _ensure_capacity(open_set, warehouses, demand["demand"].sum())
    return "kmeans", solve_network(suppliers, warehouses, demand, arcs_sw, arcs_wd, fixed_open=open_set)


def run_baselines(suppliers, warehouses, demand, arcs_sw, arcs_wd, optimal_result):
    rows = []
    baseline_results = {}
    for name, result in [
        greedy_nearest_warehouse(suppliers, warehouses, demand, arcs_sw, arcs_wd),
        open_all(suppliers, warehouses, demand, arcs_sw, arcs_wd),
        kmeans_baseline(suppliers, warehouses, demand, arcs_sw, arcs_wd),
    ]:
        baseline_results[name] = result
        reduction = None
        if result.objective and optimal_result.objective:
            reduction = 100 * (result.objective - optimal_result.objective) / result.objective
        rows.append(
            {
                "method": name,
                "status": result.status,
                "total_cost": result.objective,
                "fixed_cost": result.fixed_cost,
                "variable_cost": result.variable_cost,
                "opened_count": len(result.opened_warehouses),
                "opened_warehouses": ",".join(result.opened_warehouses),
                "optimal_cost_reduction_pct": reduction,
            }
        )

    summary = pd.DataFrame(rows)
    return summary, baseline_results
