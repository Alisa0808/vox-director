"""Offline boundary regressions: fake credentials/media only, no provider traffic.

Run with: python3 -m unittest discover -s tests -v
"""
import ast
from contextlib import contextmanager
import importlib
import io
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import atlas_cloud
import provider

# Image rendering is outside these boundary tests; do not require Pillow to run them.
if importlib.util.find_spec("PIL") is None:
    pil = types.ModuleType("PIL")
    for name in ("Image", "ImageDraw", "ImageFont", "ImageFilter"):
        setattr(pil, name, types.ModuleType(name))
    sys.modules["PIL"] = pil

STAGES = ("keyframes", "clips", "audio", "aroll_clips", "host_clips",
          "host_plates", "croll_keyframes", "assemble", "aroll_assemble",
          "kenburns", "mg_scrapbook", "style_bakeoff")


class NetworkBoundaries(unittest.TestCase):
    def test_upload_auth_is_stdin_config_not_process_arguments(self):
        sentinel = 'offline-quote"back\\slash'
        with patch.dict("os.environ", {"ATLASCLOUD_API_KEY": sentinel}), \
             patch.object(atlas_cloud.subprocess, "run", return_value=types.SimpleNamespace(
                 stdout='{"data":{"url":"https://static.atlascloud.ai/sample.png"}}')) as run:
            atlas_cloud.upload("ordinary image.png")
        args, kw = run.call_args
        self.assertNotIn(sentinel, " ".join(args[0]))
        self.assertEqual(args[0][1], "-q")  # ignore user curlrc before any option
        self.assertIn("--config", args[0])
        self.assertIn("-", args[0])
        self.assertIn('header = "Authorization: Bearer offline-quote\\"back\\\\slash"', kw["input"])
        self.assertNotIn("-L", args[0])
        self.assertIn("--fail", args[0])

    def test_upload_preserves_special_filename_as_one_attachment(self):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        import threading
        received = []

        class Receiver(BaseHTTPRequestHandler):
            def do_POST(self):
                received.append(self.rfile.read(int(self.headers['Content-Length'])))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"data":{"url":"https://static.atlascloud.ai/sample.png"}}')

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), Receiver)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        real_run = subprocess.run

        def local_transport(args, **kwargs):
            args = list(args)
            args[args.index('--url') + 1] = f'http://127.0.0.1:{server.server_port}/'
            args[args.index('--proto') + 1] = '=http'
            args[1:1] = ['--noproxy', '*']
            return real_run(args, **kwargs)

        try:
            with tempfile.TemporaryDirectory() as td:
                for filename in ('plain.png', 'with,comma.png', 'with;semi.png', 'with"quote.png', 'with\\slash.png'):
                    path = Path(td, filename)
                    path.write_bytes(b'offline-upload-sentinel')
                    with self.subTest(filename=filename), \
                         patch.dict('os.environ', {'ATLASCLOUD_API_KEY': 'offline-sentinel'}), \
                         patch.object(atlas_cloud.subprocess, 'run', side_effect=local_transport):
                        atlas_cloud.upload(str(path))
                        self.assertEqual(received[-1].count(b'offline-upload-sentinel'), 1)
                        self.assertEqual(received[-1].count(b'Content-Disposition:'), 1)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_header_controls_rejected_before_subprocess(self):
        with patch.dict("os.environ", {"ATLASCLOUD_API_KEY": "offline\nsentinel"}), \
             patch.object(atlas_cloud.subprocess, "run", return_value=types.SimpleNamespace(
                 stdout='{"data":{"url":"https://static.atlascloud.ai/sample.png"}}')) as run:
            with self.assertRaises((ValueError, atlas_cloud.AtlasCloudError)):
                atlas_cloud.upload("image.png")
            run.assert_not_called()

    def test_download_rejects_untrusted_urls_without_subprocess(self):
        urls = ["http://static.atlascloud.ai/a.png", "file:///sample.png",
                "--offline-option", "https://unrelated.example/a.png",
                "https://api.atlascloud.ai.unrelated.example/a.png",
                "https://user@static.atlascloud.ai/a.png",
                "https://static.atlascloud.ai:8443/a.png", "https://127.0.0.1/a.png",
                "https://static.atlascloud.ai/a\nb.png"]
        for url in urls:
            with self.subTest(url=url), patch.object(atlas_cloud.subprocess, "run") as run:
                with self.assertRaises((ValueError, atlas_cloud.AtlasCloudError)):
                    atlas_cloud.download(url, "unused")
                run.assert_not_called()

    def test_documented_media_hosts_download_and_http_errors_propagate(self):
        hosts = {"static.atlascloud.ai", "api.atlascloud.ai"}
        from urllib.parse import urlsplit
        for example in (ROOT / "examples").glob("*.json"):
            def collect(value):
                if isinstance(value, dict):
                    for v in value.values(): collect(v)
                elif isinstance(value, list):
                    for v in value: collect(v)
                elif isinstance(value, str) and value.startswith("https://"):
                    hosts.add(urlsplit(value).hostname)
            collect(json.loads(example.read_text()))
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "ordinary image.png"
            dest.write_bytes(b"offline-media")
            for host in hosts:
                with self.subTest(host=host), patch.object(atlas_cloud.subprocess, "run") as run:
                    self.assertEqual(atlas_cloud.download(f"https://{host}/media.png", str(dest)), str(dest))
                    args = run.call_args.args[0]
                    self.assertIn("--fail", args)
                    self.assertIn("--proto", args)
                    self.assertIn("--url", args)
                    self.assertNotIn("-L", args)
            with patch.object(atlas_cloud.subprocess, "run", side_effect=subprocess.CalledProcessError(22, "curl")):
                with self.assertRaises(subprocess.CalledProcessError):
                    atlas_cloud.download("https://static.atlascloud.ai/missing.png", str(dest))

    def test_credentialed_requests_reject_untrusted_base_before_transport(self):
        with patch.dict("os.environ", {"ATLASCLOUD_API_KEY": "offline-sentinel"}), \
             patch.object(urllib.request.OpenerDirector, "open") as transport, \
             patch.object(urllib.request, "urlopen", side_effect=lambda *a, **k: io.BytesIO(b'{}')) as legacy:
            for method, args in ((atlas_cloud._get, ("/models",)),
                                 (atlas_cloud._post, ("/models", {}))):
                with self.subTest(method=method.__name__):
                    with self.assertRaises((ValueError, atlas_cloud.AtlasCloudError)):
                        method(*args, base="https://unrelated.example")
            transport.assert_not_called()
            legacy.assert_not_called()

    def test_authenticated_redirect_is_not_followed(self):
        request = urllib.request.Request("https://api.atlascloud.ai/api/v1/models",
                                         headers={"Authorization": "Bearer offline-sentinel"})
        # Exercise installed redirect policy directly without sockets.
        opener = getattr(atlas_cloud, "_OPENER", urllib.request.build_opener())
        handler = next(h for h in opener.handlers if isinstance(h, urllib.request.HTTPRedirectHandler))
        try:
            redirected = handler.redirect_request(request, io.BytesIO(), 302, "Found", {},
                                                  "https://unrelated.example/redirect")
        except (urllib.error.HTTPError, atlas_cloud.AtlasCloudError):
            redirected = None
        self.assertIsNone(redirected)


