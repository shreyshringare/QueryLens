from dataclasses import dataclass


@dataclass
class AdaptResult:
    sql: str | None
    success: bool
    error: str | None
    source_dialect: str
    target_dialect: str
