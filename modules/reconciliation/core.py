"""Orchestrator for modular reconciliation adapters."""
from __future__ import annotations
from typing import List
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from .adapters import get_all_adapters
from .models import ReconSession, ReconSummary, ReconException, ReconEntry
from .application.services import ReconciliationApplicationService

logger = logging.getLogger(__name__)


class ReconOrchestrator:
    """Manages reconciliation sessions and coordinates adapters."""

    def __init__(self):
        self.adapters = get_all_adapters()
        self.app_service = ReconciliationApplicationService()
        logger.info("Loaded %d adapters: %s", len(self.adapters), [a.module_key for a in self.adapters])

    def get_session(self, session_id: int) -> ReconSession:
        """Load a reconciliation session from DB."""
        session = self.app_service.get_session(session_id)
        if not session:
            raise ValueError(f"Invalid session id: {session_id}")

        # Convert domain entries to ReconEntry
        entries = []
        for e in session.entries:
            entries.append(ReconEntry(
                payment_method=e.payment_method,
                system_amount=e.system_amount,
                actual_amount=e.actual_amount,
                variance=e.variance,
                metadata={'is_reviewed': e.is_reviewed, 'notes': e.notes}
            ))

        return ReconSession(
            session_id=session.session_id,
            start_date=session.start_date,
            end_date=session.end_date,
            created_at=session.created_at or datetime.now(),
            entries=entries
        )

    def run_all_summaries(self, session: ReconSession) -> List[ReconSummary]:
        """Run summaries for all adapters in parallel."""
        summaries = []
        with ThreadPoolExecutor(max_workers=len(self.adapters)) as executor:
            future_to_adapter = {executor.submit(adapter.summarize, session): adapter for adapter in self.adapters}
            for future in as_completed(future_to_adapter):
                adapter = future_to_adapter[future]
                try:
                    summary = future.result()
                    summaries.append(summary)
                except Exception as e:
                    logger.exception("Adapter %s failed: %s", adapter.module_key, e)
                    # Add error summary
                    summaries.append(ReconSummary(
                        module_key=adapter.module_key,
                        module_name=adapter.module_name,
                        total_system=0.0,
                        total_actual=0.0,
                        total_variance=0.0,
                        entries_count=0,
                        status="error"
                    ))
        return summaries

    def run_all_validations(self, session: ReconSession) -> List[ReconException]:
        """Run validations for all adapters."""
        exceptions = []
        for adapter in self.adapters:
            try:
                adapter_exceptions = adapter.validate(session)
                exceptions.extend(adapter_exceptions)
            except Exception as e:
                logger.exception("Validation failed for %s: %s", adapter.module_key, e)
                exceptions.append(ReconException(
                    module_key=adapter.module_key,
                    description=f"Validation error: {str(e)}",
                    severity="error"
                ))
        return exceptions

    def get_module_entries(self, session: ReconSession, module_key: str) -> List[ReconEntry]:
        """Return entries produced by the adapter for the given module and session."""
        adapter = next((a for a in self.adapters if a.module_key == module_key), None)
        if not adapter:
            raise KeyError(module_key)
        try:
            return adapter.get_entries(session)
        except Exception as e:
            logger.exception('Adapter %s get_entries failed: %s', module_key, e)
            return []

    def run_validations_for_module(self, session: ReconSession, module_key: str) -> List[ReconException]:
        """Run validation only for a single module."""
        adapter = next((a for a in self.adapters if a.module_key == module_key), None)
        if not adapter:
            raise KeyError(module_key)
        try:
            return adapter.validate(session)
        except Exception as e:
            logger.exception('Validation failed for %s: %s', module_key, e)
            return [ReconException(module_key=module_key, description=f'Validation error: {e}', severity='error')]


    def get_available_modules(self) -> List[str]:
        """Return list of available module keys."""
        return [a.module_key for a in self.adapters]


# Global orchestrator instance
orchestrator = ReconOrchestrator()