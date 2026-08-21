"""
stats.py — Dataset distribution statistics.

After building the normalised dataset it is important to understand what you
have actually created.  Saying "the dataset loaded" is not informative enough.
Knowing the breakdown by source, domain, dialect, and database count lets you:
  - Detect class imbalance (e.g. 90 % Spider records → dialect bias toward SQLite)
  - Identify missing coverage (e.g. no finance domain in the dataset)
  - Monitor the effect of deduplication and capping across pipeline runs
  - Produce audit-ready artefacts (statistics.json) alongside the dataset

All statistics are computed in-memory with collections.Counter, which is O(n)
and adds negligible overhead even for datasets of tens of thousands of records.
"""

from collections import Counter
from typing import Any, Sequence

from .models import NormalizedQuery


def dataset_statistics(
    records: Sequence[NormalizedQuery],
) -> dict[str, Any]:
    """
    Compute distribution statistics for a collection of NormalizedQuery records.

    Parameters
    ----------
    records : Sequence[NormalizedQuery]
        The full (post-dedup) dataset to analyse.

    Returns
    -------
    dict with keys:
        total     : int            — total number of records
        sources   : Counter[str]   — count per source label
        domains   : Counter[str]   — count per semantic domain
        dialects  : Counter[str]   — count per SQL dialect
        databases : int            — number of unique database_id values
    """
    return {
        "total": len(records),

        # Counter automatically sorts by frequency when printed; most_common()
        # is available for descending display in format_dataset_statistics().
        "sources":  Counter(r.source      for r in records),
        "domains":  Counter(r.domain      for r in records),
        "dialects": Counter(r.dialect     for r in records),

        # Unique database count — the key metric for database-level splitting.
        # A dataset with 1000 records across 10 databases will produce very
        # different splits than one with 1000 records across 800 databases.
        "databases": len(set(r.database_id for r in records)),
    }


def format_dataset_statistics(stats: dict[str, Any]) -> str:
    """
    Format a statistics dict (from dataset_statistics) into a readable string
    suitable for printing to the terminal or writing to a log file.

    The format mirrors the STEP 30 specification:

        Total records: 12,500

        Sources:
          spider: 7,000
          bird: 5,000
          synthetic: 500

        Dialects: …
        Databases: …

    Parameters
    ----------
    stats : dict
        Output of dataset_statistics().

    Returns
    -------
    str
        Multi-line formatted report.
    """
    lines = [
        f"Total records: {stats['total']:,}\n",
        "Sources:",
    ]
    # most_common() lists entries highest → lowest count
    for source, count in stats["sources"].most_common():
        lines.append(f"  {source}: {count:,}")

    lines.append("\nDomains:")
    for domain, count in stats["domains"].most_common():
        lines.append(f"  {domain}: {count:,}")

    lines.append("\nDialects:")
    for dialect, count in stats["dialects"].most_common():
        lines.append(f"  {dialect}: {count:,}")

    # Singular number — no per-item breakdown needed here
    lines.append(f"\nDatabases:\n  {stats['databases']:,}")

    return "\n".join(lines)


def print_dataset_statistics(
    records_or_stats: Any,
) -> None:
    """
    Print a formatted statistics report to stdout.

    Accepts either a list of NormalizedQuery records (computes stats first) or
    a pre-computed stats dict (skips computation).  The dual-mode signature
    allows callers to reuse a stats dict they already have without recomputing.

    Parameters
    ----------
    records_or_stats : list[NormalizedQuery] | dict
        Either the raw record list or the output of dataset_statistics().
    """
    # Detect whether a pre-computed stats dict was passed in
    if isinstance(records_or_stats, dict) and "total" in records_or_stats:
        stats = records_or_stats
    else:
        stats = dataset_statistics(records_or_stats)

    print(format_dataset_statistics(stats))
