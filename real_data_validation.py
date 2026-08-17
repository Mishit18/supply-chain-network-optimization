"""Real shipment-data calibration for the synthetic network-design model."""

from __future__ import annotations

import json
from pathlib import Path

import kagglehub
import numpy as np
import pandas as pd


DATASET_HANDLE = "apoorvwatsky/supply-chain-shipment-pricing-data"
ORIGINAL_SOURCE = "USAID Supply Chain Shipment Pricing Dataset"


def download_shipment_history() -> Path:
    """Download the public USAID shipment-history mirror through KaggleHub."""
    directory = Path(kagglehub.dataset_download(DATASET_HANDLE))
    candidates = sorted(directory.glob("*.csv"))
    if not candidates:
        raise FileNotFoundError(f"No CSV found in downloaded dataset directory: {directory}")
    return candidates[0]


def load_shipment_history(path: Path) -> pd.DataFrame:
    """Load and normalize shipment history without imputing unavailable costs."""
    frame = pd.read_csv(path, encoding="latin1")
    for column in ["Scheduled Delivery Date", "Delivered to Client Date", "PO Sent to Vendor Date"]:
        frame[column] = pd.to_datetime(frame[column], errors="coerce", dayfirst=True, format="mixed")

    for column in [
        "Line Item Quantity",
        "Line Item Value",
        "Weight (Kilograms)",
        "Freight Cost (USD)",
        "Line Item Insurance (USD)",
    ]:
        frame[column] = pd.to_numeric(
            frame[column].astype(str).str.replace(",", "", regex=False), errors="coerce"
        )

    frame["delivery_delay_days"] = (
        frame["Delivered to Client Date"] - frame["Scheduled Delivery Date"]
    ).dt.days
    frame["vendor_lead_time_days"] = (
        frame["Delivered to Client Date"] - frame["PO Sent to Vendor Date"]
    ).dt.days
    frame["on_time"] = frame["delivery_delay_days"].le(0)
    frame["freight_per_kg"] = frame["Freight Cost (USD)"] / frame["Weight (Kilograms)"].replace(0, np.nan)
    frame["freight_value_ratio"] = frame["Freight Cost (USD)"] / frame["Line Item Value"].replace(0, np.nan)
    return frame


def _quantile(series: pd.Series, q: float) -> float:
    clean = series.replace([np.inf, -np.inf], np.nan).dropna()
    return float(clean.quantile(q)) if not clean.empty else float("nan")


def build_real_data_evidence(frame: pd.DataFrame, output_dir: Path) -> dict[str, float | int | str]:
    """Create auditable real-data priors and route/mode summaries."""
    output_dir.mkdir(parents=True, exist_ok=True)
    dated = frame.dropna(subset=["delivery_delay_days"])
    lead_time = frame.loc[frame["vendor_lead_time_days"].ge(0), "vendor_lead_time_days"]
    freight_per_kg = frame.loc[frame["freight_per_kg"].gt(0), "freight_per_kg"]
    freight_ratio = frame.loc[frame["freight_value_ratio"].between(0, 5), "freight_value_ratio"]

    metrics: dict[str, float | int | str] = {
        "source": ORIGINAL_SOURCE,
        "dataset_records": int(len(frame)),
        "countries": int(frame["Country"].nunique()),
        "vendors": int(frame["Vendor"].nunique()),
        "shipment_modes": int(frame["Shipment Mode"].nunique()),
        "dated_shipments": int(len(dated)),
        "on_time_delivery_rate": round(float(dated["on_time"].mean()), 5),
        "delivery_delay_p50_days": round(_quantile(dated["delivery_delay_days"], 0.50), 2),
        "delivery_delay_p90_days": round(_quantile(dated["delivery_delay_days"], 0.90), 2),
        "vendor_lead_time_p50_days": round(_quantile(lead_time, 0.50), 2),
        "vendor_lead_time_p90_days": round(_quantile(lead_time, 0.90), 2),
        "freight_per_kg_p50_usd": round(_quantile(freight_per_kg, 0.50), 4),
        "freight_per_kg_p90_usd": round(_quantile(freight_per_kg, 0.90), 4),
        "freight_to_item_value_p50": round(_quantile(freight_ratio, 0.50), 5),
        "quantity_p90": round(_quantile(frame["Line Item Quantity"], 0.90), 2),
    }

    mode_summary = (
        frame.groupby("Shipment Mode", dropna=False)
        .agg(
            shipments=("ID", "size"),
            countries=("Country", "nunique"),
            on_time_rate=("on_time", "mean"),
            median_delay_days=("delivery_delay_days", "median"),
            median_freight_usd=("Freight Cost (USD)", "median"),
            median_freight_per_kg=("freight_per_kg", "median"),
        )
        .reset_index()
        .sort_values("shipments", ascending=False)
    )
    country_summary = (
        frame.groupby("Country", dropna=False)
        .agg(
            shipments=("ID", "size"),
            vendors=("Vendor", "nunique"),
            total_item_value_usd=("Line Item Value", "sum"),
            on_time_rate=("on_time", "mean"),
            median_lead_time_days=("vendor_lead_time_days", "median"),
        )
        .reset_index()
        .sort_values("shipments", ascending=False)
    )
    mode_summary.to_csv(output_dir / "real_shipment_mode_benchmark.csv", index=False)
    country_summary.to_csv(output_dir / "real_shipment_country_benchmark.csv", index=False)
    (output_dir / "real_shipment_empirical_priors.json").write_text(
        json.dumps(metrics, indent=2, allow_nan=False), encoding="utf-8"
    )

    report = f"""# Real Shipment Data Validation

## Scope

The network optimizer remains a synthetic decision experiment. Its stress assumptions are now benchmarked separately against {metrics['dataset_records']:,} public shipment records from the {ORIGINAL_SOURCE}. This does not claim that USAID's physical network is the modeled 65-node network.

## Evidence

- {metrics['countries']} destination countries, {metrics['vendors']} vendors, and {metrics['shipment_modes']} shipment modes.
- On-time delivery rate: {metrics['on_time_delivery_rate']:.1%} across {metrics['dated_shipments']:,} dated shipments.
- Vendor lead-time P50/P90: {metrics['vendor_lead_time_p50_days']:.0f}/{metrics['vendor_lead_time_p90_days']:.0f} days.
- Freight-per-kg P50/P90: ${metrics['freight_per_kg_p50_usd']:.2f}/${metrics['freight_per_kg_p90_usd']:.2f}.

Missing or non-numeric freight and weight fields are retained as missing rather than imputed. Mode and country outputs provide auditable operational benchmarks for scenario selection.
"""
    docs_dir = output_dir.parents[1] / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "REAL_DATA_VALIDATION.md").write_text(report, encoding="utf-8")
    return metrics


def main() -> None:
    root = Path(__file__).resolve().parent
    path = download_shipment_history()
    metrics = build_real_data_evidence(load_shipment_history(path), root / "results" / "real_data")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
