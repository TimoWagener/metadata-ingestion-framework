import argparse
from pathlib import Path
import sys
from typing import Any, Dict
import yaml

# Ensure src directory is in sys.path for direct script execution
if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))

from metadata_ingestion_framework.compiler import MetadataCompiler

METADATA_DIR = Path(__file__).parent / "metadata"


def load_yaml(file_path: Path) -> Dict[str, Any]:
    """Load and parse a YAML file safely."""
    if not file_path.exists():
        raise FileNotFoundError(f"Metadata file not found: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def inspect(source_name: str = "m3", table_name: str = "osbstd") -> None:
    source_file = METADATA_DIR / source_name / "_source.yml"
    table_file = METADATA_DIR / source_name / f"{table_name.lower()}.yml"

    source_data = load_yaml(source_file).get("source", {})
    table_data = load_yaml(table_file).get("table", {})

    compiler = MetadataCompiler(METADATA_DIR)
    manifest = compiler.compile(source_name, table_name)

    print("=" * 80)
    print(f"  METADATA INSPECTOR: Source '{source_name}' -> Table '{table_name.upper()}'")
    print("=" * 80)

    # 1. Source Details
    print("\n--- [1] Source Configuration ---")
    print(f"System Name:        {source_data.get('system_name')}")
    print(f"System Type:        {source_data.get('system_type')}")
    print(f"Naming Convention:  {source_data.get('naming_convention')}")
    print(f"Auth Type:          {source_data.get('auth', {}).get('type')}")
    print(f"Secret Name:        {source_data.get('auth', {}).get('secret_name')}")
    print(f"Default Schema:     {source_data.get('defaults', {}).get('schema', 'N/A')}")
    print(f"Landing Format:     {source_data.get('defaults', {}).get('landing_format')}")

    # 2. Table Details
    print("\n--- [2] Table Configuration ---")
    print(f"Table Name:         {table_data.get('name', table_name.upper())}")
    print(f"Primary Key:        {table_data.get('primary_key')}")
    columns = table_data.get("columns", ["*"])
    print(f"Columns ({len(columns)} cols): {columns[:6]}..." if len(columns) > 6 else f"Columns: {columns}")
    print(f"Static Filters:     {table_data.get('filters', [])}")

    # 3. Subscriptions & Generated SQL
    print("\n--- [3] Compiled Ingestion Subscriptions ---")
    for sub in manifest.subscriptions:
        status = "[ACTIVE]" if sub.active else "[INACTIVE / AD-HOC]"
        print(f"\n>> Subscription: {sub.name} {status}")
        print(f"   Load Type:    {sub.load_type}")
        print(f"   Landing Path: {sub.landing_path}")

        if sub.runtime_date_generator:
            gen = sub.runtime_date_generator
            print(f"   Date Generator:")
            print(f"     - Period:              {gen.period} ({gen.format})")
            print(f"     - Source Runtime Code: {gen.source_runtime_code}")
            print(f"     - ADF Expression:      {gen.adf_runtime_code}")

        if sub.adf_pagination_rules:
            print(f"   ADF Pagination Rules: {sub.adf_pagination_rules}")

        print(f"   [Executable Query (Direct Run)]:\n{sub.query}")
        print(f"   [Parameterized Template (ADF Run)]:\n{sub.query_template}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect metadata definitions and compiled queries.")
    parser.add_argument("--source", "-s", default="m3", help="Source system name (default: m3)")
    parser.add_argument("--table", "-t", default="osbstd", help="Table name (default: osbstd)")
    args = parser.parse_args()

    inspect(args.source, args.table)


if __name__ == "__main__":
    main()
