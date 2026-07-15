from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_generation import generate_synthetic_data
from scaling import aggregate_demand_nodes, generate_large_demand_cloud, run_scale_demo


def test_demand_aggregation_preserves_total_demand():
    _, warehouses, _, _, _ = generate_synthetic_data(seed=11, save=False)
    customers = generate_large_demand_cloud(warehouses, n_nodes=120, seed=12)
    zones = aggregate_demand_nodes(customers, n_zones=12, seed=13)

    assert zones.shape[0] == 12
    assert zones["demand"].sum() == customers["demand"].sum()
    assert zones["customer_count"].sum() == customers.shape[0]


def test_scale_demo_solves_aggregated_instance():
    suppliers, warehouses, _, arcs_sw, _ = generate_synthetic_data(seed=21, save=False)
    summary, customers, zones = run_scale_demo(suppliers, warehouses, arcs_sw, n_customers=90, n_zones=9)

    row = summary.iloc[0]
    assert row.status == "Optimal"
    assert row.raw_customer_nodes == 90
    assert row.aggregated_zones == 9
    assert row.variables > 0
    assert customers["demand"].sum() == zones["demand"].sum()
