"""Pagination utilities for report display."""

from typing import List, Dict, Any, Tuple
import math


class ReportPaginator:
    """Handles pagination for report data display."""

    def __init__(self, items_per_page: int = 50):
        self.items_per_page = items_per_page
        self.current_page = 1
        self.total_items = 0

    def set_data(self, data: List[Dict[str, Any]]) -> None:
        """Set the data to paginate."""
        self.total_items = len(data)
        self.current_page = 1

    def get_page(self, data: List[Dict[str, Any]], page: int = None) -> List[Dict[str, Any]]:
        """Get items for the specified page."""
        if page is not None:
            self.current_page = page

        start_idx = (self.current_page - 1) * self.items_per_page
        end_idx = start_idx + self.items_per_page

        return data[start_idx:end_idx]

    def get_page_info(self) -> Dict[str, Any]:
        """Get pagination information."""
        total_pages = math.ceil(self.total_items / self.items_per_page) if self.total_items > 0 else 1

        return {
            'current_page': self.current_page,
            'total_pages': total_pages,
            'total_items': self.total_items,
            'items_per_page': self.items_per_page,
            'has_next': self.current_page < total_pages,
            'has_prev': self.current_page > 1,
            'start_item': ((self.current_page - 1) * self.items_per_page) + 1,
            'end_item': min(self.current_page * self.items_per_page, self.total_items)
        }

    def next_page(self) -> bool:
        """Go to next page. Returns True if successful."""
        total_pages = math.ceil(self.total_items / self.items_per_page) if self.total_items > 0 else 1
        if self.current_page < total_pages:
            self.current_page += 1
            return True
        return False

    def prev_page(self) -> bool:
        """Go to previous page. Returns True if successful."""
        if self.current_page > 1:
            self.current_page -= 1
            return True
        return False

    def go_to_page(self, page: int) -> bool:
        """Go to specific page. Returns True if successful."""
        total_pages = math.ceil(self.total_items / self.items_per_page) if self.total_items > 0 else 1
        if 1 <= page <= total_pages:
            self.current_page = page
            return True
        return False