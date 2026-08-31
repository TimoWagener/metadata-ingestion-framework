# Metadata Ingestion Framework

Declarative metadata framework that translates source and table YAML definitions into executable ingestion queries, paths, and Azure Data Factory (ADF) pagination rules.

## Setup

Requires [uv](https://docs.astral.sh/uv/).

```bash
# Clone the repository and install dependencies
git clone <repo-url>
cd metadata-ingestion-framework
uv sync
```

## Running the Compiler

Compile metadata for any source and table into an executable JSON manifest:

### 1. M3 Item Master (`M3.MITMAS` - Full Load)
```bash
uv run metadata-ingestion-framework --source m3 --table mitmas
```

### 2. M3 Sales Statistics (`M3.OSBSTD` - Incremental + Bounded Full Load)
```bash
uv run metadata-ingestion-framework --source m3 --table osbstd
```

### 3. Thinkwise Agreement (`thinkwise.agreement` - REST API with ADF Pagination)
```bash
uv run metadata-ingestion-framework --source thinkwise --table agreement
```

*(You can also run directly with `uv run src/metadata_ingestion_framework/main.py --source m3 --table mitmas`)*

## Metadata Inspector (Human-Readable Walkthrough)

Run the visual metadata inspector for detailed source, table, date generator, and query breakdowns:

```bash
# Default (M3 OSBSTD)
uv run src/metadata_ingestion_framework/inspect_metadata.py

# Any table
uv run src/metadata_ingestion_framework/inspect_metadata.py --source thinkwise --table agreement
```
