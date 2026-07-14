from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config
from data_generation import generate_synthetic_data
from validation import validate_inputs


def test_valid_generated_inputs_pass_validation():
    suppliers, warehouses, demand, arcs_sw, arcs_wd = generate_synthetic_data(seed=config.RANDOM_SEED, save=False)

    assert validate_inputs(suppliers, warehouses, demand, arcs_sw, arcs_wd) == []


def test_validation_flags_capacity_shortage():
    suppliers, warehouses, demand, arcs_sw, arcs_wd = generate_synthetic_data(seed=config.RANDOM_SEED, save=False)
    suppliers["capacity"] = 0

    errors = validate_inputs(suppliers, warehouses, demand, arcs_sw, arcs_wd)

    assert "total supplier capacity is lower than total demand" in errors
