def validate_inputs(suppliers, warehouses, demand, arcs_sw, arcs_wd):
    errors = []

    required_supplier_cols = {"supplier_id", "capacity", "x", "y"}
    required_warehouse_cols = {"warehouse_id", "capacity", "fixed_cost", "x", "y", "tier"}
    required_demand_cols = {"demand_id", "demand", "x", "y"}
    required_sw_cols = {"supplier_id", "warehouse_id", "unit_cost", "distance"}
    required_wd_cols = {"warehouse_id", "demand_id", "unit_cost", "distance"}

    for name, frame, required in [
        ("suppliers", suppliers, required_supplier_cols),
        ("warehouses", warehouses, required_warehouse_cols),
        ("demand", demand, required_demand_cols),
        ("supplier_to_warehouse arcs", arcs_sw, required_sw_cols),
        ("warehouse_to_demand arcs", arcs_wd, required_wd_cols),
    ]:
        missing = required - set(frame.columns)
        if missing:
            errors.append(f"{name} missing columns: {', '.join(sorted(missing))}")

    if errors:
        return errors

    if suppliers["supplier_id"].duplicated().any():
        errors.append("supplier_id values must be unique")
    if warehouses["warehouse_id"].duplicated().any():
        errors.append("warehouse_id values must be unique")
    if demand["demand_id"].duplicated().any():
        errors.append("demand_id values must be unique")

    if (suppliers["capacity"] < 0).any():
        errors.append("supplier capacities must be non-negative")
    if (warehouses["capacity"] < 0).any():
        errors.append("warehouse capacities must be non-negative")
    if (warehouses["fixed_cost"] < 0).any():
        errors.append("warehouse fixed costs must be non-negative")
    if (demand["demand"] < 0).any():
        errors.append("demand values must be non-negative")
    if (arcs_sw["unit_cost"] < 0).any() or (arcs_wd["unit_cost"] < 0).any():
        errors.append("transportation unit costs must be non-negative")

    expected_sw = len(suppliers) * len(warehouses)
    expected_wd = len(warehouses) * len(demand)
    if len(arcs_sw.drop_duplicates(["supplier_id", "warehouse_id"])) != expected_sw:
        errors.append("supplier-to-warehouse arcs must cover every supplier/warehouse pair exactly once")
    if len(arcs_wd.drop_duplicates(["warehouse_id", "demand_id"])) != expected_wd:
        errors.append("warehouse-to-demand arcs must cover every warehouse/demand pair exactly once")

    if suppliers["capacity"].sum() < demand["demand"].sum():
        errors.append("total supplier capacity is lower than total demand")
    if warehouses["capacity"].sum() < demand["demand"].sum():
        errors.append("total warehouse capacity is lower than total demand")

    return errors


def raise_for_invalid_inputs(suppliers, warehouses, demand, arcs_sw, arcs_wd):
    errors = validate_inputs(suppliers, warehouses, demand, arcs_sw, arcs_wd)
    if errors:
        joined = "\n- ".join(errors)
        raise ValueError(f"Invalid supply chain inputs:\n- {joined}")
