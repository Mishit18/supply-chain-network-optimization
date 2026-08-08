"""Grounded RAG copilot for supply-chain network decisions.

The copilot retrieves evidence from project reports, assumptions, CSV result
tables, and generated metrics, then synthesizes a decision-facing answer with
citations. It intentionally works offline: the retrieval layer uses TF-IDF so
the project remains reproducible without API keys or model downloads.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import config


MAX_CHARS_PER_CHUNK = 1_100
DEFAULT_TOP_K = 5
SCENARIO_MEMORY_PATH = config.RESULTS_DIR / "scenario_runs.csv"
EVAL_SET_PATH = config.BASE_DIR / "docs" / "rag_eval_questions.csv"


@dataclass(frozen=True)
class KnowledgeChunk:
    source: str
    title: str
    text: str
    metadata: dict[str, str]


@dataclass(frozen=True)
class RetrievedChunk:
    source: str
    title: str
    text: str
    score: float
    metadata: dict[str, str]


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _split_markdown_sections(path: Path) -> list[KnowledgeChunk]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    chunks: list[KnowledgeChunk] = []
    current_title = path.stem
    buffer: list[str] = []

    def flush() -> None:
        content = _normalize_whitespace("\n".join(buffer))
        if not content:
            return
        chunks.extend(_chunk_long_text(path, current_title, content, {"kind": "document"}))

    for line in text.splitlines():
        if line.startswith("#"):
            flush()
            current_title = line.strip("# ").strip() or path.stem
            buffer = []
        else:
            buffer.append(line)
    flush()
    return chunks


def _chunk_long_text(path: Path, title: str, text: str, metadata: dict[str, str]) -> list[KnowledgeChunk]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[KnowledgeChunk] = []
    current: list[str] = []
    current_len = 0
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if current and current_len + len(sentence) > MAX_CHARS_PER_CHUNK:
            chunks.append(
                KnowledgeChunk(
                    source=str(path.relative_to(config.BASE_DIR)),
                    title=title,
                    text=_normalize_whitespace(" ".join(current)),
                    metadata=metadata,
                )
            )
            current = []
            current_len = 0
        current.append(sentence)
        current_len += len(sentence) + 1
    if current:
        chunks.append(
            KnowledgeChunk(
                source=str(path.relative_to(config.BASE_DIR)),
                title=title,
                text=_normalize_whitespace(" ".join(current)),
                metadata=metadata,
            )
        )
    return chunks


def _csv_chunks(path: Path, max_rows: int = 80) -> list[KnowledgeChunk]:
    try:
        df = pd.read_csv(path)
    except Exception:
        return []
    if df.empty:
        return []

    chunks: list[KnowledgeChunk] = []
    source = str(path.relative_to(config.BASE_DIR))
    table_name = path.stem.replace("_", " ")
    summary = (
        f"Table {path.name} has columns {', '.join(map(str, df.columns))} "
        f"and {len(df)} rows."
    )
    chunks.append(KnowledgeChunk(source, f"{table_name} schema", summary, {"kind": "table_schema"}))

    for idx, row in df.head(max_rows).iterrows():
        parts = [f"{col}: {row[col]}" for col in df.columns if pd.notna(row[col])]
        text = f"Row {idx + 1} from {path.name}. " + "; ".join(parts)
        chunks.append(
            KnowledgeChunk(
                source=source,
                title=f"{table_name} row {idx + 1}",
                text=_normalize_whitespace(text),
                metadata={"kind": "table_row", "row": str(idx + 1)},
            )
        )
    return chunks


def _json_chunks(path: Path) -> list[KnowledgeChunk]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    source = str(path.relative_to(config.BASE_DIR))
    chunks = []
    for key, value in data.items():
        text = f"{key}: {value}"
        chunks.append(KnowledgeChunk(source, key, text, {"kind": "metric"}))
    return chunks


def build_default_corpus(base_dir: Path | None = None) -> list[KnowledgeChunk]:
    base = base_dir or config.BASE_DIR
    candidate_paths: list[Path] = [
        base / "README.md",
        base / "PROJECT_REPORT.md",
    ]
    candidate_paths.extend(sorted((base / "docs").glob("*.md")) if (base / "docs").exists() else [])
    result_csvs = sorted((base / "results").glob("*.csv")) if (base / "results").exists() else []
    candidate_paths.extend(path for path in result_csvs if path.name != "rag_eval_results.csv")
    candidate_paths.extend(sorted((base / "results").glob("*.json")) if (base / "results").exists() else [])

    chunks: list[KnowledgeChunk] = []
    for path in candidate_paths:
        if not path.exists():
            continue
        if path.suffix.lower() == ".md":
            chunks.extend(_split_markdown_sections(path))
        elif path.suffix.lower() == ".csv":
            chunks.extend(_csv_chunks(path))
        elif path.suffix.lower() == ".json":
            chunks.extend(_json_chunks(path))

    return [chunk for chunk in chunks if len(chunk.text) >= 30]


class SupplyChainRAG:
    def __init__(self, chunks: Iterable[KnowledgeChunk]):
        self.chunks = list(chunks)
        if not self.chunks:
            raise ValueError("No knowledge chunks found. Run `python main.py` first or add project docs/results.")
        self.word_vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
            min_df=1,
        )
        self.char_vectorizer = TfidfVectorizer(
            lowercase=True,
            analyzer="char_wb",
            ngram_range=(4, 6),
            min_df=1,
        )
        texts = [chunk.text for chunk in self.chunks]
        self.word_matrix = self.word_vectorizer.fit_transform(texts)
        self.char_matrix = self.char_vectorizer.fit_transform(texts)

    def retrieve(self, query: str, top_k: int = DEFAULT_TOP_K) -> list[RetrievedChunk]:
        query = query.strip()
        if not query:
            return []
        word_query = self.word_vectorizer.transform([query])
        char_query = self.char_vectorizer.transform([query])
        word_scores = cosine_similarity(word_query, self.word_matrix).ravel()
        char_scores = cosine_similarity(char_query, self.char_matrix).ravel()
        scores = 0.72 * word_scores + 0.28 * char_scores
        scores = _boost_source_quality(query, self.chunks, scores)
        ranked = scores.argsort()[::-1][:top_k]
        results: list[RetrievedChunk] = []
        for idx in ranked:
            score = float(scores[idx])
            if score <= 0:
                continue
            chunk = self.chunks[int(idx)]
            results.append(
                RetrievedChunk(
                    source=chunk.source,
                    title=chunk.title,
                    text=chunk.text,
                    score=score,
                    metadata=chunk.metadata,
                )
            )
        return results

    def answer(self, query: str, top_k: int = DEFAULT_TOP_K) -> dict[str, object]:
        retrieved = self.retrieve(query, top_k=top_k)
        if not retrieved:
            return {
                "answer": "I do not have enough project evidence to answer that from the current reports/results.",
                "confidence": "Low",
                "citations": [],
                "evidence": [],
            }

        answer = _synthesize_answer(query, retrieved)
        confidence = _confidence_label(retrieved)
        return {
            "answer": answer,
            "confidence": confidence,
            "citations": [
                {
                    "source": item.source,
                    "title": item.title,
                    "score": round(item.score, 3),
                    "kind": item.metadata.get("kind", ""),
                    "row": item.metadata.get("row", ""),
                }
                for item in retrieved
            ],
            "evidence": [item.text for item in retrieved],
        }


def _confidence_label(retrieved: list[RetrievedChunk]) -> str:
    top = retrieved[0].score if retrieved else 0.0
    if top >= 0.35 and len(retrieved) >= 3:
        return "High"
    if top >= 0.18:
        return "Medium"
    return "Low"


def _boost_source_quality(query: str, chunks: list[KnowledgeChunk], scores):
    boosted = scores.copy()
    low_query = query.lower()
    for idx, chunk in enumerate(chunks):
        source = chunk.source.lower()
        title = chunk.title.lower()
        text = chunk.text.lower()
        if "scenario" in low_query and "scenario_runs" in source:
            boosted[idx] += 0.08
        if any(term in low_query for term in ["cost reduction", "greedy", "baseline", "open-all", "k-means"]) and (
            "baseline_comparison" in source or "baseline comparison" in title or "20.60" in text
        ):
            boosted[idx] += 0.14
        if any(term in low_query for term in ["recommend", "executive", "management", "decision"]) and (
            "executive summary" in title
            or "baseline_comparison" in source
            or "demand_shocks" in source
            or "service_level" in source
            or "scenario_runs" in source
        ):
            boosted[idx] += 0.10
        if any(term in low_query for term in ["assumption", "risk", "limit"]) and "assumption" in source:
            boosted[idx] += 0.06
        if any(term in low_query for term in ["risk", "rollout", "implementation"]) and (
            "supplier_sla_policy" in source or "model_assumptions" in source or "risks" in title
        ):
            boosted[idx] += 0.12
        if any(term in low_query for term in ["robust", "shock", "sensitivity"]) and (
            "demand_shocks" in source or "robustness" in title or "resume_metrics" in source
        ):
            boosted[idx] += 0.07
        if any(term in low_query for term in ["service", "distance"]) and (
            "service_level" in source or "service" in source or "service" in title
        ):
            boosted[idx] += 0.12
        if any(term in low_query for term in ["carbon", "emission", "sustainability"]) and (
            "emission" in source or "sustainability" in title
        ):
            boosted[idx] += 0.07
    return boosted


def _pick_sentences(query: str, retrieved: list[RetrievedChunk], max_sentences: int = 5) -> list[str]:
    terms = {
        token
        for token in re.findall(r"[a-zA-Z0-9+%.-]+", query.lower())
        if len(token) > 2 and token not in {"what", "why", "how", "which", "does", "the", "and"}
    }
    scored: list[tuple[int, str]] = []
    for item in retrieved:
        for sentence in re.split(r"(?<=[.!?])\s+", item.text):
            clean = sentence.strip()
            if not clean:
                continue
            if clean.count("|") > 10:
                continue
            if len(clean) > 320:
                clean = _focused_excerpt(clean, terms)
            low = clean.lower()
            score = sum(1 for term in terms if term in low)
            score += len(re.findall(r"\d+(?:\.\d+)?%?|\$[0-9,]+", clean))
            if score:
                scored.append((score, clean))
    scored.sort(key=lambda x: x[0], reverse=True)
    selected: list[str] = []
    seen = set()
    for _, sentence in scored:
        key = sentence.lower()
        if key in seen:
            continue
        selected.append(sentence)
        seen.add(key)
        if len(selected) >= max_sentences:
            break
    if selected:
        return selected
    return [_focused_excerpt(item.text, terms) for item in retrieved[: min(max_sentences, len(retrieved))]]


def _focused_excerpt(text: str, terms: set[str], max_chars: int = 260) -> str:
    clean = _normalize_whitespace(text.replace("|", " "))
    if len(clean) <= max_chars:
        return clean
    low = clean.lower()
    hits = [low.find(term) for term in terms if term in low]
    start = max(0, min(hits) - 80) if hits else 0
    excerpt = clean[start : start + max_chars].strip()
    if start > 0:
        excerpt = "..." + excerpt
    if start + max_chars < len(clean):
        excerpt += "..."
    return excerpt


def _synthesize_answer(query: str, retrieved: list[RetrievedChunk]) -> str:
    sentences = _pick_sentences(query, retrieved)
    evidence_text = " ".join(sentences)
    opening = "Based on the retrieved project evidence, "
    if any(word in query.lower() for word in ["why", "selected", "open", "warehouse"]):
        opening += "the network decision should be explained through fixed-cost, transport-cost, capacity, service, and robustness trade-offs."
    elif any(word in query.lower() for word in ["risk", "implementation", "rollout"]):
        opening += "the main implementation risks are scenario fragility, capacity pressure, service-level cost, and operational rollout discipline."
    elif any(word in query.lower() for word in ["carbon", "emission", "sustainability"]):
        opening += "the sustainability decision should be framed as a cost-versus-emissions trade-off rather than a single optimum."
    elif any(word in query.lower() for word in ["scenario", "shock", "sensitivity"]):
        opening += "the scenario answer should focus on how the facility mix and cost change under demand, capacity, service, or carbon assumptions."
    else:
        opening += "the answer is grounded in the optimizer outputs, sensitivity tables, and model assumptions."
    return f"{opening} Key evidence: {evidence_text}"


def answer_question(query: str, top_k: int = DEFAULT_TOP_K) -> dict[str, object]:
    rag = SupplyChainRAG(build_default_corpus())
    return rag.answer(query, top_k=top_k)


def explain_scenario(
    opened_warehouses: list[str],
    objective: float | None,
    assumptions: dict[str, object],
    top_k: int = 4,
) -> dict[str, object]:
    query = (
        "Explain scenario decision with demand multiplier "
        f"{assumptions.get('demand_multiplier')}, capacity multiplier {assumptions.get('capacity_multiplier')}, "
        f"fixed cost multiplier {assumptions.get('fixed_cost_multiplier')}, service limit {assumptions.get('service_limit')}, "
        f"carbon price {assumptions.get('carbon_price')}, opened warehouses {opened_warehouses}."
    )
    result = answer_question(query, top_k=top_k)
    cost_text = f"${objective:,.0f}" if objective is not None else "not available"
    scenario_summary = (
        f"Scenario opened {len(opened_warehouses)} warehouses ({', '.join(opened_warehouses) or 'none'}) "
        f"at total cost {cost_text}. "
    )
    result["answer"] = scenario_summary + str(result["answer"])
    return result


def record_scenario_run(
    opened_warehouses: list[str],
    objective: float | None,
    assumptions: dict[str, object],
    explanation: dict[str, object] | None = None,
) -> Path:
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    exists = SCENARIO_MEMORY_PATH.exists()
    citations = explanation.get("citations", []) if explanation else []
    top_sources = "; ".join(
        f"{item.get('source')}::{item.get('title')}" for item in citations[:3]
    )
    row = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "demand_multiplier": assumptions.get("demand_multiplier"),
        "capacity_multiplier": assumptions.get("capacity_multiplier"),
        "fixed_cost_multiplier": assumptions.get("fixed_cost_multiplier"),
        "service_limit": assumptions.get("service_limit"),
        "carbon_price": assumptions.get("carbon_price"),
        "status": assumptions.get("status", "Solved"),
        "objective": objective,
        "opened_count": len(opened_warehouses),
        "opened_warehouses": ",".join(opened_warehouses),
        "copilot_confidence": explanation.get("confidence") if explanation else "",
        "top_evidence": top_sources,
    }
    with SCENARIO_MEMORY_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not exists:
            writer.writeheader()
        writer.writerow(row)
    return SCENARIO_MEMORY_PATH


def generate_executive_memo(question: str, top_k: int = DEFAULT_TOP_K) -> dict[str, object]:
    retrieval_question = (
        f"{question}. Include optimal cost, baseline cost reduction, robust warehouses, "
        "service-level tradeoffs, carbon sensitivity, scenario memory, and rollout risks."
    )
    response = answer_question(retrieval_question, top_k=top_k)
    citations = response["citations"]
    evidence = response["evidence"]
    citation_text = "\n".join(
        f"- {item['source']} | {item['title']}" + (f" | row {item['row']}" if item.get("row") else "")
        for item in citations
    )
    evidence_bullets = "\n".join(f"- {_focused_excerpt(str(item), set(), 220)}" for item in evidence[:5])
    memo = f"""# Executive Decision Memo

