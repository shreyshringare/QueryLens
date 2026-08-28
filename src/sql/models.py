from dataclasses import dataclass, field


@dataclass
class ColumnReference:
    table: str | None
    column: str


@dataclass
class Join:
    join_type: str
    table: str
    left: ColumnReference
    right: ColumnReference


@dataclass
class Filter:
    column: ColumnReference
    operator: str
    value: str


@dataclass
class Aggregation:
    function: str
    column: ColumnReference | None


@dataclass
class OrderBy:
    expression: str
    direction: str


@dataclass
class SQLStructure:
    select_columns: list[ColumnReference] = field(default_factory=list)
    tables: list[str] = field(default_factory=list)
    joins: list[Join] = field(default_factory=list)
    filters: list[Filter] = field(default_factory=list)
    aggregations: list[Aggregation] = field(default_factory=list)
    group_by: list[ColumnReference] = field(default_factory=list)
    order_by: list[OrderBy] = field(default_factory=list)
    limit: int | None = None
    cte_names: list[str] = field(default_factory=list)
