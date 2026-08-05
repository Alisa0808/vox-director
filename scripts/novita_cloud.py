#!/usr/bin/env python3
"""
Novita AI API client for vox-director.

Thin, dependency-free wrapper around Novita's `/v3` API: the async task_id ->
poll pattern shared by txt2img/img2video/txt2speech, plus the synchronous
remove-background call.

Two gaps, left honest rather than guessed at:
  - submit_video talks to the generic /async/img2video model family (image-in,
    motion-out, no text prompt) -- Novita's prompt-steered flagship video models
    (the Kling/Seedance/Gemini-video equivalents this pipeline prefers for
    real-person content) live behind their own per-model endpoints, not this
    generic one, and aren't wired up here.
  - submit_audio only covers narration (txt2speech). Novita's text-to-music
    (MiniMax Music series) uses a different, not-yet-verified request shape,
    so a music call raises clearly instead of guessing at fields.

Env: NOVITA_API_KEY must be set.
"""
import base64
import json
import mimetypes
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://api.novita.ai/v3"


class NovitaError(RuntimeError):
    pass


def _key() -> str:
    k = os.environ.get("NOVITA_API_KEY")
    if not k:
        raise NovitaError("NOVITA_API_KEY is not set. Get one at "
                           "https://novita.ai/settings/key-management")
    return k


def _post(path: str, payload: dict, timeout: int = 60) -> dict:
    req = urllib.request.Request(
        BASE + path, data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {_key()}", "Content-Type": "application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise NovitaError(f"POST {path} -> {e.code}: {e.read().decode()[:400]}") from e


def _get(path: str, params: dict, timeout: int = 60, retries: int = 3) -> dict:
    url = f"{BASE}{path}?{urllib.parse.urlencode(params)}"
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {_key()}"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            # A failed task can come back as a non-2xx whose body is still the
            # normal task envelope (status: TASK_STATUS_FAILED) -- parse it like
            # any other response rather than collapsing it to a bare HTTP error.
            body = e.read().decode(errors="replace")
            try:
                return json.loads(body)
            except ValueError:
                last = NovitaError(f"GET {path} -> {e.code}: {body[:400]}")
                break
        except (urllib.error.URLError, TimeoutError) as e:  # transient
            last = e
            time.sleep(2 ** i)
    raise NovitaError(f"GET {path} failed after {retries} tries: {last}")


def _to_data_uri(image: str) -> str:
    """Accept a data: URI, an http(s) URL, or a local path; return a data: URI.
    Novita's image inputs (remove-background, img2video) take base64 inline --
    there's no separate "host it, get a URL back" step to round-trip through."""
    if image.startswith("data:"):
        return image
    if image.startswith("http://") or image.startswith("https://"):
        req = urllib.request.Request(image, headers={"User-Agent": "vox-director/0.1"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
        mime = r.headers.get_content_type() or "application/octet-stream"
    else:
        with open(image, "rb") as f:
            data = f.read()
        mime = mimetypes.guess_type(image)[0] or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


def _b64_of(data_uri: str) -> str:
    return data_uri.split(",", 1)[1]


# ---------------------------------------------------------------- generation

def submit_image(model: str, prompt: str, **params) -> str:
    """Submit a text-to-image task; return task_id."""
    body = {"model_name": model, "prompt": prompt, **params}
    return _post("/async/txt2img", body)["task_id"]


def submit_video(model: str, prompt: str, **params) -> str:
    """Submit an image-to-video task; return task_id.

    `prompt` is accepted for Provider interface parity but not sent -- the
    generic img2video model family is image-driven motion only. `image`
    (URL/path/data-URI, typically from Provider.upload()) is required."""
    image = params.pop("image", None)
    if not image:
        raise NovitaError("submit_video requires image=<url, path, or data URI>")
    body = {"model_name": model, "image_file": _b64_of(_to_data_uri(image)), **params}
    return _post("/async/img2video", body)["task_id"]


def submit_audio(model: str, **params) -> str:
    """Submit a narration (text-to-speech) task; return task_id. `model` is
    unused -- Novita's generic txt2speech endpoint is a single engine selected
    by `voice_id`, not a model catalog, so the voice comes from **params."""
    text = params.pop("text", None)
    if text is None:
        raise NovitaError("submit_audio only supports narration (text=...); "
                           "Novita's music-generation endpoint isn't wired up here")
    body = {"request": {"texts": [text], **params}}
    return _post("/async/txt2speech", body)["task_id"]


_SYNC_RESULTS = {}


def remove_bg(image: str, **params) -> str:
    """remove-background is synchronous, unlike every other call here -- wrap its
    result behind a synthetic job id so callers can still poll get_status()."""
    body = {"image_file": _b64_of(_to_data_uri(image)), **params}
    resp = _post("/remove-background", body)
    job_id = f"sync:{len(_SYNC_RESULTS)}:{time.time()}"
    _SYNC_RESULTS[job_id] = resp
    return job_id


def get_status(job_id: str) -> dict:
    """Normalize a task's status to {status, output, error}. `output` is a URL,
    except for the synchronous remove-background path, where it's the decoded
    data: URI directly (Novita hands that call's image back inline, not via a
    CDN link)."""
    if job_id.startswith("sync:"):
        resp = _SYNC_RESULTS.pop(job_id, None)
        if resp is None:
            return {"status": "failed", "output": None, "error": "sync result already consumed"}
        mime = f"image/{resp.get('image_type', 'png')}"
        return {"status": "completed",
                "output": f"data:{mime};base64,{resp['image_file']}", "error": None}
    d = _get("/async/task-result", {"task_id": job_id})
    task = d.get("task", {})
    status = task.get("status")
    if status == "TASK_STATUS_SUCCEED":
        out = (d.get("images") or []) + (d.get("videos") or []) + (d.get("audios") or [])
        url = None
        if out:
            first = out[0]
            url = first.get("image_url") or first.get("video_url") or first.get("audio_url")
        return {"status": "completed", "output": url, "error": None}
    if status == "TASK_STATUS_FAILED":
        return {"status": "failed", "output": None, "error": task.get("reason", "")}
    return {"status": "pending", "output": None, "error": None}


# ---------------------------------------------------------------- upload / dl

def upload(file_path: str) -> str:
    """Return a data: URI for the local file. Novita's generation calls take
    base64 inline, so "uploading" is just reading the file -- no hosting step
    (and thus no separate public URL) is needed before a generation call."""
    return _to_data_uri(file_path)


def download(url: str, dest: str) -> str:
    """Save a generated asset to `dest`. Handles both real https:// CDN URLs
    (images/videos/audio from task-result) and the data: URIs this module
    itself hands back from upload()/remove_bg()."""
    if url.startswith("data:"):
        with open(dest, "wb") as f:
            f.write(base64.b64decode(_b64_of(url)))
    else:
        subprocess.run(["/usr/bin/curl", "-s", "--retry", "3", "-o", dest, url], check=True)
    if not os.path.exists(dest) or os.path.getsize(dest) == 0:
        raise NovitaError(f"download produced empty file: {url}")
    return dest


if __name__ == "__main__":
    # smoke test: confirm the key is set and a minimal txt2img round-trips
    import sys
    print("key:", "set" if os.environ.get("NOVITA_API_KEY") else "MISSING")
    if "--ping" in sys.argv:
        tid = submit_image("google/nano-banana", "a tiny red seal stamp on white paper")
        print("submitted:", tid)
