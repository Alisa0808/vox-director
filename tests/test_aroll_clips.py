import json
import os
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch


SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts")
sys.path.insert(0, SCRIPTS_DIR)

import aroll_clips


class ArollSubmissionTest(unittest.TestCase):
    def test_failed_primary_job_does_not_submit_a_fallback(self):
        prov = Mock()
        prov.upload.return_value = "https://example.test/source.mp4"
        prov.submit_video.return_value = "prediction-primary"

        def submit_once_then_fail(_prov, specs, **_kwargs):
            for submit in specs.values():
                submit()
            return {key: None for key in specs}

        doc = {
            "mode": "aroll",
            "source_video": "source.mp4",
            "aspect": "9:16",
            "video_model": "google/gemini-omni-flash/video-edit",
            "beats": [
                {
                    "id": 1,
                    "start": 0,
                    "end": 1,
                    "dur": 1,
                    "content_beats": "test beat",
                }
            ],
        }

        with tempfile.TemporaryDirectory() as project_dir:
            with open(os.path.join(project_dir, "beats.json"), "w") as f:
                json.dump(doc, f)
            with patch.object(aroll_clips, "get_provider", return_value=prov), patch.object(
                aroll_clips, "cut_segment"
            ), patch.object(aroll_clips, "run_jobs", side_effect=submit_once_then_fail):
                aroll_clips.run(project_dir)

        prov.submit_video.assert_called_once()
        prov.download.assert_not_called()


if __name__ == "__main__":
    unittest.main()
