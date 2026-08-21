"""
quality.py — Quality report generation for the normalised dataset.

Motivation: "the dataset loaded" tells you nothing.  A quality report tells
you *exactly* why records were rejected and where the data gaps are:

    {
        "total_records":    1000,
        "valid_records":    970,
        "invalid_records":  30,
        "duplicates_removed": 42,
        "missing_ddl":      10,
        "missing_sql":       5,
        "missing_question": 15
    }

This informs targeted remediation:
  - High missing_ddl  → source files lack inline schemas; fix the DDL injection
    logic or add schema.sql files to the raw directories.
  - High duplicates   → check for overlapping source files before re-running.
  - High invalid      → review validation thresholds or adapter field mapping.

QualityReport is a dataclass (mutable, incrementally updated) rather than a
function that returns a dict, because the builder accumulates counts as it
processes record-by-record and needs a shared mutable object.

statistics.json (produced by save_statistics) is separate from quality_report.json:
  - statistics.json  → distribution analysis (sources, dialects, databases)
  - quality_report.json → pipeline health (what was rejected and why)
"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Union

from .models import NormalizedQuery
from .stats import dataset_statistics


@dataclass
class QualityReport:
    """
    Mutable accumulator for dataset build quality metrics.

    Fields
    ------
    total_records      Total raw records encountered across all sources.
    valid_records      Records that passed all validation checks.
    invalid_records    Records rejected by validate_record() or that raised
                       an exception during normalization.
    duplicates_removed Records removed by the deduplication step.
    missing_ddl        Raw records that had no inline DDL and no sibling
                       schema.sql to inject from.
    missing_sql        Raw records with no SQL field in any expected key.
    missing_question   Raw records with no natural-language question field.
    error_details      Optional dict for finer-grained error breakdowns
                       (e.g. per-source counts).  Omitted from the saved
                       JSON when empty to keep the output clean.
    """

    total_records:     int = 0
    valid_records:     int = 0
    invalid_records:   int = 0
    duplicates_removed: int = 0
    missing_ddl:       int = 0
    missing_sql:       int = 0
    missing_question:  int = 0
    # Optional finer breakdown — not emitted to JSON when empty
    error_details: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """
        Serialise to a plain dict.

        Drops error_details when empty so the saved JSON stays clean and
        matches the specification format.
        """
        res = asdict(self)
        if not res["error_details"]:
            del res["error_details"]
        return res

    def save(self, path: Union[str, Path]) -> None:
        """
        Write the quality report to a JSON file at `path`.

        Parent directories are created automatically so the caller does not
        need to pre-create data/processed/.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=4, ensure_ascii=False)


def save_statistics(
    records: list[NormalizedQuery],
    path: Union[str, Path],
) -> None:
    """
    Compute and write dataset distribution statistics to a JSON file.

    This produces data/processed/statistics.json — a complement to
    quality_report.json that focuses on *what* is in the dataset rather
    than *what was rejected*.

    Counter objects from collections are not JSON-serialisable by default,
    so they are converted to plain dicts before writing.

    Parameters
    ----------
    records : list[NormalizedQuery]
        The final deduplicated dataset.
    path : str | Path
        Destination file path (e.g. PROCESSED_DIR / "statistics.json").
    """
    stats = dataset_statistics(records)

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        # Convert Counter objects → plain dict for JSON compatibility
        json_stats = {
            "total":     stats["total"],
            "sources":   dict(stats["sources"]),
            "domains":   dict(stats["domains"]),
            "dialects":  dict(stats["dialects"]),
            "databases": stats["databases"],
        }
        json.dump(json_stats, f, indent=4, ensure_ascii=False)
