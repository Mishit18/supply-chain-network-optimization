from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd

from rag_copilot import (
    KnowledgeChunk,
    SupplyChainRAG,
    generate_executive_memo,
    record_scenario_run,
)


def test_rag_retrieves_relevant_supply_chain_evidence():
    chunks = [
        KnowledgeChunk(
            source="PROJECT_REPORT.md",
            title="Robustness Analysis",
            text="Demand-shock experiments identify W01, W05, W06, and W08 as robust warehouses.",
            metadata={"kind": "document"},
        ),
        KnowledgeChunk(
            source="results/baseline_comparison.csv",
            title="baseline row",
            text="The MILP reduces total logistics cost by 20.60 percent versus greedy nearest warehouse.",
            metadata={"kind": "table_row", "row": "1"},
        ),
    ]

    rag = SupplyChainRAG(chunks)
    results = rag.retrieve("Which warehouses are robust under demand shocks?", top_k=1)

    assert results
    assert results[0].source == "PROJECT_REPORT.md"
    assert "W01" in results[0].text


def test_rag_answer_returns_citations_and_confidence():
    chunks = [
        KnowledgeChunk(
            source="docs/MODEL_ASSUMPTIONS.md",
            title="Model Assumptions",
            text="Service-level constraints require demand nodes to be served within a maximum warehouse distance.",
            metadata={"kind": "document"},
        ),
        KnowledgeChunk(
            source="results/service_level.csv",
            title="service row",
            text="Row 1 from service_level.csv. max_distance: 300; status: Optimal; total_cost: 2450000.",
            metadata={"kind": "table_row", "row": "1"},
        ),
    ]

    rag = SupplyChainRAG(chunks)
    response = rag.answer("Explain service-level cost tradeoff", top_k=2)

    assert response["citations"]
    assert response["confidence"] in {"Low", "Medium", "High"}
    assert "service" in response["answer"].lower()


def test_record_scenario_run_writes_memory(tmp_path, monkeypatch):
    import rag_copilot

    memory_path = tmp_path / "scenario_runs.csv"
    monkeypatch.setattr(rag_copilot, "SCENARIO_MEMORY_PATH", memory_path)

    record_scenario_run(
        ["W01", "W05"],
        12345.0,
        {
            "demand_multiplier": 1.2,
            "capacity_multiplier": 0.9,
            "fixed_cost_multiplier": 1.0,
            "service_limit": 300,
            "carbon_price": 50,
            "status": "Optimal",
        },
        {"confidence": "High", "citations": [{"source": "results/x.csv", "title": "row 1"}]},
    )

    saved = pd.read_csv(memory_path)
    assert saved.loc[0, "opened_warehouses"] == "W01,W05"
    assert saved.loc[0, "copilot_confidence"] == "High"


def test_executive_memo_contains_decision_sections(monkeypatch):
    import rag_copilot

    monkeypatch.setattr(
        rag_copilot,
        "answer_question",
        lambda question, top_k=5: {
            "answer": "The selected network is robust across demand shocks.",
            "confidence": "High",
            "citations": [{"source": "PROJECT_REPORT.md", "title": "Robustness", "row": ""}],
            "evidence": ["Demand shocks identify robust warehouses."],
        },
    )

    memo = generate_executive_memo("Should we approve the network?")["memo"]

    assert "Executive Decision Memo" in memo
    assert "Recommendation" in memo
    assert "Citations" in memo
