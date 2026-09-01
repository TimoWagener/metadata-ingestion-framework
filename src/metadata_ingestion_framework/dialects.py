from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from metadata_ingestion_framework.models import PeriodExpression, PeriodUnit


class AdfDialect:
    """Azure Data Factory dynamic content expression compiler."""

    @staticmethod
    def date_offset(period: PeriodExpression, watermark_format: str) -> str:
        if period.unit == PeriodUnit.CALENDAR_YEAR:
            offset = period.amount - 1
            return (
                "@formatDateTime(startOfYear(utcnow()), 'yyyyMMdd')"
                if offset == 0
                else f"@formatDateTime(addYears(startOfYear(utcnow()), -{offset}), 'yyyyMMdd')"
            )
        elif period.unit == PeriodUnit.DAY:
            return f"@formatDateTime(addDays(utcnow(), -{period.amount}), 'yyyyMMdd')"
        elif period.unit == PeriodUnit.HOUR and watermark_format == "unix_ms":
            return f"@string(div(sub(ticks(subtractFromTime(utcnow(), {period.amount}, 'Hour')), 621355968000000000), 10000))"
        return f"@addDays(utcnow(), -{period.amount})"


class SourceStrategy(ABC):
    """Abstract base strategy for dialect compilation."""

    @abstractmethod
    def date_offset(self, period: PeriodExpression, watermark_format: str) -> Optional[str]:
        pass

    @abstractmethod
    def build_query(self, target: str, columns: List[str], where_clauses: List[str]) -> str:
        pass

    def build_pagination_rules(
        self, pagination_cfg: Dict[str, Any], collection_ref: str
    ) -> Optional[Dict[str, str]]:
        return None


class DB2Strategy(SourceStrategy):
    """IBM DB2 for i / M3 dialect strategy."""

    def date_offset(self, period: PeriodExpression, watermark_format: str) -> str:
        if period.unit == PeriodUnit.CALENDAR_YEAR:
            offset = period.amount - 1
            return (
                "INT(VARCHAR_FORMAT(CURRENT_DATE, 'YYYY0101'))"
                if offset == 0
                else f"INT(VARCHAR_FORMAT(CURRENT_DATE - {offset} YEARS, 'YYYY0101'))"
            )
        elif period.unit == PeriodUnit.DAY and watermark_format == "yyyyMMdd":
            return f"INT(VARCHAR_FORMAT(CURRENT_DATE - {period.amount} DAYS, 'YYYYMMDD'))"
        elif period.unit == PeriodUnit.HOUR and watermark_format == "unix_ms":
            return (
                f"(BIGINT(DAYS(CURRENT_TIMESTAMP - {period.amount} HOURS) - DAYS('1970-01-01')) * 86400000 "
                f"+ MIDNIGHT_SECONDS(CURRENT_TIMESTAMP - {period.amount} HOURS) * 1000)"
            )
        return f"CURRENT_DATE - {period.amount} DAYS"

    def build_query(self, target: str, columns: List[str], where_clauses: List[str]) -> str:
        cols = ", ".join(columns)
        where_sql = "\n  WHERE " + "\n    AND ".join(where_clauses) if where_clauses else ""
        return f"SELECT {cols}\n  FROM {target}{where_sql}\n  WITH UR;"


class MSSQLStrategy(SourceStrategy):
    """Microsoft SQL Server dialect strategy."""

    def date_offset(self, period: PeriodExpression, watermark_format: str) -> str:
        if period.unit == PeriodUnit.CALENDAR_YEAR:
            offset = period.amount - 1
            return (
                "CONVERT(INT, CONVERT(VARCHAR(4), DATEPART(year, GETDATE())) + '0101')"
                if offset == 0
                else f"CONVERT(INT, CONVERT(VARCHAR(4), DATEPART(year, GETDATE()) - {offset}) + '0101')"
            )
        elif period.unit == PeriodUnit.DAY and watermark_format == "yyyyMMdd":
            return f"CONVERT(INT, CONVERT(VARCHAR(8), DATEADD(day, -{period.amount}, GETDATE()), 112))"
        elif period.unit == PeriodUnit.HOUR and watermark_format == "unix_ms":
            return f"DATEDIFF_BIG(ms, '1970-01-01', DATEADD(hour, -{period.amount}, GETUTCDATE()))"
        return f"DATEADD(day, -{period.amount}, GETDATE())"

    def build_query(self, target: str, columns: List[str], where_clauses: List[str]) -> str:
        cols = ", ".join(columns)
        where_sql = "\n  WHERE " + "\n    AND ".join(where_clauses) if where_clauses else ""
        return f"SELECT {cols}\n  FROM {target}{where_sql};"


