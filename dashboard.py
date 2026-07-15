from pathlib import Path

import pandas as pd

try:
    import streamlit as st
except ImportError as exc:
    raise SystemExit(
        "Streamlit is not installed. Run: python -m pip install -r requirements-dashboard.txt"
    ) from exc

import config
from data_generation import load_data
from model import solve_network


st.set_page_config(page_title="Supply Chain Network Optimization", layout="wide")


def _read_csv(path):
    return pd.read_csv(path) if Path(path).exists() else pd.DataFrame()


def _money(value):
    return f"${value:,.0f}" if pd.notna(value) else "N/A"


metrics_path = config.RESULTS_DIR / "resume_metrics.json"
if not metrics_path.exists():
    st.title("Supply Chain Network Optimization")
    st.info("Run `python main.py` first to generate results and plots.")
    st.stop()

metrics = pd.read_json(metrics_path, typ="series")
baseline = _read_csv(config.RESULTS_DIR / "baseline_comparison.csv")
demand_shocks = _read_csv(config.RESULTS_DIR / "demand_shocks.csv")
service = _read_csv(config.RESULTS_DIR / "service_level.csv")
capacity = _read_csv(config.RESULTS_DIR / "capacity.csv")

st.title("Supply Chain Network Optimization")
st.caption("Capacitated facility location MILP with benchmarking, robustness analysis, and service-level tradeoffs.")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Optimal Cost", _money(metrics["optimal_total_cost"]))
col2.metric("Warehouses Opened", len(metrics["opened_warehouses"]))
col3.metric("Vs Greedy", f"{metrics['cost_reduction_vs_greedy_pct']:.2f}%")
col4.metric("Vs Open-All", f"{metrics['cost_reduction_vs_open_all_pct']:.2f}%")

left, right = st.columns([1.4, 1])
with left:
    st.subheader("Optimized Network")
    network_plot = config.PLOTS_DIR / "network_map.png"
    if network_plot.exists():
        st.image(str(network_plot), use_container_width=True)

with right:
    st.subheader("Selected Warehouses")
    st.write(", ".join(metrics["opened_warehouses"]))
    st.subheader("Robust Warehouses")
    st.write(", ".join(metrics["robust_warehouses"]))
    st.subheader("Marginal Warehouses")
    st.write(", ".join(metrics["marginal_warehouses"]))

st.subheader("Baseline Comparison")
if not baseline.empty:
    display = baseline.copy()
    display["total_cost"] = display["total_cost"].map(_money)
    display["optimal_cost_reduction_pct"] = display["optimal_cost_reduction_pct"].map(lambda x: f"{x:.2f}%")
    st.dataframe(
        display[["method", "status", "total_cost", "opened_count", "optimal_cost_reduction_pct"]],
        use_container_width=True,
        hide_index=True,
    )

chart_cols = st.columns(2)
with chart_cols[0]:
    st.subheader("Cost Breakdown")
    cost_plot = config.PLOTS_DIR / "cost_breakdown.png"
    if cost_plot.exists():
        st.image(str(cost_plot), use_container_width=True)
with chart_cols[1]:
    st.subheader("Service-Level Tradeoff")
    service_plot = config.PLOTS_DIR / "service_cost_tradeoff.png"
    if service_plot.exists():
        st.image(str(service_plot), use_container_width=True)

st.subheader("Demand Shock Robustness")
if not demand_shocks.empty:
    st.dataframe(demand_shocks, use_container_width=True, hide_index=True)

lower_cols = st.columns(2)
with lower_cols[0]:
    st.subheader("Sensitivity Tornado")
    tornado_plot = config.PLOTS_DIR / "sensitivity_tornado.png"
    if tornado_plot.exists():
        st.image(str(tornado_plot), use_container_width=True)
with lower_cols[1]:
    st.subheader("Cost vs Emissions")
    emissions_plot = config.PLOTS_DIR / "cost_emissions_pareto.png"
    if emissions_plot.exists():
        st.image(str(emissions_plot), use_container_width=True)

with st.expander("Service and capacity tables"):
    if not service.empty:
        st.write("Service-level scenarios")
        st.dataframe(service, use_container_width=True, hide_index=True)
    if not capacity.empty:
        st.write("Capacity stress test")
        st.dataframe(capacity, use_container_width=True, hide_index=True)

st.divider()
st.subheader("Interactive Re-Optimization")
st.caption("Adjust scenario assumptions and re-solve the MILP with CBC.")

scenario_cols = st.columns(5)
demand_multiplier = scenario_cols[0].slider("Demand multiplier", 0.5, 1.5, 1.0, 0.05)
capacity_multiplier = scenario_cols[1].slider("Warehouse capacity", 0.7, 1.3, 1.0, 0.05)
fixed_cost_multiplier = scenario_cols[2].slider("Fixed cost", 0.5, 2.0, 1.0, 0.1)
service_limit = scenario_cols[3].selectbox("Max service distance", ["None", 200, 300, 400])
carbon_price = scenario_cols[4].slider("Carbon price", 0, 200, 0, 10)

if st.button("Solve Scenario", type="primary"):
    suppliers, warehouses, demand, arcs_sw, arcs_wd = load_data()
    limit = None if service_limit == "None" else int(service_limit)
    with st.spinner("Solving scenario..."):
        scenario_result = solve_network(
            suppliers,
            warehouses,
            demand,
            arcs_sw,
            arcs_wd,
            demand_multiplier=demand_multiplier,
            capacity_multiplier=capacity_multiplier,
            fixed_cost_multiplier=fixed_cost_multiplier,
            service_distance_limit=limit,
            emission_price=carbon_price,
            time_limit=60,
        )

    if scenario_result.objective is None:
        st.error(f"Scenario status: {scenario_result.status}")
    else:
        scen_cols = st.columns(4)
        scen_cols[0].metric("Scenario Cost", _money(scenario_result.objective))
        scen_cols[1].metric("Opened Warehouses", len(scenario_result.opened_warehouses))
        scen_cols[2].metric("Variables", scenario_result.variable_count)
        scen_cols[3].metric("Constraints", scenario_result.constraint_count)
        st.write("Opened warehouses:", ", ".join(scenario_result.opened_warehouses))