class RetryBoundaries(unittest.TestCase):
    def test_failed_job_is_not_resubmitted_by_default(self):
        submissions = []
        prov = types.SimpleNamespace(get_status=lambda _: {"status": "failed", "error": "offline failure"})
        with patch.object(provider.time, "sleep"):
            result = provider.run_jobs(prov, {"a": lambda: submissions.append(1) or "job"})
        self.assertEqual(submissions, [1])
        self.assertEqual(result, {"a": None})

    def test_stalled_job_keeps_polling_same_id_without_resubmission(self):
        submissions, polled = [], []
        def status(pid):
            polled.append(pid)
            if len(polled) > 1:
                return {"status": "completed", "output": "offline-result"}
            return {"status": "pending"}
        clock = iter(range(100))
        with patch.object(provider.time, "sleep"), patch.object(provider.time, "time", side_effect=clock):
            result = provider.run_jobs(types.SimpleNamespace(get_status=status),
                                       {"a": lambda: submissions.append(1) or "original"}, stall_s=0)
        self.assertEqual(submissions, [1])
        self.assertEqual(polled, ["original", "original"])
        self.assertEqual(result, {"a": "offline-result"})

    def test_explicit_retry_budget_is_honored(self):
        submissions = []
        prov = types.SimpleNamespace(get_status=lambda _: {"status": "failed"})
        with patch.object(provider.time, "sleep"):
            provider.run_jobs(prov, {"a": lambda: submissions.append(1) or "job"}, max_retries=1)
        self.assertEqual(len(submissions), 2)

    def test_stages_do_not_embed_paid_retry_budgets(self):
        for path in (ROOT / "scripts").glob("*.py"):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "run_jobs":
                    kw = next((k.value for k in node.keywords if k.arg == "max_retries"), None)
                    with self.subTest(script=path.name, line=node.lineno):
                        self.assertFalse(isinstance(kw, ast.Constant) and bool(kw.value),
                                         "stage silently opts into billable retries")

    def test_aroll_failure_does_not_automatically_submit_fallback(self):
        module = importlib.import_module("aroll_clips")
        with tempfile.TemporaryDirectory() as td:
            doc = {"mode": "aroll", "source_video": "unused", "aspect": "9:16",
                   "beats": [{"id": "1", "start": 0, "end": 1, "dur": 1}]}
            Path(td, "beats.json").write_text(json.dumps(doc))
            prov = types.SimpleNamespace(upload=lambda _: "https://static.atlascloud.ai/sample.mp4")
            with patch.object(module, "get_provider", return_value=prov), \
                 patch.object(module, "cut_segment"), \
                 patch.object(module, "run_jobs", return_value={"1": None}) as jobs:
                module.run(td)
            self.assertEqual(jobs.call_count, 1)


