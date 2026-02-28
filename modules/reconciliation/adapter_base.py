"""Base class for reconciliation adapters."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List
from .models import ReconSummary, ReconException, ReconEntry


class ReconAdapterBase(ABC):
    """Abstract base class for reconciliation adapters."""

    @property
    @abstractmethod
    def module_key(self) -> str:
        """Unique key for this adapter."""
        pass

    @property
    @abstractmethod
    def module_name(self) -> str:
        """Human-readable name for this adapter."""
        pass

    @abstractmethod
    def get_expected(self, session) -> float:
        """Return the expected (system) total for this module."""
        pass

    @abstractmethod
    def get_actual(self, session) -> float:
        """Return the actual (user-entered) total for this module."""
        pass

    @abstractmethod
    def get_entries(self, session) -> List[ReconEntry]:
        """Return a list of ReconEntry objects representing system entries for this module."""
        pass

    @abstractmethod
    def summarize(self, session) -> ReconSummary:
        """Return a summary object for this module."""
        pass

    @abstractmethod
    def validate(self, session) -> List[ReconException]:
        """Validate the reconciliation and return any exceptions."""
        pass