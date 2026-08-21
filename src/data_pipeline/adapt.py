"""
adapt.py — Adapter dispatcher.

Provides a single entry-point function adapt_record() that routes a raw dict
from any supported source to the correct adapter class.

Design decision — registry dict vs. if/elif chain:
  A dict lookup (O(1)) is cleaner than a growing if/elif chain, and adding a
  new source only requires registering one extra entry in ADAPTERS.  The
  adapter instances are created once at import time (flyweight pattern) so
  there is no per-call construction overhead.

Motivation: pipeline.py and build_normalized_dataset.py should not need to
import every adapter class individually.  This module is the single choke-point
where "which adapter handles this source?" is decided.
"""

from typing import Any

from .adapters import (
    BIRDAdapter,
    SpiderAdapter,
    SyntheticAdapter,
)

# Module-level registry: source label → singleton adapter instance.
# New sources are added here without changing any other module.
ADAPTERS: dict[str, object] = {
    "spider":    SpiderAdapter(),
    "bird":      BIRDAdapter(),
    "synthetic": SyntheticAdapter(),
}


def adapt_record(
    source: str,
    record: dict[str, Any],
) -> dict[str, Any]:
    """
    Dispatch a raw record to the appropriate source adapter and return
    the normalised intermediate dict.

    Parameters
    ----------
    source : str
        One of "spider", "bird", or "synthetic".  Case-insensitive.
    record : dict
        The raw JSON object loaded from the source file.

    Returns
    -------
    dict
        Intermediate canonical dict ready for QueryNormalizer.normalize().

    Raises
    ------
    ValueError
        If `source` is not registered in ADAPTERS.  This is an explicit fail-
        fast rather than a silent no-op so pipeline bugs are caught early.
    """
    # Normalise case so callers don't need to worry about "Spider" vs "spider"
    source = source.lower()

    if source not in ADAPTERS:
        raise ValueError(
            f"Unsupported source: '{source}'. "
            f"Registered sources: {list(ADAPTERS.keys())}"
        )

    return ADAPTERS[source].adapt(record)