import io
import os
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock, patch


SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts")
sys.path.insert(0, SCRIPTS_DIR)

import provider


class FakeClock:
    def __init__(self):
        self.now = 0

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class RunJobsTest(unittest.TestCase):
    def run_with_clock(self, prov, submit, **kwargs):
        clock = FakeClock()
        output = io.StringIO()
        with patch.object(provider.time, "time", clock.time), patch.object(
            provider.time, "sleep", clock.sleep
        ), redirect_stdout(output):
            result = provider.run_jobs(prov, {"shot": submit}, **kwargs)
        return result, output.getvalue()

    def test_completed_job_is_submitted_once(self):
        prov = Mock()
        prov.get_status.return_value = {
            "status": "completed",
            "output": "https://example.test/output.mp4",
            "error": None,
        }
        submit = Mock(return_value="prediction-1")

        result, _ = self.run_with_clock(
            prov, submit, poll_s=1, stall_s=10, deadline_s=20
        )

        self.assertEqual(result, {"shot": "https://example.test/output.mp4"})
        submit.assert_called_once_with()

    def test_failed_job_is_not_resubmitted(self):
        prov = Mock()
        prov.get_status.return_value = {
            "status": "failed",
            "output": None,
            "error": "policy rejection",
        }
        submit = Mock(return_value="prediction-failed")

        result, output = self.run_with_clock(
            prov, submit, poll_s=1, stall_s=10, deadline_s=20
        )

        self.assertEqual(result, {"shot": None})
        submit.assert_called_once_with()
        self.assertIn("prediction-failed", output)
        self.assertNotIn("resubmit", output.lower())

    def test_stalled_job_is_not_resubmitted(self):
        prov = Mock()
        prov.get_status.return_value = {
            "status": "pending",
            "output": None,
            "error": None,
        }
        submit = Mock(return_value="prediction-stalled")

        result, output = self.run_with_clock(
            prov, submit, poll_s=1, stall_s=0.5, deadline_s=20
        )

        self.assertEqual(result, {"shot": None})
        submit.assert_called_once_with()
        self.assertIn("prediction-stalled", output)
        self.assertIn("not resubmitted", output)

    def test_deadline_does_not_create_a_replacement_task(self):
        prov = Mock()
        prov.get_status.return_value = {
            "status": "pending",
            "output": None,
            "error": None,
        }
        submit = Mock(return_value="prediction-timeout")

        result, output = self.run_with_clock(
            prov, submit, poll_s=1, stall_s=100, deadline_s=2
        )

        self.assertEqual(result, {"shot": None})
        submit.assert_called_once_with()
        self.assertIn("prediction-timeout", output)
        self.assertIn("not resubmitted", output)


if __name__ == "__main__":
    unittest.main()
