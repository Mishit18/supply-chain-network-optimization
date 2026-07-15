import argparse
import json
import time

import pandas as pd

import config
from baselines import run_baselines
from data_generation import generate_synthetic_data
from model import diagnose_feasibility, solve_network
from multi_period import solve_multi_period_network
from report import generate_project_report
from scaling import run_scale_demo
from sensitivity import run_sensitivity_suite
from stochastic import run_monte_carlo_demand_analysis
from solve import run_optimal
from validation import raise_for_invalid_inputs
from visualize import create_all_plots


def _write_outputs(
    baseline_summary,
    sensitivity_outputs,
    resume_metrics,
    multi_period_result=None,
    scale_summary=None,
    monte_carlo_outputs=None,
):
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    baseline_summary.to_csv(config.RESULTS_DIR / "baseline_comparison.csv", index=False)
    for name, value in sensitivity_outputs.items():
        if isinstance(value, pd.DataFrame):
            value.to_csv(config.RESULTS_DIR / f"{name}.csv", index=False)
    with open(config.RESULTS_DIR / "resume_metrics.json", "w", encoding="utf-8") as f:
        json.dump(resume_metrics, f, indent=2)
    if multi_period_result is not None:
        multi_period_result.period_summary.to_csv(config.RESULTS_DIR / "multi_period_summary.csv", index=False)
        multi_period_result.transition_summary.to_csv(config.RESULTS_DIR / "multi_period_transitions.csv", index=False)
    if scale_summary is not None:
        scale_summary.to_csv(config.RESULTS_DIR / "scale_demo_summary.csv", index=False)
    if monte_carlo_outputs is not None:
        scenario_summary, stability = monte_carlo_outputs
        scenario_summary.to_csv(config.RESULTS_DIR / "monte_carlo_demand_scenarios.csv", index=False)
        stability.to_csv(config.RESULTS_DIR / "monte_carlo_warehouse_stability.csv", index=False)


def _resume_metrics(optimal_result, baseline_summary, sensitivity_outputs, demand, multi_period_result=None):
    reductions = {}
    if not baseline_summary.empty and "method" in baseline_summary.columns:
        reductions = baseline_summary.set_index("method")["optimal_cost_reduction_pct"].to_dict()
    service = sensitivity_outputs["service_level"]
    if "status" in service.columns:
        feasible_service = service[service["status"].isin(["Optimal", "Feasible"])]
    else:
        feasible_service = pd.DataFrame()
    service_tradeoff = None
    if not feasible_service.empty and "total_cost" in feasible_service.columns and optimal_result.objective:
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
        "model_variables": optimal_result.variable_count,
        "model_constraints": optimal_result.constraint_count,
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
        "multi_period_status": multi_period_result.status if multi_period_result else None,
        "multi_period_objective": round(multi_period_result.objective, 2) if multi_period_result and multi_period_result.objective else None,
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


def parse_args():
    parser = argparse.ArgumentParser(description="Run supply chain network optimization experiments.")
    parser.add_argument("--quick", action="store_true", help="Run only data generation, base MILP, LP relaxation, and report refresh.")
    parser.add_argument("--deep", action="store_true", help="Include slower fixed-cost threshold sweeps in sensitivity outputs.")
    parser.add_argument("--multi-period", action="store_true", help="Run the three-period facility-location extension with switching costs.")
    parser.add_argument("--scale-demo", action="store_true", help="Aggregate a 1,000-customer demand cloud into zones and solve the scaled instance.")
    parser.add_argument("--monte-carlo", action="store_true", help="Run node-level Monte Carlo demand uncertainty scenarios.")
    parser.add_argument("--solver-msg", action="store_true", help="Show CBC solver logs.")
    return parser.parse_args()


