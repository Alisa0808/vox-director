#!/usr/bin/env python3
"""
ModelRunner API client for vox-director.

Thin, dependency-free wrapper around the ModelRunner queue API (image / video /
audio generation, upload) — one hosted catalog of models behind a single key,
so no per-model deployment is needed.

Measured against the live API (not just the docs) — the gotchas that cost time:
  1. The model id lives in the URL PATH, not the body. POST /{owner}/{alias}
     takes the input object directly; there is no {"input": {...}} envelope and
     no "model" body field.
  2. A queued job reports "IN_QUEUE" for its whole cold start and may never
     report "IN_PROGRESS" — a 41s cold start was observed going straight from
     IN_QUEUE to COMPLETED. Never wait for IN_PROGRESS.
  3. The per-model /status URL never carries the output. Read the result from
     GET /requests/{id}, which needs no model id and so works from a bare job id.
  4. `output` is an ARRAY of URLs for most image models and a BARE URL STRING
     for most video models. Normalize both.
  5. Unknown input fields are forwarded to the model rather than rejected here,
     so a param the model does not declare fails downstream instead of at
     submit. input_fields() reads the public schema and filter_params() drops
     what the model does not declare, before it can cost anything.

Env: MODELRUNNER_API_KEY must be set.
"""
import json
import os
import subprocess
import urllib.error
import urllib.request

QUEUE_BASE = "https://queue.modelrunner.run"
CATALOG_BASE = "https://modelrunner.run"
UA = "vox-director/0.1 (+https://modelrunner.ai)"


class ModelRunnerError(RuntimeError):
    pass


def _key() -> str:
    k = os.environ.get("MODELRUNNER_API_KEY")
    if not k:
        raise ModelRunnerError("MODELRUNNER_API_KEY is not set. Get one at "
                               "https://modelrunner.ai")
    return k


def _headers(json_body: bool = True) -> dict:
    h = {"Authorization": f"Key {_key()}", "User-Agent": UA}
    if json_body:
        h["Content-Type"] = "application/json"
    return h


def _request(url: str, *, method: str = "GET", body: dict | None = None,
             headers: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers=headers if headers is not None else _headers(body is not None))
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:400]
        raise ModelRunnerError(f"{method} {url} -> HTTP {e.code}: {detail}") from None
    except urllib.error.URLError as e:
        raise ModelRunnerError(f"{method} {url} -> {e.reason}") from None


# --- Catalog (public, no key) ----------------------------------------------

_SCHEMA_CACHE: dict[str, set] = {}


def input_fields(model: str) -> set:
    """Field names the model declares, read from the PUBLIC catalog (no key).

    Returns an empty set if the model publishes no usable input schema, which
    filter_params() treats as "do not filter".
    """
    if model in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[model]
    fields: set = set()
    try:
        doc = _request(f"{CATALOG_BASE}/models/{model}",
                       headers={"User-Agent": UA})
        schemas = ((doc.get("schema") or {}).get("components") or {}).get("schemas") or {}
        props = (schemas.get("Input") or {}).get("properties") or {}
        fields = set(props)
    except ModelRunnerError:
        pass
    _SCHEMA_CACHE[model] = fields
    return fields


def filter_params(model: str, params: dict) -> tuple[dict, list]:
    """Drop params the model does not declare. Returns (kept, dropped_names).

    Stage params are written per model family, so a param that is meaningful on
    one backend can be unknown on another. Dropping before submit keeps an
    unknown field from failing a job that has already been billed.
    """
    declared = input_fields(model)
    if not declared:
        return dict(params), []
    kept = {k: v for k, v in params.items() if k in declared}
    dropped = [k for k in params if k not in declared]
    return kept, dropped


# --- Params -----------------------------------------------------------------

#: Sizes this catalog accepts as an `image_size` preset, "<w>_<h>_<res>".
IMAGE_SIZE_ASPECTS = ("1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3", "21:9", "9:21")
IMAGE_SIZE_RES = ("512", "1k", "2k", "4k")


def image_size_preset(aspect: str, resolution: str) -> str | None:
    """Map a vox aspect+resolution pair to this catalog's `image_size` preset.

    Text-to-image models here take one `image_size` rather than a separate
    aspect_ratio and resolution, so without this the aspect is simply lost and
    keyframes come back square. Returns None for a pair with no preset, which
    leaves the model on its own default.
    """
    if aspect not in IMAGE_SIZE_ASPECTS or resolution not in IMAGE_SIZE_RES:
        return None
    return f"{aspect.replace(':', '_')}_{resolution}"


# --- Generation -------------------------------------------------------------

def submit(model: str, params: dict) -> str:
    """Submit a job to a catalog model; return the request id."""
    kept, dropped = filter_params(model, params)
    if dropped:
        print(f"[modelrunner] {model}: dropped undeclared param(s) {', '.join(sorted(dropped))}")
    res = _request(f"{QUEUE_BASE}/{model}", method="POST", body=kept)
    rid = res.get("request_id")
    if not rid:
        raise ModelRunnerError(f"submit to {model} returned no request_id: {str(res)[:200]}")
    return rid


def get(request_id: str) -> dict:
    """Fetch a request record by id. Needs no model id (see gotcha 3)."""
    return _request(f"{QUEUE_BASE}/requests/{request_id}")


def first_url(output) -> str | None:
    """Normalize `output` — array of URLs, bare URL string, or None (gotcha 4)."""
    if isinstance(output, list):
        return output[0] if output else None
    if isinstance(output, str):
        return output or None
    return None


# --- Files ------------------------------------------------------------------

def upload(path: str) -> str:
    """Upload a local file and return its public URL.

    Two steps: ask for a presigned PUT url, then stream the bytes straight to
    storage — the file never passes through the API.
    """
    name = os.path.basename(path)
    ext = os.path.splitext(name)[1].lower()
    content_type = {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".webp": "image/webp", ".mp4": "video/mp4", ".mp3": "audio/mpeg",
        ".wav": "audio/wav", ".m4a": "audio/mp4",
    }.get(ext, "application/octet-stream")

    res = _request(f"{QUEUE_BASE}/storage/upload/initiate", method="POST",
                   body={"file_name": name, "content_type": content_type})
    put_url, file_url = res.get("upload_url"), res.get("file_url")
    if not put_url or not file_url:
        raise ModelRunnerError(f"upload initiate returned no url: {str(res)[:200]}")

    # curl rather than urllib: same reason the download helper uses it, and it
    # streams the body instead of holding the whole file in memory.
    proc = subprocess.run(
        ["curl", "-sS", "-X", "PUT", "-H", f"Content-Type: {content_type}",
         "--data-binary", f"@{path}", put_url, "-o", "/dev/null", "-w", "%{http_code}"],
        capture_output=True, text=True)
    code = (proc.stdout or "").strip()
    if proc.returncode != 0 or code != "200":
        raise ModelRunnerError(f"upload PUT failed ({code or proc.returncode}): {proc.stderr[:200]}")
    return file_url


def download(url: str, dest: str) -> str:
    """Download a generated asset to `dest`."""
    proc = subprocess.run(["curl", "-sSL", url, "-o", dest], capture_output=True, text=True)
    if proc.returncode != 0:
        raise ModelRunnerError(f"download failed: {proc.stderr[:200]}")
    return dest
