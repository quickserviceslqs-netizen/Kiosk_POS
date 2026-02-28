"""Overview report generator for dashboard metrics."""

from typing import Dict, List, Any
import logging
from datetime import datetime, timedelta

from .reports_base import ReportGenerator, ReportData
from modules import reports

logger = logging.getLogger(__name__)


class OverviewGenerator(ReportGenerator):
    """Generator for overview dashboard metrics."""

    def generate_data(self) -> ReportData:
        """Generate overview metrics data."""
        today = datetime.now().strftime("%Y-%m-%d")

        try:
            # Today's revenue
            today_data = reports.get_daily_sales(today)
            today_revenue = sum(item['total'] for item in today_data) if today_data else 0
            today_transactions = len(set(item['receipt_number'] for item in today_data)) if today_data else 0

            # This week's revenue
            week_start = (datetime.now() - timedelta(days=datetime.now().weekday())).strftime("%Y-%m-%d")
            week_end = (datetime.now() + timedelta(days=6-datetime.now().weekday())).strftime("%Y-%m-%d")
            week_data = reports.get_date_range_sales(week_start, week_end)
            week_revenue = sum(item.get('total_sales', 0) for item in week_data) if week_data else 0

            # Calculate growth rate
            last_week_start = (datetime.now() - timedelta(days=datetime.now().weekday() + 7)).strftime("%Y-%m-%d")
            last_week_end = (datetime.now() - timedelta(days=datetime.now().weekday() + 1)).strftime("%Y-%m-%d")
            last_week_data = reports.get_date_range_sales(last_week_start, last_week_end)
            last_week_revenue = sum(item.get('total_sales', 0) for item in last_week_data) if last_week_data else 0

            growth_rate = 0.0
            if last_week_revenue > 0:
                growth_rate = ((week_revenue - last_week_revenue) / last_week_revenue) * 100
            elif week_revenue > 0:
                growth_rate = 100.0

            metadata = {
                'today_revenue': today_revenue,
                'today_transactions': today_transactions,
                'week_revenue': week_revenue,
                'growth_rate': growth_rate
            }

        except Exception as e:
            logger.error(f"Error generating overview data: {e}")
            metadata = {
                'today_revenue': 0,
                'today_transactions': 0,
                'week_revenue': 0,
                'growth_rate': 0.0,
                'error': str(e)
            }

        return ReportData('overview', self.start_date, self.end_date, [], metadata)

    def get_formatter(self, report_data: ReportData):
        """Overview doesn't need a traditional formatter."""
        return None