"""Adapters package for reconciliation modules."""
from __future__ import annotations
import importlib
import logging
from typing import List
from ..adapter_base import ReconAdapterBase

logger = logging.getLogger(__name__)

# Auto-discover adapters
_adapters: List[ReconAdapterBase] = []

def _load_adapters():
    """Load all adapters from this package."""
    import pkgutil
    import modules.reconciliation.adapters as adapters_pkg

    for importer, modname, ispkg in pkgutil.iter_modules(adapters_pkg.__path__):
        if not ispkg:
            try:
                module = importlib.import_module(f"modules.reconciliation.adapters.{modname}")
                # Assume each module has an 'adapter' instance
                if hasattr(module, 'adapter'):
                    _adapters.append(module.adapter)
                    logger.info("Loaded adapter: %s", modname)
            except Exception as e:
                logger.warning("Failed to load adapter %s: %s", modname, e)

_load_adapters()

def get_all_adapters() -> List[ReconAdapterBase]:
    """Return all loaded adapters."""
    return _adapters.copy()