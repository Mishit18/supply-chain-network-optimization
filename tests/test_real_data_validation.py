from pathlib import Path

import pandas as pd

from real_data_validation import build_real_data_evidence, load_shipment_history


def test_real_shipment_metrics_and_missing_values(tmp_path: Path) -> None:
    raw = pd.DataFrame(
        {
            "ID": [1, 2],
            "Country": ["A", "B"],
            "Vendor": ["V1", "V2"],
            "Shipment Mode": ["Air", "Sea"],
            "Scheduled Delivery Date": ["01-Jan-24", "10-Jan-24"],
            "Delivered to Client Date": ["01-Jan-24", "15-Jan-24"],
            "PO Sent to Vendor Date": ["01-Dec-23", "01-Dec-23"],
            "Line Item Quantity": ["1,000", "2000"],
            "Line Item Value": [10000, 20000],
            "Weight (Kilograms)": [100, "See DN"],
            "Freight Cost (USD)": [500, "See DN"],
            "Line Item Insurance (USD)": [10, 20],
        }
    )
    source = tmp_path / "sample.csv"
    raw.to_csv(source, index=False, encoding="latin1")
    frame = load_shipment_history(source)
    metrics = build_real_data_evidence(frame, tmp_path / "results" / "real_data")
    assert metrics["dataset_records"] == 2
    assert metrics["on_time_delivery_rate"] == 0.5
    assert pd.isna(frame.loc[1, "freight_per_kg"])
    assert (tmp_path / "results" / "real_data" / "real_shipment_empirical_priors.json").exists()
