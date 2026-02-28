"""Repository interfaces for reconciliation domain."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Optional
from ...domain.entities import ReconciliationSession, VarianceExplanation


class ReconciliationSessionRepository(ABC):
    """Abstract repository for reconciliation sessions."""

    @abstractmethod
    def save(self, session: ReconciliationSession) -> int:
        """Save a session and return its ID."""
        pass

    @abstractmethod
    def find_by_id(self, session_id: int) -> Optional[ReconciliationSession]:
        """Find a session by ID."""
        pass

    @abstractmethod
    def find_all(self, start_date: Optional[str] = None,
                end_date: Optional[str] = None,
                status: Optional[str] = None,
                limit: int = 50,
                offset: int = 0) -> List[ReconciliationSession]:
        """Find all sessions with optional filters."""
        pass

    @abstractmethod
    def delete(self, session_id: int) -> None:
        """Delete a session."""
        pass


class VarianceExplanationRepository(ABC):
    """Abstract repository for variance explanations."""

    @abstractmethod
    def save(self, session_id: int, explanation: VarianceExplanation) -> int:
        """Save an explanation and return its ID."""
        pass

    @abstractmethod
    def find_by_session_id(self, session_id: int) -> List[VarianceExplanation]:
        """Find all explanations for a session."""
        pass

    @abstractmethod
    def update(self, explanation_id: int, explanation: str, amount: float) -> None:
        """Update an explanation."""
        pass

    @abstractmethod
    def delete(self, explanation_id: int) -> None:
        """Delete an explanation."""
        pass