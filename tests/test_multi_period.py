from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_generation import generate_synthetic_data
from multi_period import solve_multi_period_network


def test_multi_period_extension_solves_small_generated_instance():
    suppliers, warehouses, demand, arcs_sw, arcs_wd = generate_synthetic_data(seed=7, save=False)
    suppliers = suppliers.head(2).copy()
    warehouses = warehouses.head(3).copy()
    demand = demand.head(6).copy()
    arcs_sw = arcs_sw[
        arcs_sw["supplier_id"].isin(suppliers["supplier_id"])
        & arcs_sw["warehouse_id"].isin(warehouses["warehouse_id"])
    ].copy()
    arcs_wd = arcs_wd[
        arcs_wd["warehouse_id"].isin(warehouses["warehouse_id"])
        & arcs_wd["demand_id"].isin(demand["demand_id"])
    ].copy()

    total_demand = demand["demand"].sum() * 1.1
    suppliers["capacity"] = total_demand
    warehouses["capacity"] = total_demand

    result = solve_multi_period_network(
        suppliers,
        warehouses,
        demand,
        arcs_sw,
        arcs_wd,
        demand_growth=[1.0, 1.1],
        time_limit=20,
    )

    assert result.status == "Optimal"
    assert result.objective > 0
    assert result.period_summary.shape[0] == 2
    assert result.variable_count > 0
    assert result.constraint_count > 0