class OracleStrategy(SourceStrategy):
    """Oracle DB dialect strategy."""

    def date_offset(self, period: PeriodExpression, watermark_format: str) -> str:
        if period.unit == PeriodUnit.CALENDAR_YEAR:
            offset_months = (period.amount - 1) * 12
            return (
                "TO_NUMBER(TO_CHAR(TRUNC(SYSDATE, 'YYYY'), 'YYYYMMDD'))"
                if offset_months == 0
                else f"TO_NUMBER(TO_CHAR(TRUNC(ADD_MONTHS(SYSDATE, -{offset_months}), 'YYYY'), 'YYYYMMDD'))"
            )
        elif period.unit == PeriodUnit.DAY and watermark_format == "yyyyMMdd":
            return f"TO_NUMBER(TO_CHAR(SYSDATE - {period.amount}, 'YYYYMMDD'))"
        elif period.unit == PeriodUnit.HOUR and watermark_format == "unix_ms":
            return f"ROUND((SYSDATE - {period.amount}/24 - TO_DATE('1970-01-01', 'YYYY-MM-DD')) * 86400000)"
        return f"SYSDATE - {period.amount}"

    def build_query(self, target: str, columns: List[str], where_clauses: List[str]) -> str:
        cols = ", ".join(columns)
        where_sql = "\n  WHERE " + "\n    AND ".join(where_clauses) if where_clauses else ""
        return f"SELECT {cols}\n  FROM {target}{where_sql};"


class RestApiStrategy(SourceStrategy):
    """REST API URL & Pagination Strategy."""

    def date_offset(self, period: PeriodExpression, watermark_format: str) -> Optional[str]:
        return None

    def build_query(self, target: str, columns: List[str], where_clauses: List[str]) -> str:
        query_params = f"?{where_clauses[0]}" if where_clauses else ""
        return f"GET {target}{query_params}"

    def build_pagination_rules(
        self, pagination_cfg: Dict[str, Any], collection_ref: str
    ) -> Optional[Dict[str, str]]:
        pag_type = pagination_cfg.get("type")
        if pag_type == "offset_limit":
            page_size = pagination_cfg.get("page_size", 1000)
            return {
                "AbsoluteUrl.{offset}": f"RANGE:0::{page_size}",
                f"EndCondition:$.{collection_ref}": "Empty",
            }
        elif pag_type == "cursor":
            cursor_path = pagination_cfg.get("cursor_path", "@odata.nextLink")
            return {"AbsoluteUrl": f"Body:$.[{cursor_path}]"}
        return None


_SYSTEM_TYPES = {"db2", "mssql", "sqlserver", "oracle", "rest_api"}


class UnknownSystemTypeError(ValueError):
    """Raised when metadata declares a system_type with no compiled strategy."""


class StrategyRegistry:
    """Registry mapping system_type to appropriate SourceStrategy."""

    _strategies: Dict[str, SourceStrategy] = {
        "db2": DB2Strategy(),
        "mssql": MSSQLStrategy(),
        "sqlserver": MSSQLStrategy(),
        "oracle": OracleStrategy(),
        "rest_api": RestApiStrategy(),
    }

    @classmethod
    def get(cls, system_type: str) -> "SourceStrategy":
        key = system_type.lower()
        if key not in cls._strategies:
            raise UnknownSystemTypeError(
                f"Unknown system_type '{system_type}'. Supported types: {sorted(cls._strategies)}"
            )
        return cls._strategies[key]
