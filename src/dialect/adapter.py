# src/dialect/adapter.py
import sqlglot
from sqlglot.errors import ErrorLevel

from .models import AdaptResult


class DialectAdapter:

    CANONICAL_TO_SQLGLOT = {
        "postgresql": "postgres",
        "mysql": "mysql",
        "sqlite": "sqlite",
        "duckdb": "duckdb",
    }

    def _resolve(self, dialect: str) -> str | None:
        return self.CANONICAL_TO_SQLGLOT.get(dialect)

    def adapt(self, sql: str, source_dialect: str, target_dialect: str) -> AdaptResult:

        resolved_source = self._resolve(source_dialect)
        resolved_target = self._resolve(target_dialect)

        if resolved_source is None:
            return AdaptResult(
                sql=None,
                success=False,
                error=f"Unknown dialect: {source_dialect}",
                source_dialect=source_dialect,
                target_dialect=target_dialect,
            )

        if resolved_target is None:
            return AdaptResult(
                sql=None,
                success=False,
                error=f"Unknown dialect: {target_dialect}",
                source_dialect=source_dialect,
                target_dialect=target_dialect,
            )

        # unsupported_level=RAISE: sqlglot's default silently embeds a warning
        # comment in the output SQL for unsupported constructs instead of
        # failing. RAISE converts that into a catchable UnsupportedError so a
        # broken transpile can never silently reach the execution agent.
        statements = sqlglot.transpile(
            sql,
            read=resolved_source,
            write=resolved_target,
            unsupported_level=ErrorLevel.RAISE,
        )

        return AdaptResult(
            sql="; ".join(statements),
            success=True,
            error=None,
            source_dialect=source_dialect,
            target_dialect=target_dialect,
        )
