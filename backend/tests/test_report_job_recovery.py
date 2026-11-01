"""A job whose lease is held by a dead worker must be retried, never left stuck."""
from __future__ import annotations

from unittest.mock import patch

from app.services import report_job_service as jobs


def test_failed_claim_schedules_a_retry_that_requeues_unfinished_job() -> None:
    service = jobs.ReportJobService.__new__(jobs.ReportJobService)
    service._jobs = {"rpt_x": {"report_id": "rpt_x", "status": "queued"}}
    service._lock = jobs.threading.RLock()
    service._queue = jobs.queue.Queue()
    timers = []

    class FakeTimer:
        def __init__(self, delay, fn):
            self.delay, self.fn, self.daemon = delay, fn, False
            timers.append(self)

        def start(self):
            pass

    with patch.object(service, "_claim_job", return_value=False), patch.object(jobs.threading, "Timer", FakeTimer), \
            patch.object(service, "_load_stored", return_value=None):
        service.run("rpt_x")
        assert timers and timers[0].delay == jobs.CLAIM_RETRY_SECONDS
        timers[0].fn()
    assert service._queue.get_nowait() == "rpt_x"


def test_retry_does_not_rerun_a_job_another_worker_finished() -> None:
    service = jobs.ReportJobService.__new__(jobs.ReportJobService)
    service._jobs = {"rpt_y": {"report_id": "rpt_y", "status": "queued"}}
    service._lock = jobs.threading.RLock()
    service._queue = jobs.queue.Queue()
    timers = []

    class FakeTimer:
        def __init__(self, delay, fn):
            self.fn, self.daemon = fn, False
            timers.append(self)

        def start(self):
            pass

    with patch.object(service, "_claim_job", return_value=False), patch.object(jobs.threading, "Timer", FakeTimer), \
            patch.object(service, "_load_stored", return_value={"report_id": "rpt_y", "status": "completed"}):
        service.run("rpt_y")
        timers[0].fn()
    assert service._queue.empty()
    assert service._jobs["rpt_y"]["status"] == "completed"
