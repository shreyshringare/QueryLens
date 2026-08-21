"""
adapters/__init__.py — Public adapter exports.

Re-exports the three source adapters so callers can write:

    from src.data_pipeline.adapters import SpiderAdapter

instead of reaching into sub-modules directly.  This keeps the internal
module layout flexible — adapter files can be renamed or split without
changing any import outside this package.
"""

from .spider    import SpiderAdapter
from .bird      import BIRDAdapter
from .synthetic import SyntheticAdapter

__all__ = [
    "SpiderAdapter",
    "BIRDAdapter",
    "SyntheticAdapter",
]