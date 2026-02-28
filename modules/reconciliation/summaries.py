"""Utility helpers for producing display-ready summary rows."""
from __future__ import annotations
from typing import List
from .core import orchestrator
from .models import ReconSummary


def get_summaries_for_session(session_id: int) -> List[ReconSummary]:
    """Get summaries for all modules in a session."""
    session = orchestrator.get_session(session_id)
    return orchestrator.run_all_summaries(session)
