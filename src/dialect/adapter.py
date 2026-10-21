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

        # Transpile call added in Task 3 — for now, resolution-only tests pass
        # because both failure branches above return before reaching here.
        raise NotImplementedError("transpile step added in Task 3")
