"""Report controller for managing report generation and coordination."""

from typing import Dict, List, Any, Optional, Callable, Tuple
import logging
import threading
import time
from queue import Queue

from .reports_base import ReportGenerator, ReportData, ReportError
from .reports_constants import THREAD_TIMEOUT

# legacy imports kept for backward compatibility (currently unused)
# NOTE: these can be removed once all consumers rely solely on the
# module-level registry in modules/reports.

# registry from the modules package
from modules import reports as modules_reports

logger = logging.getLogger(__name__)


class ReportController:
    """Controller for managing report generation and coordination."""

    def __init__(self):
        # mapping report_type -> callable
        self.generators: Dict[str, Callable] = {}
        self._load_generators()

        self.active_threads: Dict[str, threading.Thread] = {}
        self.result_queue = Queue()
        self.callbacks: Dict[str, Callable] = {}

        # simple in-memory TTL cache for ReportData objects
        self._cache: Dict[Tuple, Tuple[ReportData, float]] = {}

    def _cache_key(self, report_type: str, start_date: str, end_date: str, status_filter: str, **kwargs) -> Tuple:
        """Construct a hashable key for caching based on parameters."""
        # sort kwargs to make key order-independent
        items = tuple(sorted(kwargs.items()))
        return (report_type, start_date, end_date, status_filter, items)

    def generate_report_page(self, report_type: str, start_date: str, end_date: str,
                             page_size: int = 100, cursor: str | None = None,
                             status_filter: str = "all", **kwargs) -> tuple:
        """Return a page of rows along with next cursor and metadata.

        This method will use the cache if available; otherwise it will
        compute the full report once and slice in-memory.  For generators
        that support efficient paging (by accepting limit/offset), the
        caller can override by registering a custom function that handles
        those arguments directly.
        """
        rd = self.generate_report_sync(report_type, start_date, end_date, status_filter, **kwargs)
        data = rd.data or []
        offset = int(cursor) if cursor else 0
        rows = data[offset:offset + page_size]
        next_cursor = str(offset + len(rows)) if offset + len(rows) < len(data) else None
        metadata = {**rd.metadata, 'total_items': len(data)}
        return rows, next_cursor, metadata

    def _load_generators(self) -> None:
        """Populate self.generators from module registry.

        Legacy hardcoded generators are no longer required once the
        registry in `modules.reports` covers all types; keep additional
        fallback logic here only in case a key is missing at runtime.
        """
        # copy everything from the module-level registry
        for key, fn in modules_reports.REPORT_GENERATORS.items():
            self.generators[key] = fn

        # no legacy fallback required; registry in modules.reports
        # already contains all known generators
        pass

    def register_generator(self, key: str, fn: Callable) -> None:
        """Register a new report generator function under *key*.  Used by
        plugin code or initialization routines.

        The function should accept at least (start_date, end_date) and may
        accept additional kwargs.  It may return a ReportData instance or
        raw data (list/dict) which will be wrapped automatically.
        """
        self.generators[key] = fn

    def invalidate_cache(self, report_type: Optional[str] = None) -> None:
        """Clear cache for all reports or a specific report type."""
        if report_type is None:
            self._cache.clear()
        else:
            keys = [k for k in self._cache if k[0] == report_type]
            for k in keys:
                del self._cache[k]


    def generate_report_async(self, report_type: str, start_date: str, end_date: str,
                            callback: Callable[[ReportData], None] | None = None,
                            status_filter: str = "all", **kwargs) -> str:
        """Generate a report asynchronously."""
        request_id = f"{report_type}_{int(time.time() * 1000)}"

        def worker():
            try:
                # check cache
                key = self._cache_key(report_type, start_date, end_date, status_filter, **kwargs)
                if key in self._cache:
                    data, ts = self._cache[key]
                    if time.time() - ts < THREAD_TIMEOUT:
                        result = data
                    else:
                        del self._cache[key]
                        result = self._run_generator(report_type, start_date, end_date, status_filter, **kwargs)
                else:
                    result = self._run_generator(report_type, start_date, end_date, status_filter, **kwargs)
                # cache it
                self._cache[key] = (result, time.time())

                self.result_queue.put((request_id, result))
                if callback:
                    callback(result)
            except Exception as e:
                logger.exception(f"Error generating report {request_id}: {e}")
                error_result = ReportData(report_type, start_date, end_date, [],
                                        {'error': str(e)})
                self.result_queue.put((request_id, error_result))
                if callback:
                    callback(error_result)
            finally:
                if request_id in self.active_threads:
                    del self.active_threads[request_id]

        thread = threading.Thread(target=worker, daemon=True)
        self.active_threads[request_id] = thread
        thread.start()

        return request_id

    def generate_report_sync(self, report_type: str, start_date: str, end_date: str,
                           status_filter: str = "all", **kwargs) -> ReportData:
        """Generate a report synchronously (with caching)."""
        try:
            key = self._cache_key(report_type, start_date, end_date, status_filter, **kwargs)
            if key in self._cache:
                data, ts = self._cache[key]
                if time.time() - ts < THREAD_TIMEOUT:
                    return data
                else:
                    del self._cache[key]
            result = self._run_generator(report_type, start_date, end_date, status_filter, **kwargs)
            self._cache[key] = (result, time.time())
            return result
        except Exception as e:
            logger.error(f"Error generating report synchronously: {e}")
            return ReportData(report_type, start_date, end_date, [],
                            {'error': str(e)})

    def _run_generator(self, report_type: str, start_date: str, end_date: str,
                       status_filter: str = "all", **kwargs) -> ReportData:
        """Invoke the registered generator function and normalize result to
        ReportData.
        """
        if report_type not in self.generators:
            return ReportData(report_type, start_date, end_date, [],
                              {'error': f'Unknown report type: {report_type}'})

        fn = self.generators[report_type]
        # inspect signature to call with appropriate args
        try:
            import inspect
            sig = inspect.signature(fn)
            params = list(sig.parameters.keys())
        except Exception:
            params = []

        # build argument list depending on what the generator expects
        call_args: list = []
        call_kwargs: dict = {}

        if params:
            # common patterns:
            # - date only (daily)
            # - start_date, end_date
            # - start_date, end_date, status
            # - start_date, end_date, limit, offset
            # use positionally where possible
            if len(params) == 1:
                call_args = [start_date]
            elif len(params) == 2:
                call_args = [start_date, end_date]
            else:
                # first two always dates
                call_args = [start_date, end_date]
                # if 'status' in params and status_filter is provided
                if 'status' in params:
                    call_args.append(status_filter)
                # any remaining kwargs pass through
                for name in params[3:]:
                    if name in kwargs:
                        call_args.append(kwargs[name])
        else:
            # fallback to two-arg call
            call_args = [start_date, end_date]

        # merge any extra kwargs not consumed
        remaining = {k: v for k, v in kwargs.items() if k not in sig.parameters}
        call_kwargs.update(remaining)

        result = fn(*call_args, **call_kwargs)
        if isinstance(result, ReportData):
            return result
        elif isinstance(result, dict):
            return ReportData(report_type, start_date, end_date, [], result)
        elif isinstance(result, list):
            return ReportData(report_type, start_date, end_date, result, **kwargs)
        else:
            # unexpected return
            return ReportData(report_type, start_date, end_date, [], {'result': result})

    def cancel_report(self, request_id: str) -> bool:
        """Cancel an active report generation."""
        if request_id in self.active_threads:
            # Note: In Python, we can't actually stop a thread, but we can mark it for cleanup
            thread = self.active_threads[request_id]
            # The thread will clean itself up when done
            return True
        return False

    def get_active_reports(self) -> List[str]:
        """Get list of active report request IDs."""
        return list(self.active_threads.keys())

    def is_report_active(self, request_id: str) -> bool:
        """Check if a report is currently being generated."""
        return request_id in self.active_threads

    def wait_for_report(self, request_id: str, timeout: float = THREAD_TIMEOUT) -> Optional[ReportData]:
        """Wait for a report to complete and return the result."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not self.is_report_active(request_id):
                # Check queue for result
                try:
                    while True:
                        req_id, result = self.result_queue.get_nowait()
                        if req_id == request_id:
                            return result
                except:
                    pass
            time.sleep(0.1)
        return None

    def cleanup_completed_reports(self):
        """Clean up completed report threads and results."""
        # Clean up old results from queue (keep only recent ones)
        temp_queue = Queue()
        recent_results = []

        while not self.result_queue.empty():
            try:
                item = self.result_queue.get_nowait()
                req_id, result = item
                # Keep results that are less than 5 minutes old
                if time.time() - result.generated_at.timestamp() < 300:
                    recent_results.append(item)
            except:
                break

        # Put back recent results
        for item in recent_results:
            temp_queue.put(item)

        self.result_queue = temp_queue