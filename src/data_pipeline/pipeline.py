"""
pipeline.py — Top-level convenience function for single-record normalisation.

This module ties together the two-stage transformation:
    adapt_record()   → source-aware field mapping
    QueryNormalizer  → typed NormalizedQuery + dialect normalisation

Most callers only need this one function.  They don't need to know whether
a record came from Spider, BIRD, or a synthetic file — they just call
normalize_record(source, raw_dict, index) and get back a NormalizedQuery.

Motivation: keeping the two-stage composition here (rather than inlining it
everywhere) means future changes to the pipeline shape (e.g. adding a SQL
normalisation step) happen in one place.
"""

from typing import Any

from .adapt import adapt_record
from .normalizer import QueryNormalizer


def normalize_record(
    source: str,
    record: dict[str, Any],
    index: int,
) -> "NormalizedQuery":  # type: ignore[name-defined]
    """
    Adapt and normalise a single raw record into a NormalizedQuery.

    This is the main entry-point used by both the dataset builder script
    (build_normalized_dataset.py) and the test suite.

    Parameters
    ----------
    source : str
        Dataset origin: "spider" | "bird" | "synthetic".
    record : dict
        Raw JSON object loaded directly from the source file.
    index : int
        Zero-based position of the record in the current batch.
        Used as the record id and as a component of fallback identifiers.

    Returns
    -------
    NormalizedQuery
        Fully typed record ready for validation, deduplication, and splitting.

    Raises
    ------
    ValueError
        Propagated from QueryNormalizer when question or SQL is missing.
    ValueError
        Raised by adapt_record when `source` is not registered.
    """
    # Stage 1: source-specific field mapping → canonical intermediate dict
    adapted = adapt_record(source, record)

    # Stage 2: field extraction, dialect normalisation, type coercion
    normalizer = QueryNormalizer(source)

    return normalizer.normalize(adapted, index)