class PathBoundaries(unittest.TestCase):
    @contextmanager
    def rejects_input(self, message):
        try:
            yield
        except ValueError as error:
            self.assertRegex(str(error), message)
        except (Exception, SystemExit) as error:
            self.fail(f"stage did work before validation: {type(error).__name__}")
        else:
            self.fail("unsafe input was not rejected")

    def test_all_stages_reject_path_ids_before_provider_or_media_work(self):
        for name in STAGES:
            module = importlib.import_module(name)
            with self.subTest(stage=name), tempfile.TemporaryDirectory() as td:
                # Intentionally minimal doc: identifiers must be checked before stage work.
                Path(td, "beats.json").write_text(json.dumps({"beats": [{"id": "../outside"}]}))
                with patch.object(module, "get_provider", create=True) as prov, \
                     patch.object(module.subprocess if hasattr(module, "subprocess") else subprocess, "run") as media:
                    with self.rejects_input("identifier|component"):
                        module.run(td)
                    prov.assert_not_called()
                    media.assert_not_called()
                self.assertEqual(sorted(p.name for p in Path(td).iterdir()), ["beats.json"])

    def test_style_names_and_element_names_validated_before_work(self):
        style = importlib.import_module("style_bakeoff")
        elements = importlib.import_module("extract_elements")
        with tempfile.TemporaryDirectory() as td:
            Path(td, "beats.json").write_text(json.dumps({"beats": []}))
            with self.rejects_input("identifier|component"):
                style.run(td, ["../outside"])
            Path(td, "elements_spec.json").write_text(json.dumps({"card": "unused", "elements": [{"name": "../outside"}]}))
            with self.rejects_input("identifier|component"):
                elements.run(td)

    def test_output_symlink_is_rejected_before_provider(self):
        module = importlib.import_module("keyframes")
        for leaf in (False, True):
            with self.subTest(leaf=leaf), tempfile.TemporaryDirectory() as td:
                root = Path(td) / "project"
                root.mkdir()
                outside = Path(td) / "outside"
                outside.mkdir()
                Path(root, "beats.json").write_text(json.dumps({"beats": [{"id": "1"}]}))
                if leaf:
                    Path(root, "keyframes").mkdir()
                    Path(root, "keyframes", "kf_1.jpg").symlink_to(outside / "file.jpg")
                else:
                    Path(root, "keyframes").symlink_to(outside, target_is_directory=True)
                with patch.object(module, "get_provider") as prov:
                    with self.rejects_input("outside|escape"):
                        module.run(str(root))
                    prov.assert_not_called()

    def test_nested_in_root_symlink_cannot_hide_an_escaped_output(self):
        from safety import validate_project
        with tempfile.TemporaryDirectory() as td:
            root = Path(td, "project")
            root.mkdir()
            shared = root / "shared"
            shared.mkdir()
            outside = Path(td, "outside")
            outside.mkdir()
            (shared / "kf_1.jpg").symlink_to(outside / "sample.jpg")
            (root / "keyframes").symlink_to(shared, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "outside|escape"):
                validate_project(root, {"beats": [{"id": 1}]})

    def test_valid_ids_and_examples_remain_supported(self):
        from safety import component, validate_project, concat_entry
        for value in (1, "beat-01", "ordinary space", "editor's choice"):
            self.assertEqual(component(value), str(value))
        for value in ("plain\\label", "../outside", "/outside", "", ".", ".."):
            with self.assertRaises(ValueError):
                component(value)
        with tempfile.TemporaryDirectory() as td:
            for example in (ROOT / "examples").glob("*.json"):
                validate_project(td, json.loads(example.read_text()))
        with self.assertRaises(ValueError):
            concat_entry("ordinary\nlabel.mp4")

    def test_keyframe_stage_preserves_quote_and_space_ids_and_explicit_retry_budget(self):
        module = importlib.import_module("keyframes")
        for budget in (0, 1):
            with self.subTest(budget=budget), tempfile.TemporaryDirectory() as td:
                doc = {"style": "collage", "job_retries": budget,
                       "beats": [{"id": "editor's choice", "scene": "plain card",
                                  "title_cn": "", "title_en": "Offline"}]}
                Path(td, "beats.json").write_text(json.dumps(doc))
                def jobs(prov, specs, **kw):
                    self.assertEqual(kw["max_retries"], budget)
                    return {key: "https://static.atlascloud.ai/sample.jpg" for key in specs}
                def download(url, dest):
                    Path(dest).write_bytes(b"offline-media")
                prov = types.SimpleNamespace(download=download)
                with patch.object(module, "get_provider", return_value=prov), patch.object(module, "run_jobs", side_effect=jobs):
                    module.run(td)
                dest = Path(td, "keyframes", "kf_editor's choice.jpg")
                self.assertEqual(dest.read_bytes(), b"offline-media")
                saved = json.loads(Path(td, "beats.json").read_text())
                self.assertEqual(saved["beats"][0]["keyframe_path"], str(dest))

    def test_both_assemblers_quote_concat_filenames(self):
        for name in ("assemble", "aroll_assemble"):
            module = importlib.import_module(name)
            with self.subTest(stage=name), tempfile.TemporaryDirectory(prefix="vox quote ' ") as td:
                clip = Path(td) / "input.mp4"
                clip.write_bytes(b"offline")
                beat = {"id": "1", "start": 0, "dur": 1, "clip_path": str(clip),
                        "narration_audio": "unused", "narration": "offline"}
                doc = {"source_video": str(clip), "beats": [beat], "bgm_path": "unused", "captions": False}
                Path(td, "beats.json").write_text(json.dumps(doc))
                overlays = types.SimpleNamespace(render_watermark=lambda *a: "unused")
                with patch.object(module, "ff"), patch.object(module, "probe_dur", return_value=1), \
                     patch.object(module, "text_overlay", overlays, create=True):
                    module.run(td)
                filename = "list.txt" if name == "assemble" else "concat_list.txt"
                line = Path(td, "_seg", filename).read_text().strip()
                expected = Path(td, "_seg", "seg_00.mp4" if name == "assemble" else "muxed_1.mp4")
                try:
                    tokens = shlex.split(line)
                except ValueError:
                    self.fail("assembler wrote an unquoted filename in ffconcat")
                self.assertEqual(tokens, ["file", str(expected)])


if __name__ == "__main__":
    unittest.main()
