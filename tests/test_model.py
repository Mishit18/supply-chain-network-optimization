from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd

from model import solve_network


def test_tiny_network_opens_lowest_total_cost_warehouse():
    suppliers = pd.DataFrame(
        [
            {"supplier_id": "S01", "x": 0, "y": 0, "capacity": 100},
        ]
    )
    warehouses = pd.DataFrame(
        [
            {"warehouse_id": "W01", "x": 0, "y": 0, "tier": "small", "fixed_cost": 20, "capacity": 100},
            {"warehouse_id": "W02", "x": 100, "y": 0, "tier": "small", "fixed_cost": 500, "capacity": 100},
        ]
    )
    demand = pd.DataFrame(
        [
            {"demand_id": "D01", "x": 0, "y": 0, "base_demand": 10, "seasonal_multiplier": 1, "demand": 10},
            {"demand_id": "D02", "x": 10, "y": 0, "base_demand": 20, "seasonal_multiplier": 1, "demand": 20},
        ]
    )
    arcs_sw = pd.DataFrame(
        [
            {"supplier_id": "S01", "warehouse_id": "W01", "distance": 0, "unit_cost": 1, "emission_kg_per_unit": 0},
            {"supplier_id": "S01", "warehouse_id": "W02", "distance": 100, "unit_cost": 25, "emission_kg_per_unit": 0},
        ]
    )
    arcs_wd = pd.DataFrame(
        [
            {"warehouse_id": "W01", "demand_id": "D01", "distance": 0, "unit_cost": 1, "emission_kg_per_unit": 0},
            {"warehouse_id": "W01", "demand_id": "D02", "distance": 10, "unit_cost": 2, "emission_kg_per_unit": 0},
            {"warehouse_id": "W02", "demand_id": "D01", "distance": 100, "unit_cost": 30, "emission_kg_per_unit": 0},
            {"warehouse_id": "W02", "demand_id": "D02", "distance": 90, "unit_cost": 28, "emission_kg_per_unit": 0},
        ]
    )

    result = solve_network(suppliers, warehouses, demand, arcs_sw, arcs_wd, time_limit=10)

    assert result.status == "Optimal"
    assert result.opened_warehouses == ["W01"]
    assert round(sum(row["flow"] for row in result.flows), 6) == 30
    assert round(result.objective, 6) == 100
