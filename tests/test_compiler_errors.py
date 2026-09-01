"""Tests for fail-loud compiler validation and friendly error paths."""

from pathlib import Path

import pytest
import yaml

from metadata_ingestion_framework.compiler import MetadataCompiler
from metadata_ingestion_framework.dialects import StrategyRegistry, UnknownSystemTypeError


def _make_source(tmp_path: Path, system_type: str = "mssql") -> MetadataCompiler:
    src = tmp_path / "src1"
    src.mkdir()
    (src / "_source.yml").write_text(yaml.safe_dump({"source": {"system_type": system_type}}))
    (src / "t.yml").write_text(yaml.safe_dump({"table": {"name": "T"}}))
    return MetadataCompiler(metadata_dir=tmp_path)


def test_unknown_system_type_raises(tmp_path: Path) -> None:
    compiler = _make_source(tmp_path, system_type="azure_cosmos_db_for_nosql")
    with pytest.raises(UnknownSystemTypeError, match="Supported types"):
        compiler.compile("src1", "t")


def test_unknown_source_lists_available() -> None:
    compiler = MetadataCompiler()
    with pytest.raises(FileNotFoundError, match="Available sources"):
        compiler.compile("does_not_exist", "t")


def test_unknown_table_lists_available() -> None:
    compiler = MetadataCompiler()
    with pytest.raises(FileNotFoundError, match="Available tables"):
        compiler.compile("m3", "does_not_exist")


def test_missing_watermark_column_raises(tmp_path: Path) -> None:
    compiler = _make_source(tmp_path)
    (tmp_path / "src1" / "t.yml").write_text(
        yaml.safe_dump(
            {"table": {"loads": {"incremental": {"overlap_period": "3 days"}},
                       "subscriptions": [{"name": "s1", "load": "incremental"}]}}
        )
    )
    with pytest.raises(ValueError, match="requires a 'watermark_column'"):
        compiler.compile("src1", "t")


def test_unsupported_watermark_format_raises(tmp_path: Path) -> None:
    compiler = _make_source(tmp_path)
    (tmp_path / "src1" / "t.yml").write_text(
        yaml.safe_dump(
            {"table": {"loads": {"incremental": {
                "watermark_column": "updated_at",
                "watermark_format": "iso8601",
                "overlap_period": "3 days",
            }},
             "subscriptions": [{"name": "s1", "load": "incremental"}]}}
        )
    )
    with pytest.raises(ValueError, match="unsupported watermark_format"):
        compiler.compile("src1", "t")


def test_subscription_references_undefined_load(tmp_path: Path) -> None:
    compiler = _make_source(tmp_path)
    (tmp_path / "src1" / "t.yml").write_text(
        yaml.safe_dump(
            {"table": {"loads": {"full": {}},
                       "subscriptions": [{"name": "s1", "load": "incremental"}]}}
        )
    )
    with pytest.raises(ValueError, match="references undefined load"):
        compiler.compile("src1", "t")


def test_implicit_full_load_without_loads_entry(tmp_path: Path) -> None:
    compiler = _make_source(tmp_path)
    (tmp_path / "src1" / "t.yml").write_text(
        yaml.safe_dump(
            {"table": {"subscriptions": [{"name": "s1", "load": "full"}]}}
        )
    )
    manifest = compiler.compile("src1", "t")
    assert manifest.subscriptions[0].load_type == "full"
    assert "WHERE" not in manifest.subscriptions[0].query_template


def test_undeclared_watermark_load_still_raises(tmp_path: Path) -> None:
    compiler = _make_source(tmp_path)
    (tmp_path / "src1" / "t.yml").write_text(
        yaml.safe_dump(
            {"table": {"subscriptions": [{"name": "s1", "load": "incremental"}]}}
        )
    )
    with pytest.raises(ValueError, match="references undefined load"):
        compiler.compile("src1", "t")


def test_subscription_without_name_raises(tmp_path: Path) -> None:
    compiler = _make_source(tmp_path)
    (tmp_path / "src1" / "t.yml").write_text(
        yaml.safe_dump(
            {"table": {"loads": {"full": {}},
                       "subscriptions": [{"load": "full"}]}}
        )
    )
    with pytest.raises(ValueError, match="without a name"):
        compiler.compile("src1", "t")


@pytest.mark.parametrize(
    ("source", "table"),
    [("m3", "fgledg"), ("m3", "mitmas"), ("m3", "mitwhl"),
     ("m3", "ocusad"), ("m3", "ocusma"), ("m3", "osbstd"),
     ("thinkwise", "agreement")],
)
def test_real_tables_compile(source: str, table: str) -> None:
    manifest = MetadataCompiler().compile(source, table)
    assert manifest.subscriptions


def test_registry_known_types() -> None:
    for system_type in ("db2", "mssql", "sqlserver", "oracle", "rest_api"):
        StrategyRegistry.get(system_type)