## Decision Question

{question}

## Recommendation

Use the MILP optimizer as the source of truth for warehouse choices and use the RAG copilot as the evidence layer for stakeholder communication. {response["answer"]}

## Evidence Base

{evidence_bullets}

## Implementation Risks

- Scenario fragility: marginal warehouses may change under demand growth, contraction, or fixed-cost pressure.
- Service commitment risk: tighter distance thresholds can increase cost or create infeasibility.
- Data realism risk: current data is synthetic, so operational deployment would require real lane costs, lead times, and warehouse constraints.
- Governance risk: recommendations should cite model assumptions and scenario rows before management action.

## Next Actions

- Run the target scenario through the dashboard solver and save it to scenario memory.
- Compare selected warehouses against baseline, service-level, carbon, and demand-shock outputs.
- Use the cited evidence below in the final management recommendation.

## Citations

{citation_text}
"""
    return {**response, "memo": memo}


def evaluate_retrieval(eval_path: Path | None = None, top_k: int = DEFAULT_TOP_K) -> pd.DataFrame:
    path = eval_path or EVAL_SET_PATH
    if not path.exists():
        raise FileNotFoundError(f"Evaluation set not found: {path}")
    cases = pd.read_csv(path)
    rag = SupplyChainRAG(build_default_corpus())
    rows = []
    for case in cases.itertuples(index=False):
        expected = [item.strip() for item in str(case.expected_sources).split(";") if item.strip()]
        retrieved = rag.retrieve(str(case.question), top_k=top_k)
        retrieved_sources = [item.source for item in retrieved]
        hits = [source for source in expected if any(source in got for got in retrieved_sources)]
        rows.append(
            {
                "question": case.question,
                "expected_sources": "; ".join(expected),
                "retrieved_sources": "; ".join(retrieved_sources),
                "hit": bool(hits),
                "recall_at_k": len(hits) / len(expected) if expected else 1.0,
                "top_score": round(retrieved[0].score, 3) if retrieved else 0.0,
            }
        )
    return pd.DataFrame(rows)


def _format_cli_response(response: dict[str, object]) -> str:
    lines = [f"Confidence: {response['confidence']}", "", str(response["answer"]), "", "Citations:"]
    for citation in response["citations"]:
        row = f", row {citation['row']}" if citation.get("row") else ""
        lines.append(f"- {citation['source']} | {citation['title']}{row} | score={citation['score']}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask the supply-chain RAG decision copilot.")
    parser.add_argument("question", nargs="*", help="Question to answer from project evidence.")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help="Number of retrieved chunks.")
    parser.add_argument("--memo", action="store_true", help="Generate an executive memo instead of a short answer.")
    parser.add_argument("--evaluate", action="store_true", help="Run the retrieval benchmark in docs/rag_eval_questions.csv.")
    args = parser.parse_args()
    if args.evaluate:
        report = evaluate_retrieval(top_k=args.top_k)
        out_path = config.RESULTS_DIR / "rag_eval_results.csv"
        config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        report.to_csv(out_path, index=False)
        print(report.to_string(index=False))
        print(f"\nSaved: {out_path}")
        return
    question = " ".join(args.question).strip()
    if not question:
        question = "Why did the optimizer select the current warehouse network?"
    if args.memo:
        print(generate_executive_memo(question, top_k=args.top_k)["memo"])
    else:
        print(_format_cli_response(answer_question(question, top_k=args.top_k)))


if __name__ == "__main__":
    main()
