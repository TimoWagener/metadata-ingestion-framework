from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import yaml

from metadata_ingestion_framework.dialects import AdfDialect, SourceStrategy, StrategyRegistry
from metadata_ingestion_framework.models import (
    CompiledSubscription,
    PeriodExpression,
    RuntimeDateGenerator,
    TableManifest,
)

METADATA_DIR = Path(__file__).parent / "metadata"

# Watermark storage formats the dialects can compile expressions for.
SUPPORTED_WATERMARK_FORMATS = {"yyyyMMdd", "unix_ms"}


class MetadataCompiler:
    """
    High-level compiler service that reads declarative YAML configurations
    and translates them into executable Ingestion Manifests.
    """

    def __init__(self, metadata_dir: Path = METADATA_DIR):
        self.metadata_dir = metadata_dir

    def _load_yaml(self, file_path: Path) -> Dict[str, Any]:
        if not file_path.exists():
            raise FileNotFoundError(f"Metadata file not found: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _resolve_predicates(
        self,
        strategy: SourceStrategy,
        load_cfg: Dict[str, Any],
        load_type: str,
        base_filters: List[str],
        system_type: str,
        pagination_cfg: Dict[str, Any],
        sub_name: Optional[str],
    ) -> Tuple[List[str], List[str], Optional[RuntimeDateGenerator]]:
        """Resolves where clauses and runtime date generators for a subscription."""
        if system_type == "rest_api":
            page_param = pagination_cfg.get("page_param", "$skip")
            size_param = pagination_cfg.get("size_param", "$top")
            page_size = pagination_cfg.get("page_size", 1000)
            return (
                [f"{page_param}=0&{size_param}={page_size}"],
                [f"{page_param}={{offset}}&{size_param}={page_size}"],
                None,
            )

        where_executable = list(base_filters)
        where_template = list(base_filters)
        date_gen = None

        if load_type in ("incremental_overlap", "incremental_append", "bounded_full_load"):
            param_name = "watermark_date" if "incremental" in load_type else "boundary_date"
            period_str = load_cfg.get("lookback_period" if "incremental" in load_type else "boundary_period", "0 days")
            watermark_fmt = load_cfg.get("watermark_format", "yyyyMMdd")
            col = load_cfg.get("watermark_column")
            if not col:
                raise ValueError(
                    f"Subscription '{sub_name}': load type '{load_type}' requires a 'watermark_column'."
                )
            if watermark_fmt not in SUPPORTED_WATERMARK_FORMATS:
                raise ValueError(
                    f"Subscription '{sub_name}': unsupported watermark_format '{watermark_fmt}'. "
                    f"Supported formats: {sorted(SUPPORTED_WATERMARK_FORMATS)}"
                )

            period = PeriodExpression.parse(period_str)
            source_code = strategy.date_offset(period, watermark_fmt)
            adf_code = AdfDialect.date_offset(period, watermark_fmt)

            where_template.append(f"{col} >= :{param_name}")
            where_executable.append(f"{col} >= {source_code}" if source_code else f"{col} >= :{param_name}")

            date_gen = RuntimeDateGenerator(
                parameter_name=param_name,
                period=period_str,
                format=watermark_fmt,
                source_runtime_code=source_code,
                adf_runtime_code=adf_code,
            )

        return where_executable, where_template, date_gen

    def compile(self, source_name: str, table_name: str) -> TableManifest:
        source_data = self._load_yaml(self.metadata_dir / source_name / "_source.yml").get("source", {})
        table_data = self._load_yaml(self.metadata_dir / source_name / f"{table_name.lower()}.yml").get("table", {})

        system_type = source_data.get("system_type", "mssql")
        strategy = StrategyRegistry.get(system_type)

        schema = table_data.get("schema") or source_data.get("defaults", {}).get("schema", "dbo")
        actual_table_name = table_data.get("name", table_name.upper())
        columns = table_data.get("columns", ["*"])
        base_filters = list(table_data.get("filters", []))
        landing_format = table_data.get("landing_format") or source_data.get("defaults", {}).get("landing_format", "parquet")
        collection_ref = (
            table_data.get("collection_reference")
            or table_data.get("response_path")
            or source_data.get("defaults", {}).get("collection_reference", "value")
        )

        target = (
            f"{source_data.get('connection', {}).get('base_url', '').rstrip('/')}{table_data.get('endpoint', f'/{actual_table_name.lower()}')}"
            if system_type == "rest_api"
            else f"{schema}.{actual_table_name}"
        )

        pagination = table_data.get("pagination") or source_data.get("pagination", {})
        pagination_rules = strategy.build_pagination_rules(pagination, collection_ref)

        # Normalize subscriptions: auto-inject ad-hoc full load if not defined
        subscriptions = list(table_data.get("subscriptions", []))
        if not any(s.get("name") == "tr_adhoc_initial_load" for s in subscriptions):
            subscriptions.append({"name": "tr_adhoc_initial_load", "active": False, "load": {"type": "full_load"}})

        compiled_subscriptions = []
        for sub in subscriptions:
            sub_name = sub.get("name")
            active = sub.get("active", True)
            load = sub.get("load", {})
            load_type = load.get("type", "full_load")

            where_exec, where_tpl, date_gen = self._resolve_predicates(
                strategy, load, load_type, base_filters, system_type, pagination, sub_name
            )

            compiled_subscriptions.append(
                CompiledSubscription(
                    name=sub_name,
                    active=active,
                    load_type=load_type,
                    format=landing_format,
                    landing_path=f"landing/{source_name}/{actual_table_name.lower()}/subscription={sub_name}/",
                    query=strategy.build_query(target, columns, where_exec),
                    query_template=strategy.build_query(target, columns, where_tpl),
                    runtime_date_generator=date_gen,
                    adf_pagination_rules=pagination_rules,
                )
            )

        return TableManifest(
            source=source_name,
            system_type=system_type,
            table=actual_table_name,
            primary_key=table_data.get("primary_key", []),
            subscriptions=compiled_subscriptions,
        )

