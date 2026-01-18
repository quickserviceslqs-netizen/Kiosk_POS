"""Simple in-process pub/sub for cart change notifications."""
from __future__ import annotations
from typing import Callable

_listeners: list[Callable[[], None]] = []


def subscribe_cart_changed(cb: Callable[[], None]) -> None:
    if cb not in _listeners:
        _listeners.append(cb)


def unsubscribe_cart_changed(cb: Callable[[], None]) -> None:
    try:
        _listeners.remove(cb)
    except ValueError:
        pass


def notify_cart_changed() -> None:
    for cb in list(_listeners):
        try:
            cb()
        except Exception:
            # Swallow exceptions from callbacks
            pass
