from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config
from data_generation import generate_synthetic_data
from model import diagnose_feasibility


def test_synthetic_data_shapes_and_feasibility():
    suppliers, warehouses, demand, arcs_sw, arcs_wd = generate_synthetic_data(seed=config.RANDOM_SEED, save=False)

    assert suppliers.shape[0] == config.N_SUPPLIERS
    assert warehouses.shape[0] == config.N_WAREHOUSES
    assert demand.shape[0] == config.N_DEMAND_NODES
    assert arcs_sw.shape[0] == config.N_SUPPLIERS * config.N_WAREHOUSES
    assert arcs_wd.shape[0] == config.N_WAREHOUSES * config.N_DEMAND_NODES

    feasibility = diagnose_feasibility(suppliers, warehouses, demand)
    assert feasibility["basic_feasible"]
    assert suppliers["capacity"].sum() >= demand["demand"].sum()
    assert warehouses["capacity"].sum() >= demand["demand"].sum()


def test_synthetic_data_is_reproducible():
    first = generate_synthetic_data(seed=config.RANDOM_SEED, save=False)
    second = generate_synthetic_data(seed=config.RANDOM_SEED, save=False)

    for first_df, second_df in zip(first, second):
        assert first_df.equals(second_df)
