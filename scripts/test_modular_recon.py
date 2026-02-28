#!/usr/bin/env python3
"""Test script for the new efficient reconciliation module redesign."""

import sys
import os
# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from modules.reconciliation import orchestrator
from modules.reconciliation.models import ReconSession, ReconEntry
from datetime import datetime

def test_modular_orchestrator():
    """Test the new modular orchestrator."""
    print("Testing modular reconciliation orchestrator...")

    # Create a mock session
    session = ReconSession(
        session_id=1,
        start_date="2024-01-01",
        end_date="2024-01-01",
        created_at=datetime.now(),
        entries=[
            ReconEntry(payment_method="Cash", system_amount=1000.0, actual_amount=950.0),
            ReconEntry(payment_method="Credit Card", system_amount=500.0, actual_amount=520.0),
        ]
    )

    # Get summaries
    summaries = orchestrator.run_all_summaries(session)

    print(f"Available modules: {orchestrator.get_available_modules()}")
    print(f"Generated {len(summaries)} module summaries:")

    total_system = 0.0
    total_actual = 0.0
    total_variance = 0.0

    for summary in summaries:
        print(f"  {summary.module_name}: System={summary.total_system:.2f}, Actual={summary.total_actual:.2f}, Variance={summary.total_variance:.2f}, Status={summary.status}")
        total_system += summary.total_system
        total_actual += summary.total_actual
        total_variance += summary.total_variance

    print(f"Overall: System={total_system:.2f}, Actual={total_actual:.2f}, Variance={total_variance:.2f}")

    # Test validations
    exceptions = orchestrator.run_all_validations(session)
    print(f"Found {len(exceptions)} validation exceptions:")
    for exc in exceptions:
        print(f"  {exc.module_key}: {exc.description} ({exc.severity})")

    print("Modular orchestrator test completed successfully!")

if __name__ == "__main__":
    test_modular_orchestrator()