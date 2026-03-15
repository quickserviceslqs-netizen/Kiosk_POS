#!/usr/bin/env python3
"""
Inventory Change Notification System
Notifies UI components when inventory levels change (stock received, sold, etc.)
"""

from typing import List, Callable, Dict, Any

class InventoryNotificationSystem:
    """Centralized system for inventory change notifications."""
    
    def __init__(self):
        self._subscribers: List[Callable] = []
        
    def subscribe(self, callback: Callable) -> None:
        """Subscribe to inventory change notifications."""
        if callback not in self._subscribers:
            self._subscribers.append(callback)
    
    def unsubscribe(self, callback: Callable) -> None:
        """Unsubscribe from inventory change notifications."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)
    
    def notify_inventory_changed(self, change_type: str, item_id: int, 
                               quantity_change: float, **kwargs) -> None:
        """Notify all subscribers that inventory has changed.
        
        Args:
            change_type: Type of change ('received', 'sold', 'adjusted', 'price_changed', etc.)
            item_id: ID of the item that changed
            quantity_change: Amount of change (positive for increase, negative for decrease)
            **kwargs: Additional context (variant_id, lot_id, etc.)
        """
        print(f"Notifying {len(self._subscribers)} subscribers of inventory change: "
              f"{change_type} for item {item_id}, qty change: {quantity_change}")
        for callback in self._subscribers[:]:  # Use slice to avoid modification during iteration
            try:
                callback(change_type, item_id, quantity_change, **kwargs)
            except Exception as e:
                print(f"Error notifying inventory subscriber: {e}")

# Global notification system
_inventory_notifier = InventoryNotificationSystem()


def subscribe_to_inventory_changes(callback: Callable) -> None:
    """Subscribe a callback to inventory change notifications."""
    _inventory_notifier.subscribe(callback)


def unsubscribe_from_inventory_changes(callback: Callable) -> None:
    """Unsubscribe a callback from inventory change notifications."""
    _inventory_notifier.unsubscribe(callback)


def notify_inventory_changed(change_type: str, item_id: int, 
                           quantity_change: float, **kwargs) -> None:
    """Notify subscribers of an inventory change."""
    _inventory_notifier.notify_inventory_changed(change_type, item_id, quantity_change, **kwargs)