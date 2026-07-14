import json
import time

import pandas as pd

import config
from baselines import run_baselines
from data_generation import generate_synthetic_data
from model import diagnose_feasibility, solve_network
from report import generate_project_report
from sensitivity import run_sensitivity_suite
from solve import run_optimal
from validation import raise_for_invalid_inputs
from visualize import create_all_plots


def _write_outputs(baseline_summary, sensitivity_outputs, resume_metrics):
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    baseline_summary.to_csv(config.RESULTS_DIR / "baseline_comparison.csv", index=False)
    for name, value in sensitivity_outputs.items():
        if isinstance(value, pd.DataFrame):
            value.to_csv(config.RESULTS_DIR / f"{name}.csv", index=False)
    with open(config.RESULTS_DIR / "resume_metrics.json", "w", encoding="utf-8") as f:
        json.dump(resume_metrics, f, indent=2)


def _resume_metrics(optimal_result, baseline_summary, sensitivity_outputs, demand):
    reductions = baseline_summary.set_index("method")["optimal_cost_reduction_pct"].to_dict()
    service = sensitivity_outputs["service_level"]
    feasible_service = service[service["status"].isin(["Optimal", "Feasible"])]
    service_tradeoff = None
    if not feasible_service.empty and optimal_result.objective:
        service_tradeoff = {
            str(int(row.max_distance)): round(100 * (row.total_cost - optimal_result.objective) / optimal_result.objective, 2)
            for row in feasible_service.itertuples(index=False)
            if row.total_cost
        }

    return {
        "nodes": 5 + 10 + 50,
        "suppliers": 5,
        "warehouses": 10,
        "demand_nodes": int(demand.shape[0]),
        "binary_variables": 10,
        "continuous_flow_variables": 5 * 10 * 50,
        "optimal_total_cost": round(optimal_result.objective, 2) if optimal_result.objective else None,
        "optimal_fixed_cost": round(optimal_result.fixed_cost, 2) if optimal_result.fixed_cost else None,
        "optimal_variable_cost": round(optimal_result.variable_cost, 2) if optimal_result.variable_cost else None,
        "opened_warehouses": optimal_result.opened_warehouses,
        "cost_reduction_vs_greedy_pct": round(reductions.get("greedy_nearest", 0), 2),
        "cost_reduction_vs_open_all_pct": round(reductions.get("open_all", 0), 2),
        "cost_reduction_vs_kmeans_pct": round(reductions.get("kmeans", 0), 2),
        "robust_warehouse_count": len(sensitivity_outputs["robust_warehouses"]),
        "robust_warehouses": sensitivity_outputs["robust_warehouses"],
        "marginal_warehouse_count": len(sensitivity_outputs["marginal_warehouses"]),
        "marginal_warehouses": sensitivity_outputs["marginal_warehouses"],
        "service_tradeoff_cost_increase_pct": service_tradeoff,
    }


def _print_resume_bullets(metrics):
    print("\nResume bullets with actual experiment numbers:\n")
    print(
        f"- Formulated {metrics['nodes']}-node two-stage capacitated facility location MILP "
        f"with {metrics['binary_variables']} binary open/close decisions and "
        f"{metrics['continuous_flow_variables']} continuous flow variables in PuLP."
    )
    print(
        f"- Optimal network reduced total logistics cost by "
        f"{metrics['cost_reduction_vs_greedy_pct']}% vs. greedy nearest-warehouse baseline, "
        f"{metrics['cost_reduction_vs_open_all_pct']}% vs. open-all baseline, and "
        f"{metrics['cost_reduction_vs_kmeans_pct']}% vs. k-means baseline across "
        f"{metrics['demand_nodes']} demand nodes."
    )
    print(
        f"- Sensitivity-tested solution under +/-20%, +/-30%, and +/-50% demand shocks; "
        f"identified {metrics['robust_warehouse_count']} robust warehouse locations "
        f"and {metrics['marginal_warehouse_count']} marginal locations prone to scenario-driven changes."
    )
    if metrics["service_tradeoff_cost_increase_pct"]:
        print(
            f"- Extended model with max-distance service-level constraints; quantified cost-of-service "
            f"tradeoffs across {len(metrics['service_tradeoff_cost_increase_pct'])} feasible distance thresholds."
        )


def main():
    started = time.perf_counter()
    suppliers, warehouses, demand, arcs_sw, arcs_wd = generate_synthetic_data(save=True)
    raise_for_invalid_inputs(suppliers, warehouses, demand, arcs_sw, arcs_wd)

    feasibility = diagnose_feasibility(suppliers, warehouses, demand)
    print("Feasibility check:", feasibility)

    optimal_result = run_optimal(suppliers, warehouses, demand, arcs_sw, arcs_wd)
    print(f"Optimal status: {optimal_result.status}")
    print(f"Optimal cost: {optimal_result.objective:,.2f}")
    print(f"Opened warehouses: {optimal_result.opened_warehouses}")

    lp_relaxation = solve_network(
        suppliers,
        warehouses,
        demand,
        arcs_sw,
        arcs_wd,
        relax_integrality=True,
    )
    pd.DataFrame(
        [{"warehouse_id": j, "lp_open_value": value} for j, value in lp_relaxation.warehouse_decisions.items()]
    ).to_csv(config.RESULTS_DIR / "lp_relaxation_y_values.csv", index=False)

    baseline_summary, _ = run_baselines(suppliers, warehouses, demand, arcs_sw, arcs_wd, optimal_result)
    sensitivity_outputs = run_sensitivity_suite(suppliers, warehouses, demand, arcs_sw, arcs_wd, optimal_result)
    metrics = _resume_metrics(optimal_result, baseline_summary, sensitivity_outputs, demand)

    _write_outputs(baseline_summary, sensitivity_outputs, metrics)
    plot_paths = create_all_plots(suppliers, warehouses, demand, optimal_result, baseline_summary, sensitivity_outputs)
    report_path = generate_project_report()

    print("\nBaseline comparison:")
    print(baseline_summary[["method", "status", "total_cost", "optimal_cost_reduction_pct", "opened_count"]])
    print("\nRobust warehouses:", sensitivity_outputs["robust_warehouses"])
    print("Marginal warehouses:", sensitivity_outputs["marginal_warehouses"])
    print("\nPlots:")
    for path in plot_paths:
        print(f"- {path}")
    print(f"\nProject report: {report_path}")

    _print_resume_bullets(metrics)
    print(f"\nCompleted in {time.perf_counter() - started:.1f} seconds.")


if __name__ == "__main__":
    main()
