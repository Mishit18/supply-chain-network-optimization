import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

import config


def _save(fig, name):
    config.PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    path = config.PLOTS_DIR / name
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def plot_network(suppliers, warehouses, demand, flows, max_arrows=120):
    fig, ax = plt.subplots(figsize=(11, 8))
    open_warehouses = set(pd.DataFrame(flows)["warehouse_id"].unique()) if flows else set()

    ax.scatter(suppliers["x"], suppliers["y"], marker="^", s=140, c="#2f6fbb", label="Suppliers")
    ax.scatter(demand["x"], demand["y"], marker="o", s=35, c="#7a7a7a", alpha=0.7, label="Demand nodes")

    for is_open, group in warehouses.groupby(warehouses["warehouse_id"].isin(open_warehouses)):
        ax.scatter(
            group["x"],
            group["y"],
            marker="s",
            s=120,
            c="#1a9850" if is_open else "#d73027",
            label="Open warehouses" if is_open else "Closed warehouses",
            edgecolor="black",
            linewidth=0.5,
        )

    if flows:
        flow_df = pd.DataFrame(flows)
        wh_xy = warehouses.set_index("warehouse_id")[["x", "y"]]
        d_xy = demand.set_index("demand_id")[["x", "y"]]
        by_route = (
            flow_df.groupby(["warehouse_id", "demand_id"])["flow"]
            .sum()
            .sort_values(ascending=False)
            .head(max_arrows)
            .reset_index()
        )
        max_flow = by_route["flow"].max()
        for row in by_route.itertuples(index=False):
            wx, wy = wh_xy.loc[row.warehouse_id]
            dx, dy = d_xy.loc[row.demand_id]
            ax.annotate(
                "",
                xy=(dx, dy),
                xytext=(wx, wy),
                arrowprops={
                    "arrowstyle": "->",
                    "color": "#444444",
                    "alpha": 0.25,
                    "lw": 0.4 + 2.2 * row.flow / max_flow,
                },
            )

    ax.set_title("Optimized Supply Chain Network")
    ax.set_xlabel("X coordinate")
    ax.set_ylabel("Y coordinate")
    ax.legend(loc="upper right")
    ax.grid(alpha=0.15)
    return _save(fig, "network_map.png")


def plot_cost_breakdown(baseline_summary, optimal_result):
    rows = [
        {
            "method": "optimal",
            "fixed_cost": optimal_result.fixed_cost,
            "variable_cost": optimal_result.variable_cost,
        }
    ]
    rows.extend(baseline_summary[["method", "fixed_cost", "variable_cost"]].to_dict("records"))
    df = pd.DataFrame(rows).melt(id_vars="method", var_name="cost_type", value_name="cost")

    fig, ax = plt.subplots(figsize=(10, 6))
    pivot = df.pivot(index="method", columns="cost_type", values="cost").fillna(0)
    pivot[["fixed_cost", "variable_cost"]].plot(
        kind="bar",
        stacked=False,
        ax=ax,
        color=["#4c78a8", "#f58518"],
    )
    ax.set_title("Cost Breakdown by Method")
    ax.set_xlabel("")
    ax.set_ylabel("Cost")
    ax.tick_params(axis="x", rotation=15)
    return _save(fig, "cost_breakdown.png")


def plot_service_tradeoff(service_df):
    fig, ax = plt.subplots(figsize=(8, 5))
    feasible = service_df[service_df["status"].isin(["Optimal", "Feasible"])].copy()
    if feasible.empty:
        ax.text(0.5, 0.5, "No feasible service-level scenarios", ha="center", va="center")
    else:
        feasible = feasible.sort_values("max_distance")
        ax.plot(feasible["max_distance"], feasible["total_cost"], marker="o", color="#1b9e77")
    ax.set_title("Service-Level Distance vs Cost")
    ax.set_xlabel("Maximum warehouse-to-demand distance")
    ax.set_ylabel("Total cost")
    return _save(fig, "service_cost_tradeoff.png")


def plot_tornado(optimal_cost, sensitivity_outputs):
    rows = []
    demand_df = sensitivity_outputs["demand_shocks"]
    for row in demand_df.itertuples(index=False):
        if row.total_cost:
            rows.append({"parameter": row.scenario, "impact_pct": 100 * (row.total_cost - optimal_cost) / optimal_cost})

    capacity_df = sensitivity_outputs["capacity"]
    for row in capacity_df.itertuples(index=False):
        if row.total_cost:
            rows.append({"parameter": row.scenario, "impact_pct": 100 * (row.total_cost - optimal_cost) / optimal_cost})

    tornado = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(9, 6))
    if tornado.empty:
        ax.text(0.5, 0.5, "No sensitivity impacts available", ha="center", va="center")
    else:
        tornado = tornado.reindex(tornado["impact_pct"].abs().sort_values(ascending=True).index)
        ax.barh(tornado["parameter"], tornado["impact_pct"], color="#6a9f58")
        ax.axvline(0, color="black", linewidth=0.8)
    ax.set_title("Sensitivity Tornado Chart")
    ax.set_xlabel("Total cost impact vs base optimal (%)")
    return _save(fig, "sensitivity_tornado.png")


def plot_emissions_pareto(emissions_df):
    fig, ax = plt.subplots(figsize=(8, 5))
    feasible = emissions_df[emissions_df["status"].isin(["Optimal", "Feasible"])].copy()
    if feasible.empty:
        ax.text(0.5, 0.5, "No feasible emissions scenarios", ha="center", va="center")
    else:
        feasible = feasible.sort_values("emissions_kg")
        scatter = ax.scatter(
            feasible["emissions_kg"],
            feasible["total_cost"],
            c=feasible["emission_price_per_ton"],
            cmap="viridis",
            s=70,
        )
        ax.plot(feasible["emissions_kg"], feasible["total_cost"], color="#555555", linewidth=1)
        fig.colorbar(scatter, ax=ax, label="Emission price per ton")
    ax.set_title("Cost vs Emissions Pareto Sweep")
    ax.set_xlabel("Emissions (kg CO2e)")
    ax.set_ylabel("Total cost")
    return _save(fig, "cost_emissions_pareto.png")


def create_all_plots(suppliers, warehouses, demand, optimal_result, baseline_summary, sensitivity_outputs):
    return [
        plot_network(suppliers, warehouses, demand, optimal_result.flows),
        plot_cost_breakdown(baseline_summary, optimal_result),
        plot_service_tradeoff(sensitivity_outputs["service_level"]),
        plot_tornado(optimal_result.objective, sensitivity_outputs),
        plot_emissions_pareto(sensitivity_outputs["emissions"]),
    ]
