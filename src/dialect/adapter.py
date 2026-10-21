import sqlglot
from sqlglot.errors import ErrorLevel, SqlglotError

from .models import AdaptResult


class DialectAdapter:

    # Maps the project's canonical dialect names (src/data_pipeline/dialects.py
    # ::SUPPORTED_DIALECTS) to sqlglot's own dialect keys. sqlglot has no
    # "postgresql" alias and raises ValueError if given one directly — this
    # map exists specifically to prevent that crash. "unknown" (the pipeline's
    # sentinel for unrecognized dialects) is intentionally absent: any name
    # not in this map is unresolvable and short-circuits before any sqlglot call.
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

        # unsupported_level=RAISE: sqlglot's default (WARN) only logs a
        # warning via Python's logging module and still returns the
        # (possibly degraded) SQL — a caller checking only the return value
        # would never notice. RAISE converts that into a catchable
        # UnsupportedError so a broken transpile can never silently reach
        # the execution agent.
        try:
            statements = sqlglot.transpile(
                sql,
                read=resolved_source,
                write=resolved_target,
                unsupported_level=ErrorLevel.RAISE,
            )
        except SqlglotError as exc:
            return AdaptResult(
                sql=None,
                success=False,
                error=str(exc),
                source_dialect=source_dialect,
                target_dialect=target_dialect,
            )

        return AdaptResult(
            sql="; ".join(statements),
            success=True,
            error=None,
            source_dialect=source_dialect,
            target_dialect=target_dialect,
        )
