# CharityLens

AI-Powered NGO Trust & Transparency Platform for Indian Non-Profits

## Overview

CharityLens helps donors make informed decisions by analyzing publicly available NGO data from Indian government sources. It uses an MCP (Model Context Protocol) server to expose verified data tools, a retrieval-augmented context layer for dynamic information retrieval, and a two-agent pipeline for structured analysis and donor-friendly explanations.

The entire system is designed to run on minimal hardware (< 512 MB RAM, SQLite, FastAPI) — suitable for Raspberry Pi, low-cost VPS, or local machines.

---

## Key Features

- **MCP Server**: Wraps all NGO data interactions (FCRA, 80G, annual filings, news sentiment) as discrete, testable tools via JSON-RPC-style endpoints.
- **Real Indian NGO Datasets**: Ingests and normalizes data from NGO Darpan, FCRA Portal, MCA, OpenBudgets India, and GuideStar India.
- **Retrieval-Augmented Context**: BM25 / TF-IDF / semantic search (FAISS + DistilBERT) to dynamically retrieve relevant NGO records.
- **Two-Agent Pipeline**:
  - **Collector Agent**: Calls MCP tools, validates records, and outputs structured JSON.
  - **Analyst Agent**: Runs rule-based risk scoring and generates donor-friendly explanations (English / Hindi).
- **Responsible AI**: Bias analysis for rural/small NGOs, uncertainty flags, and a MODEL_CARD.md documenting limitations.
- **Lightweight Deployment**: SQLite + FTS5, FastAPI, optional 4-bit quantized open models (Phi-3 Mini, TinyLlama).

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      User / LLM Interface                   │
│  (ask about an NGO by name, PAN, or FCRA number)           │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                     Analyst / Explainer Agent               │
│  ─ Rule-based risk scoring                                  │
│  ─ Donor-friendly explanation generation (EN / HI)          │
│  ─ Uncertainty flags                                        │
└──────────────────────────────┬──────────────────────────────┘
                               │  structured JSON
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                       Collector Agent                       │
│  ─ Calls MCP tools                                         │
│  ─ Validates FCRA status, 80G, filings, audit reports      │
│  ─ Outputs structured record                               │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                     MCP Server (FastAPI + Uvicorn)          │
│  ─ get_fcra_registration   ─ check_fcra_status             │
│  ─ get_financial_summary   ─ get_annual_filings            │
│  ─ get_80g_status          ─ check_adverse_media           │
│  ─ search_ngo_by_name      ─ get_registration_details      │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                   Retrieval Layer (RAG)                     │
│  ─ BM25 / TF-IDF  (lightweight)                            │
│  ─ Sentence Transformers + FAISS (semantic)                 │
│  ─ Top-K record retrieval → structured context injection    │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│               SQLite + FTS5 / FAISS Vector Store            │
│  ─ Normalized, merged records from government sources      │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    ETL Pipeline (Python + Pandas)           │
│  ─ Pull CSV snapshots nightly (or bundle with repo)        │
│  ─ Clean, normalize, merge across sources                  │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                  Public Data Sources                        │
│  ─ NGO Darpan (NITI Aayog)                                 │
│  ─ FCRA Portal (MHA)                                       │
│  ─ Ministry of Corporate Affairs (MCA)                     │
│  ─ OpenBudgets India                                       │
│  ─ GuideStar India                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Risk Scoring Heuristic

| Condition                   | Score |
| --------------------------- | ----- |
| Missing annual filing       | -20   |
| Missing audit report        | -15   |
| FCRA suspended              | -50   |
| Negative media coverage     | -15   |
| Valid 80G                   | +10   |
| Consistent filings          | +20   |

Scores are advisory. Bias analysis is performed across states and NGO sizes to reduce false negatives for small/rural organizations.

---

## Data Sources

| Source             | What It Provides                                  |
| ------------------ | ------------------------------------------------- |
| NGO Darpan         | Registrations, sectors, registration numbers      |
| FCRA Portal        | FCRA registrations, suspended/cancelled orgs      |
| MCA                | Section 8 company filings (AOC-4, MGT-7)         |
| OpenBudgets India  | Budget and expenditure data                       |
| GuideStar India    | Additional organizational metadata                |

All data is publicly available government records. No personal donor data or private information is collected.

---

## Repository Structure

```
project-root/
├── mcp_server/
│   ├── main.py            # FastAPI app, MCP tool registration
│   ├── tools.py           # Tool implementations
│   └── routes.py          # JSON-RPC endpoints
│
├── data_pipeline/
│   ├── etl.py             # Nightly/bundled data ingestion
│   ├── cleaner.py         # Normalization, deduplication
│   └── loaders.py         # Source-specific loaders
│
├── agents/
│   ├── collector.py       # MCP tool caller, record validation
│   ├── analyst.py         # Risk scoring, explanation generation
│   └── prompts.py         # Prompt templates (EN / HI)
│
├── eval/
│   ├── tests.py           # Pytest test suite
│   └── metrics.py         # Scoring and bias metrics
│
├── data/                  # Processed SQLite DBs, FAISS indices
│
├── MODEL_CARD.md          # Limitations, intended use, bias notes
├── README.md
├── CONTRIBUTING.md
├── LICENSE
└── requirements.txt
```

---

## Responsible AI

- **Data**: Only public government records. No private donor data.
- **Bias**: Disparity analysis by state and NGO size; penalties reduced for delayed filings where appropriate.
- **Uncertainty**: Clearly flagged when data is incomplete or outdated.
- **Model Card**: See [MODEL_CARD.md](MODEL_CARD.md) for intended use, limitations, and bias notes.

---

