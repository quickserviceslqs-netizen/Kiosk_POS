"""Performance monitoring and optimization utilities."""
from __future__ import annotations

import time
import functools
from typing import Any, Callable, Dict, List
from contextlib import contextmanager
import psutil
import os


class PerformanceMonitor:
    """Monitor application performance metrics."""

    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
        self.start_times: Dict[str, float] = {}

    def start_timer(self, name: str) -> None:
        """Start timing an operation."""
        self.start_times[name] = time.time()

    def end_timer(self, name: str) -> float:
        """End timing and return elapsed time."""
        if name not in self.start_times:
            return 0.0

        elapsed = time.time() - self.start_times[name]
        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append(elapsed)
        del self.start_times[name]
        return elapsed

    @contextmanager
    def timer(self, name: str):
        """Context manager for timing operations."""
        self.start_timer(name)
        try:
            yield
        finally:
            self.end_timer(name)

    def get_average_time(self, name: str) -> float:
        """Get average execution time for an operation."""
        times = self.metrics.get(name, [])
        return sum(times) / len(times) if times else 0.0

    def get_total_calls(self, name: str) -> int:
        """Get total number of calls for an operation."""
        return len(self.metrics.get(name, []))

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system performance metrics."""
        try:
            return {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "memory_used_mb": psutil.virtual_memory().used / 1024 / 1024,
                "disk_usage_percent": psutil.disk_usage('/').percent,
                "process_count": len(psutil.pids())
            }
        except Exception:
            return {}

    def reset(self) -> None:
        """Reset all metrics."""
        self.metrics.clear()
        self.start_times.clear()


# Global performance monitor
performance_monitor = PerformanceMonitor()


def profile_function(func: Callable) -> Callable:
    """Decorator to profile function execution time."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        func_name = f"{func.__module__}.{func.__name__}"
        with performance_monitor.timer(func_name):
            return func(*args, **kwargs)
    return wrapper


def get_performance_report() -> Dict[str, Any]:
    """Get a performance report."""
    report = {
        "system": performance_monitor.get_system_metrics(),
        "operations": {}
    }

    for name, times in performance_monitor.metrics.items():
        report["operations"][name] = {
            "average_time": sum(times) / len(times),
            "total_calls": len(times),
            "total_time": sum(times),
            "min_time": min(times),
            "max_time": max(times)
        }

    return report


def optimize_database_query(func: Callable) -> Callable:
    """Decorator to optimize database queries with basic caching."""
    cache = {}

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Simple cache key based on function name and args
        # In production, use a more sophisticated caching strategy
        cache_key = (func.__name__, str(args), str(sorted(kwargs.items())))

        if cache_key in cache:
            return cache[cache_key]

        result = func(*args, **kwargs)
        cache[cache_key] = result
        return result

    return wrapper


def lazy_load_property(func: Callable) -> property:
    """Property decorator for lazy loading expensive operations."""
    attr_name = f"_lazy_{func.__name__}"

    @property
    @functools.wraps(func)
    def lazy_property(self):
        if not hasattr(self, attr_name):
            setattr(self, attr_name, func(self))
        return getattr(self, attr_name)

    return lazy_property


def batch_process(items: List[Any], batch_size: int = 100, processor: Callable = None) -> List[Any]:
    """Process items in batches to improve performance and memory usage.

    Args:
        items: List of items to process
        batch_size: Size of each batch
        processor: Function to process each batch

    Returns:
        List of processed results
    """
    if not processor:
        return items

    results = []
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batch_result = processor(batch)
        if isinstance(batch_result, list):
            results.extend(batch_result)
        else:
            results.append(batch_result)

    return results