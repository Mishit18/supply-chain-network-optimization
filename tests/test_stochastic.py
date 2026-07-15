from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_generation import generate_synthetic_data
from stochastic import generate_node_level_demand_scenarios, run_monte_carlo_demand_analysis


def test_node_level_scenarios_preserve_demand_keys():
    _, _, demand, _, _ = generate_synthetic_data(seed=31, save=False)
    scenarios = generate_node_level_demand_scenarios(demand, n_scenarios=3, seed=32)

    assert len(scenarios) == 3
    assert set(scenarios[0]["demand"]) == set(demand["demand_id"])
    assert all(scenario["total_demand"] > 0 for scenario in scenarios)


def test_monte_carlo_outputs_stability_table():
    suppliers, warehouses, demand, arcs_sw, arcs_wd = generate_synthetic_data(seed=33, save=False)
    suppliers = suppliers.head(2).copy()
    warehouses = warehouses.head(3).copy()
    demand = demand.head(5).copy()
    arcs_sw = arcs_sw[
        arcs_sw["supplier_id"].isin(suppliers["supplier_id"])
        & arcs_sw["warehouse_id"].isin(warehouses["warehouse_id"])
    ].copy()
    arcs_wd = arcs_wd[
        arcs_wd["warehouse_id"].isin(warehouses["warehouse_id"])
        & arcs_wd["demand_id"].isin(demand["demand_id"])
    ].copy()

    required_capacity = demand["demand"].sum() * 1.8
    suppliers["capacity"] = required_capacity
    warehouses["capacity"] = required_capacity

    scenarios, stability = run_monte_carlo_demand_analysis(
        suppliers,
        warehouses,
        demand,
        arcs_sw,
        arcs_wd,
        n_scenarios=2,
    )

    assert scenarios.shape[0] == 2
    assert stability.shape[0] == warehouses.shape[0]
    assert stability["open_frequency"].between(0, 1).all()