def main():
    args = parse_args()
    started = time.perf_counter()
    suppliers, warehouses, demand, arcs_sw, arcs_wd = generate_synthetic_data(save=True)
    raise_for_invalid_inputs(suppliers, warehouses, demand, arcs_sw, arcs_wd)

    feasibility = diagnose_feasibility(suppliers, warehouses, demand)
    print("Feasibility check:", feasibility)

    optimal_result = run_optimal(suppliers, warehouses, demand, arcs_sw, arcs_wd, msg=args.solver_msg)
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

    if args.quick:
        baseline_summary = pd.DataFrame()
        sensitivity_outputs = {
            "service_level": pd.DataFrame(),
            "robust_warehouses": [],
            "marginal_warehouses": [],
        }
        plot_paths = []
    else:
        baseline_summary, _ = run_baselines(suppliers, warehouses, demand, arcs_sw, arcs_wd, optimal_result)
        sensitivity_outputs = run_sensitivity_suite(
            suppliers,
            warehouses,
            demand,
            arcs_sw,
            arcs_wd,
            optimal_result,
            include_fixed_sweep=args.deep,
        )
        plot_paths = create_all_plots(suppliers, warehouses, demand, optimal_result, baseline_summary, sensitivity_outputs)

    multi_period_result = None
    if args.multi_period:
        multi_period_result = solve_multi_period_network(suppliers, warehouses, demand, arcs_sw, arcs_wd, msg=args.solver_msg)
        print(f"Multi-period status: {multi_period_result.status}")
        if multi_period_result.objective:
            print(f"Multi-period objective: {multi_period_result.objective:,.2f}")

    scale_summary = None
    if args.scale_demo:
        scale_summary, _, _ = run_scale_demo(suppliers, warehouses, arcs_sw)
        row = scale_summary.iloc[0]
        print(
            f"Scale demo status: {row.status}; "
            f"{row.raw_customer_nodes} customers -> {row.aggregated_zones} zones; "
            f"{row.solve_seconds}s"
        )

    monte_carlo_outputs = None
    if args.monte_carlo:
        monte_carlo_outputs = run_monte_carlo_demand_analysis(suppliers, warehouses, demand, arcs_sw, arcs_wd)
        scenario_summary, stability = monte_carlo_outputs
        feasible = scenario_summary[scenario_summary["status"].isin(["Optimal", "Feasible"])]
        avg_cost = feasible["total_cost"].mean() if not feasible.empty else None
        avg_cost_text = f"{avg_cost:,.2f}" if avg_cost else "N/A"
        print(
            f"Monte Carlo scenarios: {scenario_summary.shape[0]}; "
            f"feasible: {feasible.shape[0]}; "
            f"average cost: {avg_cost_text}"
        )

    metrics = _resume_metrics(optimal_result, baseline_summary, sensitivity_outputs, demand, multi_period_result)

    report_path = None
    if args.quick:
        if multi_period_result is not None:
            multi_period_result.period_summary.to_csv(config.RESULTS_DIR / "multi_period_summary.csv", index=False)
            multi_period_result.transition_summary.to_csv(config.RESULTS_DIR / "multi_period_transitions.csv", index=False)
        if scale_summary is not None:
            scale_summary.to_csv(config.RESULTS_DIR / "scale_demo_summary.csv", index=False)
        if monte_carlo_outputs is not None:
            scenario_summary, stability = monte_carlo_outputs
            scenario_summary.to_csv(config.RESULTS_DIR / "monte_carlo_demand_scenarios.csv", index=False)
            stability.to_csv(config.RESULTS_DIR / "monte_carlo_warehouse_stability.csv", index=False)
    else:
        _write_outputs(
            baseline_summary,
            sensitivity_outputs,
            metrics,
            multi_period_result,
            scale_summary,
            monte_carlo_outputs,
        )
        report_path = generate_project_report()

    if not baseline_summary.empty:
        print("\nBaseline comparison:")
        print(baseline_summary[["method", "status", "total_cost", "optimal_cost_reduction_pct", "opened_count"]])
        print("\nRobust warehouses:", sensitivity_outputs["robust_warehouses"])
        print("Marginal warehouses:", sensitivity_outputs["marginal_warehouses"])
    print("\nPlots:")
    for path in plot_paths:
        print(f"- {path}")
    if report_path is not None:
        print(f"\nProject report: {report_path}")
    else:
        print("\nQuick mode: skipped portfolio report refresh.")

    if not args.quick:
        _print_resume_bullets(metrics)
    print(f"\nCompleted in {time.perf_counter() - started:.1f} seconds.")


if __name__ == "__main__":
    main()
