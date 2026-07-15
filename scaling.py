import time

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

import config
from data_generation import road_adjusted_distance
from model import solve_network


def generate_large_demand_cloud(warehouses, n_nodes=config.SCALE_DEMO_DEMAND_NODES, seed=config.RANDOM_SEED + 99):
    rng = np.random.default_rng(seed)
    anchor_idx = rng.integers(0, len(warehouses), n_nodes)
    angles = rng.uniform(0, 2 * np.pi, n_nodes)
    radii = rng.gamma(shape=2.0, scale=70.0, size=n_nodes)
    anchor_x = warehouses.iloc[anchor_idx]["x"].to_numpy()
    anchor_y = warehouses.iloc[anchor_idx]["y"].to_numpy()

    x = np.clip(anchor_x + radii * np.cos(angles), 0, config.GRID_SIZE)
    y = np.clip(anchor_y + radii * np.sin(angles), 0, config.GRID_SIZE)
    demand = rng.poisson(config.BASE_DEMAND_LAMBDA / 4, n_nodes) + 1
    return pd.DataFrame(
        {
            "customer_id": [f"C{idx:05d}" for idx in range(1, n_nodes + 1)],
            "x": x.round(2),
            "y": y.round(2),
            "demand": demand.astype(int),
        }
    )


def aggregate_demand_nodes(customer_demand, n_zones=config.SCALE_DEMO_AGGREGATED_ZONES, seed=config.RANDOM_SEED):
    n_zones = min(n_zones, len(customer_demand))
    kmeans = KMeans(n_clusters=n_zones, random_state=seed, n_init=10)
    labels = kmeans.fit_predict(
        customer_demand[["x", "y"]],
        sample_weight=customer_demand["demand"],
    )
    assigned = customer_demand.copy()
    assigned["zone"] = labels

    rows = []
    for zone, group in assigned.groupby("zone"):
        weights = group["demand"].to_numpy()
        rows.append(
            {
                "demand_id": f"Z{zone + 1:03d}",
                "x": np.average(group["x"], weights=weights),
                "y": np.average(group["y"], weights=weights),
                "base_demand": group["demand"].sum(),
                "seasonal_multiplier": 1.0,
                "demand": int(group["demand"].sum()),
                "customer_count": int(group.shape[0]),
            }
        )
    return pd.DataFrame(rows).sort_values("demand_id").reset_index(drop=True)


def build_warehouse_to_zone_arcs(warehouses, zones, seed=config.RANDOM_SEED + 101):
    rng = np.random.default_rng(seed)
    rows = []
    for _, w in warehouses.iterrows():
        for _, z in zones.iterrows():
            distance = road_adjusted_distance(
                w.x,
                w.y,
                z.x,
                z.y,
                rng.uniform(config.ROAD_CIRCUITY_LOW, config.ROAD_CIRCUITY_HIGH),
            )
            weight = rng.uniform(config.WEIGHT_FACTOR_LOW, config.WEIGHT_FACTOR_HIGH)
            rows.append(
                {
                    "warehouse_id": w.warehouse_id,
                    "demand_id": z.demand_id,
                    "distance": round(distance, 2),
                    "unit_cost": round(distance * config.LAST_MILE_UNIT_COST_PER_KM * weight, 2),
                    "emission_kg_per_unit": round(distance * config.EMISSION_KG_PER_KM_UNIT, 4),
                }
            )
    return pd.DataFrame(rows)


def run_scale_demo(suppliers, warehouses, arcs_sw, n_customers=None, n_zones=None):
    n_customers = n_customers or config.SCALE_DEMO_DEMAND_NODES
    n_zones = n_zones or config.SCALE_DEMO_AGGREGATED_ZONES
    customers = generate_large_demand_cloud(warehouses, n_nodes=n_customers)
    zones = aggregate_demand_nodes(customers, n_zones=n_zones)

    total_zone_demand = zones["demand"].sum()
    scaled_suppliers = suppliers.copy()
    scaled_warehouses = warehouses.copy()
    if scaled_suppliers["capacity"].sum() < total_zone_demand * 1.15:
        factor = total_zone_demand * 1.15 / scaled_suppliers["capacity"].sum()
        scaled_suppliers["capacity"] = np.ceil(scaled_suppliers["capacity"] * factor).astype(int)
    if scaled_warehouses["capacity"].sum() < total_zone_demand * 1.15:
        factor = total_zone_demand * 1.15 / scaled_warehouses["capacity"].sum()
        scaled_warehouses["capacity"] = np.ceil(scaled_warehouses["capacity"] * factor).astype(int)

    arcs_wz = build_warehouse_to_zone_arcs(scaled_warehouses, zones)
    started = time.perf_counter()
    result = solve_network(
        scaled_suppliers,
        scaled_warehouses,
        zones,
        arcs_sw,
        arcs_wz,
        time_limit=config.CBC_TIME_LIMIT_SECONDS,
    )
    elapsed = time.perf_counter() - started

    summary = pd.DataFrame(
        [
            {
                "raw_customer_nodes": n_customers,
                "aggregated_zones": zones.shape[0],
                "status": result.status,
                "objective": result.objective,
                "opened_count": len(result.opened_warehouses),
                "opened_warehouses": ",".join(result.opened_warehouses),
                "variables": result.variable_count,
                "constraints": result.constraint_count,
                "solve_seconds": round(elapsed, 2),
                "total_demand": int(total_zone_demand),
            }
        ]
    )
    return summary, customers, zones
