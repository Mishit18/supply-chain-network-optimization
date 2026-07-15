import numpy as np
import pandas as pd

import config


def euclidean_distance(a_x, a_y, b_x, b_y):
    return float(np.hypot(a_x - b_x, a_y - b_y))


def road_adjusted_distance(a_x, a_y, b_x, b_y, circuity=1.18):
    euclidean = euclidean_distance(a_x, a_y, b_x, b_y)
    manhattan = abs(a_x - b_x) + abs(a_y - b_y)
    return float(circuity * (0.75 * euclidean + 0.25 * manhattan))


def _node_ids(prefix, n):
    return [f"{prefix}{idx:02d}" for idx in range(1, n + 1)]


def generate_synthetic_data(seed=config.RANDOM_SEED, save=True):
    rng = np.random.default_rng(seed)
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)

    supplier_ids = _node_ids("S", config.N_SUPPLIERS)
    warehouse_ids = _node_ids("W", config.N_WAREHOUSES)
    demand_ids = _node_ids("D", config.N_DEMAND_NODES)

    suppliers = pd.DataFrame(
        {
            "supplier_id": supplier_ids,
            "x": rng.uniform(0, config.GRID_SIZE, config.N_SUPPLIERS).round(2),
            "y": rng.uniform(0, config.GRID_SIZE, config.N_SUPPLIERS).round(2),
        }
    )

    tiers = rng.choice(["small", "medium", "large"], size=config.N_WAREHOUSES, p=[0.35, 0.40, 0.25])
    warehouses = pd.DataFrame(
        {
            "warehouse_id": warehouse_ids,
            "x": rng.uniform(0, config.GRID_SIZE, config.N_WAREHOUSES).round(2),
            "y": rng.uniform(0, config.GRID_SIZE, config.N_WAREHOUSES).round(2),
            "tier": tiers,
        }
    )

    base_demand = rng.poisson(config.BASE_DEMAND_LAMBDA, config.N_DEMAND_NODES)
    seasonal_multiplier = rng.uniform(
        config.SEASONAL_MULTIPLIER_LOW,
        config.SEASONAL_MULTIPLIER_HIGH,
        config.N_DEMAND_NODES,
    )
    anchor_idx = rng.integers(0, config.N_WAREHOUSES, config.N_DEMAND_NODES)
    angles = rng.uniform(0, 2 * np.pi, config.N_DEMAND_NODES)
    radii = rng.uniform(25, 175, config.N_DEMAND_NODES)
    anchor_x = warehouses.loc[anchor_idx, "x"].to_numpy()
    anchor_y = warehouses.loc[anchor_idx, "y"].to_numpy()
    demand_x = np.clip(anchor_x + radii * np.cos(angles), 0, config.GRID_SIZE)
    demand_y = np.clip(anchor_y + radii * np.sin(angles), 0, config.GRID_SIZE)

    demand = pd.DataFrame(
        {
            "demand_id": demand_ids,
            "x": demand_x.round(2),
            "y": demand_y.round(2),
            "base_demand": base_demand,
            "seasonal_multiplier": seasonal_multiplier.round(3),
        }
    )
    demand["demand"] = np.ceil(demand["base_demand"] * demand["seasonal_multiplier"]).astype(int)

    total_demand = int(demand["demand"].sum())

    raw_supply = rng.dirichlet(np.ones(config.N_SUPPLIERS))
    supplier_capacity = np.ceil(raw_supply * total_demand * config.SUPPLIER_CAPACITY_BUFFER).astype(int)
    supplier_capacity[-1] += int(np.ceil(total_demand * config.SUPPLIER_CAPACITY_BUFFER - supplier_capacity.sum()))
    suppliers["capacity"] = supplier_capacity

    fixed_costs = []
    capacities = []
    for tier in warehouses["tier"]:
        fixed_low, fixed_high = config.FIXED_COST_BY_TIER[tier]
        cap_low, cap_high = config.WAREHOUSE_TIER_CAPACITY_SHARE[tier]
        fixed_costs.append(int(rng.integers(fixed_low, fixed_high + 1)))
        capacities.append(int(np.ceil(rng.uniform(cap_low, cap_high) * total_demand * config.WAREHOUSE_CAPACITY_BUFFER)))

    warehouses["fixed_cost"] = fixed_costs
    warehouses["capacity"] = capacities

    if warehouses["capacity"].sum() < total_demand:
        shortage = int(total_demand - warehouses["capacity"].sum())
        largest_idx = warehouses["capacity"].idxmax()
        warehouses.loc[largest_idx, "capacity"] += shortage

    supplier_to_warehouse = []
    for _, s in suppliers.iterrows():
        for _, w in warehouses.iterrows():
            euclidean = euclidean_distance(s.x, s.y, w.x, w.y)
            distance = road_adjusted_distance(
                s.x,
                s.y,
                w.x,
                w.y,
                rng.uniform(config.ROAD_CIRCUITY_LOW, config.ROAD_CIRCUITY_HIGH),
            )
            weight = rng.uniform(config.WEIGHT_FACTOR_LOW, config.WEIGHT_FACTOR_HIGH)
            supplier_to_warehouse.append(
                {
                    "supplier_id": s.supplier_id,
                    "warehouse_id": w.warehouse_id,
                    "euclidean_distance": round(euclidean, 2),
                    "distance": round(distance, 2),
                    "unit_cost": round(distance * config.SUPPLIER_UNIT_COST_PER_KM * weight, 2),
                    "emission_kg_per_unit": round(distance * config.EMISSION_KG_PER_KM_UNIT, 4),
                }
            )

    warehouse_to_demand = []
    for _, w in warehouses.iterrows():
        for _, d in demand.iterrows():
            euclidean = euclidean_distance(w.x, w.y, d.x, d.y)
            distance = road_adjusted_distance(
                w.x,
                w.y,
                d.x,
                d.y,
                rng.uniform(config.ROAD_CIRCUITY_LOW, config.ROAD_CIRCUITY_HIGH),
            )
            weight = rng.uniform(config.WEIGHT_FACTOR_LOW, config.WEIGHT_FACTOR_HIGH)
            warehouse_to_demand.append(
                {
                    "warehouse_id": w.warehouse_id,
                    "demand_id": d.demand_id,
                    "euclidean_distance": round(euclidean, 2),
                    "distance": round(distance, 2),
                    "unit_cost": round(distance * config.LAST_MILE_UNIT_COST_PER_KM * weight, 2),
                    "emission_kg_per_unit": round(distance * config.EMISSION_KG_PER_KM_UNIT, 4),
                }
            )

    arcs_sw = pd.DataFrame(supplier_to_warehouse)
    arcs_wd = pd.DataFrame(warehouse_to_demand)

    if save:
        suppliers.to_csv(config.DATA_DIR / "suppliers.csv", index=False)
        warehouses.to_csv(config.DATA_DIR / "warehouses.csv", index=False)
        demand.to_csv(config.DATA_DIR / "demand_nodes.csv", index=False)
        arcs_sw.to_csv(config.DATA_DIR / "supplier_to_warehouse.csv", index=False)
        arcs_wd.to_csv(config.DATA_DIR / "warehouse_to_demand.csv", index=False)

    return suppliers, warehouses, demand, arcs_sw, arcs_wd


def load_data():
    paths = [
        config.DATA_DIR / "suppliers.csv",
        config.DATA_DIR / "warehouses.csv",
        config.DATA_DIR / "demand_nodes.csv",
        config.DATA_DIR / "supplier_to_warehouse.csv",
        config.DATA_DIR / "warehouse_to_demand.csv",
    ]
    if not all(path.exists() for path in paths):
        return generate_synthetic_data(save=True)

    return tuple(pd.read_csv(path) for path in paths)


if __name__ == "__main__":
    generate_synthetic_data()
    print(f"Data written to {config.DATA_DIR}")
