from dataclasses import asdict, dataclass, field
from enum import Enum
import re
from typing import Any, Dict, List, Optional


class PeriodUnit(str, Enum):
    HOUR = "hour"
    DAY = "day"
    MONTH = "month"
    CALENDAR_YEAR = "calendar_year"


@dataclass(frozen=True)
class PeriodExpression:
    """Value object representing a period offset (e.g. 3 days, 1 calendar year)."""

    amount: int
    unit: PeriodUnit

    _UNIT_MAPPING = {
        "calendar_year": PeriodUnit.CALENDAR_YEAR,
        "year": PeriodUnit.CALENDAR_YEAR,
        "month": PeriodUnit.MONTH,
        "day": PeriodUnit.DAY,
        "hour": PeriodUnit.HOUR,
        "hr": PeriodUnit.HOUR,
    }

    @classmethod
    def parse(cls, raw: str) -> "PeriodExpression":
        match = re.match(
            r"(\d+)\s*(calendar\s*years?|years?|months?|days?|hours?|hrs?)",
            raw.strip().lower(),
        )
        if not match:
            raise ValueError(f"Invalid period expression: {raw}")

        amount = int(match.group(1))
        normalized_unit = match.group(2).replace(" ", "_").rstrip("s")
        try:
            unit = cls._UNIT_MAPPING[normalized_unit]
        except KeyError:
            raise ValueError(
                f"Unknown period unit in '{raw}'. Supported units: {sorted(set(cls._UNIT_MAPPING))}"
            ) from None
        return cls(amount=amount, unit=unit)


@dataclass
class RuntimeDateGenerator:
    parameter_name: str
    period: str
    format: str
    source_runtime_code: Optional[str]
    adf_runtime_code: str


@dataclass
class CompiledSubscription:
    name: str
    active: bool
    load_type: str
    format: str
    landing_path: str
    query: str
    query_template: str
    runtime_date_generator: Optional[RuntimeDateGenerator] = None
    adf_pagination_rules: Optional[Dict[str, str]] = None


@dataclass
class TableManifest:
    source: str
    system_type: str
    table: str
    primary_key: List[str]
    subscriptions: List[CompiledSubscription] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        def strip_none(obj: Any) -> Any:
            if isinstance(obj, dict):
                return {k: strip_none(v) for k, v in obj.items() if v is not None}
            elif isinstance(obj, list):
                return [strip_none(v) for v in obj if v is not None]
            return obj

        return strip_none(asdict(self))
