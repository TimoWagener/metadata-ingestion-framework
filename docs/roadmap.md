# 📋 Framework Roadmap (MoSCoW Prioritization)

This document outlines the strategic enhancements for scaling the **Metadata Ingestion Framework** into a robust, enterprise-grade system maintainable by both engineers and non-technical contributors.

---

```
┌────────────────────────────────────────────────────────┐
│                      M - MUST HAVE                     │
│           (Safeguards for non-technical users)         │
├────────────────────────────────────────────────────────┤
│                      S - SHOULD HAVE                   │
│             (Automation & CI/CD Guardrails)            │
├────────────────────────────────────────────────────────┤
│                      C - COULD HAVE                    │
│            (Advanced Developer & Pipeline DX)          │
├────────────────────────────────────────────────────────┤
│                      W - WON'T HAVE (NOW)              │
│               (Overkill / Premature Complexity)        │
└────────────────────────────────────────────────────────┘
```

---

## 🔴 1. MUST HAVE (Safeguards for YAML Authors)

These features ensure that non-technical users can contribute and edit YAML files without breaking production pipelines:

| Feature / Package | Purpose | Value & Rationale |
| :--- | :--- | :--- |
| **`pydantic` (v2)** | Strict schema validation during YAML loading (`TableSchema`, `SourceSchema`). | Replaces manual dictionary checks with immediate, actionable error messages (e.g. *"Missing required field `load.type` on line 12 of mitmas.yml"*). |
| **VS Code / IDE JSON Schema (`$schema`)** | Real-time schema validation, autocomplete, and inline tooltips in IDEs. | YAML authors get dropdown completions for `system_type`, `load.type`, and formatting rules directly in their editor. |
| **Batch Compiler (`--all` / `--source all`)** | Bulk compile all source tables into a destination directory (`landing_manifests/*.json`). | Allows Azure Data Factory (ADF) or orchestration scripts to ingest manifests in bulk without per-table CLI execution. |

---

## 🟡 2. SHOULD HAVE (Automated Quality & CI/CD)

Automated quality gates that protect the `main` branch from broken or invalid metadata:

| Feature / Package | Purpose | Value & Rationale |
| :--- | :--- | :--- |
| **`pytest` Suite** | Automated unit tests for database dialect calculations (DB2, MSSQL, Oracle, REST). | Guarantees that adjustments to DB2 date logic never accidentally break MSSQL or Thinkwise OData expressions. |
| **Pre-Commit Hooks (`pre-commit`)** | Automatically runs schema validation and YAML linting on `git commit`. | Prevents invalid YAML files from ever being committed to Git. |
| **CI/CD Pipeline Validation** | Automated GitHub Actions or Azure DevOps pipeline on Pull Requests. | Automated PR review: failing builds block merges if metadata validation or tests fail. |

---

## 🟢 3. COULD HAVE (Advanced Developer & Pipeline DX)

High-leverage enhancements to streamline daily operation and pipeline deployment:

| Feature / Package | Purpose | Value & Rationale |
| :--- | :--- | :--- |
| **`rich` / `typer`** | Enhanced terminal formatting with color-coded status tables and progress bars. | Provides clean visual feedback during bulk compilation and testing. |
| **ADF Pipeline Generator / Azure SDK** | Directly deploy or trigger ADF Copy Activity pipelines from compiled manifests. | Closes the loop from metadata Git commit to live Azure pipeline execution. |
| **Source Schema Drift Detection** | Query source catalogs (`INFORMATION_SCHEMA` / OData `$metadata`) to compare declared columns. | Warns if source columns were renamed or deleted before ingestion runs. |

---

## ⚪ 4. WON'T HAVE (Out of Scope for Now)

To prevent premature over-engineering, the following items are intentionally omitted:

* **Custom Web Admin Portal:** Maintaining YAML files in Git with IDE autocomplete provides version control, audit trails, and zero hosting/maintenance overhead.
* **Full Data Transformation / dbt Layer:** Landing zone ingestion remains strictly decoupled from Silver and Gold business transformations.
* **Heavy Orchestration Overhead (Airflow/Prefect):** ADF native Copy Activities with pagination rules handle the landing ingestion with zero extra infrastructure.
