from pathlib import Path
from typing import Any, Dict, Optional
import yaml

METADATA_DIR = Path(__file__).parent / "metadata"


def load_yaml(file_path: Path) -> Dict[str, Any]:
    """Load and parse a YAML file safely."""
    if not file_path.exists():
        raise FileNotFoundError(f"Metadata file not found: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_source_metadata(source_name: str) -> Dict[str, Any]:
    """Load the _source.yml for a given source system."""
    source_path = METADATA_DIR / source_name / "_source.yml"
    data = load_yaml(source_path)
    return data.get("source", {})


def load_table_metadata(source_name: str, table_name: str) -> Dict[str, Any]:
    """Load table metadata (e.g. osbstd.yml) for a given source."""
    table_path = METADATA_DIR / source_name / f"{table_name.lower()}.yml"
    data = load_yaml(table_path)
    return data.get("table", {})


def build_sql_query(
    source_meta: Dict[str, Any],
    table_meta: Dict[str, Any],
    subscription_name: Optional[str] = None,
) -> str:
    """Build the extraction SQL query based on metadata configuration."""
    schema = table_meta.get("schema") or source_meta.get("defaults", {}).get("schema", "dbo")
    table_name = table_meta["name"]
    columns = ", ".join(table_meta.get("columns", ["*"]))

    # Base WHERE clauses from static table filters
    where_clauses = list(table_meta.get("filters", []))

    # Add watermark/boundary condition if subscription requested
    if subscription_name:
        subscriptions = table_meta.get("subscriptions", [])
        subscription = next((s for s in subscriptions if s.get("name") == subscription_name), None)
        if subscription:
            load = subscription.get("load", {})
            load_type = load.get("type")
            watermark_col = load.get("watermark_column")

            if load_type in ("incremental_overlap", "incremental_append"):
                lookback = load.get("lookback_period", "0 days")
                where_clauses.append(f"{watermark_col} >= :watermark_date (lookback: {lookback})")
            elif load_type == "bounded_full_load":
                boundary = load.get("boundary_period", "1 calendar year")
                where_clauses.append(f"{watermark_col} >= :boundary_date (period: {boundary})")

    where_sql = "\n  WHERE " + "\n    AND ".join(where_clauses) if where_clauses else ""
    isolation = "\n  WITH UR" if source_meta.get("system_type") == "db2" else ""

    return f"SELECT {columns}\n  FROM {schema}.{table_name}{where_sql}{isolation};"


def main() -> None:
    source_name = "m3"
    table_name = "osbstd"

    print("=================================================================")
    print(f"  Loading Metadata for Source: '{source_name}' & Table: '{table_name}'")
    print("=================================================================\n")

    # 1. Load source and table metadata
    source_meta = load_source_metadata(source_name)
    table_meta = load_table_metadata(source_name, table_name)

    # 2. Display Source Details
    print("--- [1] Source Configuration ---")
    print(f"System Name:        {source_meta.get('system_name')}")
    print(f"System Type:        {source_meta.get('system_type')}")
    print(f"Naming Convention:  {source_meta.get('naming_convention')}")
    print(f"Auth Type:          {source_meta.get('auth', {}).get('type')}")
    print(f"Secret Name:        {source_meta.get('auth', {}).get('secret_name')}")
    print(f"Default Schema:     {source_meta.get('defaults', {}).get('schema')}")
    print(f"Landing Format:     {source_meta.get('defaults', {}).get('landing_format')}\n")

    # 3. Display Table Details
    print("--- [2] Table Configuration ---")
    print(f"Table Name:         {table_meta.get('name')}")
    print(f"Primary Key:        {table_meta.get('primary_key')}")
    print(f"Columns ({len(table_meta.get('columns', []))} cols): {table_meta.get('columns')[:5]}...")
    print(f"Filters:            {table_meta.get('filters')}\n")

    # 4. Display Subscriptions & Generated SQL Queries
    print("--- [3] Subscriptions & Generated Extraction SQL ---")
    for sub in table_meta.get("subscriptions", []):
        sub_name = sub.get("name")
        active_status = "[ACTIVE]" if sub.get("active", True) else "[INACTIVE/ADHOC]"
        load_type = sub.get("load", {}).get("type")
        print(f"\nSubscription: {sub_name} {active_status}")
        print(f"Load Type:    {load_type}")

        # Compile extract SQL for this subscription
        query = build_sql_query(source_meta, table_meta, subscription_name=sub_name)
        print("Generated SQL:")
        print(query)


if __name__ == "__main__":
    main()
