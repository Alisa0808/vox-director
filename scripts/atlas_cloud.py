#!/usr/bin/env python3
"""
Atlas Cloud API client for vox-director.

Thin, dependency-free wrapper around the Atlas Cloud Media Generation API
(image / video / upload) plus the OpenAI-compatible LLM endpoint.

Hard-won gotchas baked in:
  1. Every request MUST send a real User-Agent header — the default urllib UA
     is blocked by the WAF and returns 403 Forbidden.
  2. Generated assets live on OSS behind the user's local proxy; python's
     urlretrieve dies with "Remote end closed connection". Download via curl.
  3. POST generation calls are NOT retried (they create billable tasks).
     GET polls are safe to retry.

Env: ATLASCLOUD_API_KEY must be set.
"""
import json
import os
import subprocess
import time
import urllib.request
import urllib.error
from urllib.parse import urlsplit

MEDIA_BASE = "https://api.atlascloud.ai/api/v1"
LLM_BASE = "https://api.atlascloud.ai/v1"
UA = "vox-director/0.1 (+https://atlascloud.ai)"
# Atlas's own delivery domains (examples/, README, references/); downloads refuse
# everything else, and no other host is ever sent the API key.
ALLOWED_HOSTS = {"api.atlascloud.ai", "www.atlascloud.ai", "static.atlascloud.ai",
                 "atlas-img.oss-accelerate-overseas.aliyuncs.com",
                 "atlas-media.oss-us-west-1.aliyuncs.com"}


class AtlasCloudError(RuntimeError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Never follow a redirect: it would silently re-send the Authorization header."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def check_url(url, *, credentialed=False):
    """Only https:// to an allowed Atlas host, and no curl option look-alikes."""
    if (not isinstance(url, str) or any(ord(c) <= 32 or ord(c) == 127 for c in url)
            or "\\" in url or url.startswith("-")):
        raise AtlasCloudError("refusing unsafe URL")
    try:
        parts = urlsplit(url)
        hosts = {"api.atlascloud.ai"} if credentialed else ALLOWED_HOSTS
        if (parts.scheme != "https" or parts.hostname not in hosts
                or parts.username is not None or parts.password is not None
                or parts.port not in (None, 443) or parts.fragment):
            raise ValueError
    except ValueError:
        raise AtlasCloudError("URL must use HTTPS and an allowed Atlas host") from None
    return url


def _curl_quote(value):
    """Quote a curl config value (not shell syntax)."""
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise AtlasCloudError("curl config value contains a control character")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _key() -> str:
    k = os.environ.get("ATLASCLOUD_API_KEY")
    if not k:
        raise AtlasCloudError("ATLASCLOUD_API_KEY is not set. Get one at "
                         "https://www.atlascloud.ai/console/api-keys")
    if any(ord(c) < 32 or ord(c) == 127 for c in k):
        raise AtlasCloudError("API key contains a control character")
    return k


def _headers(json_body: bool = True) -> dict:
    h = {"Authorization": f"Bearer {_key()}", "User-Agent": UA}
    if json_body:
        h["Content-Type"] = "application/json"
    return h


def _post(path: str, payload: dict, base: str = MEDIA_BASE, timeout: int = 60) -> dict:
    url = check_url(base + path, credentialed=True)
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers=_headers(), method="POST")
    try:
        with _OPENER.open(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise AtlasCloudError(f"POST {path} -> {e.code}: {e.read().decode()[:400]}") from e


def _get(path: str, base: str = MEDIA_BASE, timeout: int = 60, retries: int = 3) -> dict:
    url = check_url(base + path, credentialed=True)
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=_headers(json_body=False))
            with _OPENER.open(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            # A prediction that failed upstream (e.g. a content-policy rejection) can
            # come back wrapped in a non-2xx status, but the body is still the normal
            # JSON envelope with the real status/error_code -- `except URLError` below
            # would catch this too (HTTPError subclasses it) but collapses it to a bare
            # "HTTP Error 400: Bad Request" and throws the diagnosis away. Parse it and
            # hand it back like any other response so callers see the real status.
            body = e.read().decode(errors="replace")
            try:
                return json.loads(body)
            except ValueError:
                last = AtlasCloudError(f"GET {path} -> {e.code}: {body[:400]}")
                break
        except (urllib.error.URLError, TimeoutError) as e:  # transient
            last = e
            time.sleep(2 ** i)
    raise AtlasCloudError(f"GET {path} failed after {retries} tries: {last}")


# ---------------------------------------------------------------- generation

def submit_image(model: str, prompt: str, **params) -> str:
    """Submit an image generation task; return prediction id."""
    body = {"model": model, "prompt": prompt, **params}
    return _post("/model/generateImage", body)["data"]["id"]


def submit_video(model: str, prompt: str, **params) -> str:
    """Submit a video generation task; return prediction id.

    For image-to-video pass image="<url>"; for reference-to-video pass the model's own
    keys: Kling takes images=["<url>", ...] (1-5 refs); Seedance 2.0 takes
    reference_images=[...] and reference_audios=[...] (see references/host-mode.md).
    """
    body = {"model": model, "prompt": prompt, **params}
    return _post("/model/generateVideo", body)["data"]["id"]


def submit_media(model: str, **params) -> str:
    """Submit any media task that runs through the generateVideo endpoint
    (audio/TTS, music, etc.); return prediction id."""
    body = {"model": model, **params}
    return _post("/model/generateVideo", body)["data"]["id"]


def transcribe(audio_url: str, interval: int = 3, timeout_s: int = 300, **params) -> dict:
    """Blocking ASR via xai/stt-v1. Returns the full stt_result: {"text", "language",
    "duration", "words": [{"text","start","end"}, ...]} (word-level timestamps).

    Submits to /model/generateAudio (the model's real endpoint per its schema),
    NOT /model/generateVideo like submit_media -- and polls for the raw stt_result
    dict directly rather than going through poll()/get_status(), because those only
    surface outputs[0] (the plain transcript string) and would silently drop the
    word timestamps this exists to fetch.
    """
    body = {"model": "xai/stt-v1", "audio": audio_url, **params}
    pid = _post("/model/generateAudio", body)["data"]["id"]
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        time.sleep(interval)
        d = _get(f"/model/prediction/{pid}").get("data", {})
        status = d.get("status", "?")
        if status in ("completed", "succeeded"):
            result = d.get("stt_result")
            if not result:
                raise AtlasCloudError(f"{pid}: completed but no stt_result")
            return result
        if status == "failed":
            raise AtlasCloudError(f"{pid} failed: {json.dumps(d)[:300]}")
    raise AtlasCloudError(f"{pid} timed out after {timeout_s}s")


def poll(prediction_id: str, interval: int = 3, timeout_s: int = 900) -> str:
    """Poll a prediction until done; return the first output URL."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        time.sleep(interval)
        d = _get(f"/model/prediction/{prediction_id}").get("data", {})
        status = d.get("status", "?")
        if status in ("completed", "succeeded"):
            out = d.get("outputs") or d.get("output")
            if isinstance(out, str):
                out = [out]
            if not out:
                raise AtlasCloudError(f"{prediction_id}: completed but no output")
            return out[0]
        if status == "failed":
            raise AtlasCloudError(f"{prediction_id} failed: {json.dumps(d)[:300]}")
    raise AtlasCloudError(f"{prediction_id} timed out after {timeout_s}s")


def image(model: str, prompt: str, **params) -> str:
    """Blocking image generation -> output URL."""
    return poll(submit_image(model, prompt, **params), interval=3, timeout_s=180)


def video(model: str, prompt: str, **params) -> str:
    """Blocking video generation -> output URL."""
    return poll(submit_video(model, prompt, **params), interval=4, timeout_s=900)


# ---------------------------------------------------------------- upload / dl

def upload(file_path: str) -> str:
    """Upload a local file, return its public URL.

    Uses curl (multipart). Authorization travels through stdin config, never
    process arguments or a temporary file. Redirects are not followed.
    """
    url = check_url(f"{MEDIA_BASE}/model/uploadMedia", credentialed=True)
    key = _key()
    # curl -F has its own filename grammar; shell argv quoting is not enough.
    form_path = _curl_quote(os.fspath(file_path))
    config = "header = " + _curl_quote(f"Authorization: Bearer {key}") + "\n"
    out = subprocess.run(
        ["/usr/bin/curl", "-q", "-s", "--fail", "--config", "-",
         "--proto", "=https", "--user-agent", UA,
         "-X", "POST", "--url", url, "-F", f"file=@{form_path}"],
        input=config, capture_output=True, text=True, check=True).stdout
    data = json.loads(out).get("data", {})
    url = data.get("download_url") or data.get("url")
    if not url:
        raise AtlasCloudError(f"upload failed: {out[:300]}")
    return url


def download(url: str, dest: str) -> str:
    """Proxy-safe download via curl (urllib breaks on the OSS host).

    HTTPS Atlas/OSS URLs only (check_url), and --fail so an error page is never
    written to dest as if it were the media.
    """
    subprocess.run(["/usr/bin/curl", "-q", "-s", "--fail", "--retry", "3",
                    "--proto", "=https", "--output", dest, "--url", check_url(url)],
                   check=True)
    if not os.path.exists(dest) or os.path.getsize(dest) == 0:
        raise AtlasCloudError(f"download produced empty file: {url}")
    return dest


# ---------------------------------------------------------------- llm

def chat(model: str, messages: list, **params) -> str:
    """OpenAI-compatible chat completion -> assistant text."""
    body = {"model": model, "messages": messages, **params}
    resp = _post("/chat/completions", body, base=LLM_BASE, timeout=120)
    return resp["choices"][0]["message"]["content"]


if __name__ == "__main__":
    # smoke test: confirm key + UA work
    import sys
    print("key:", "set" if os.environ.get("ATLASCLOUD_API_KEY") else "MISSING")
    if "--ping" in sys.argv:
        url = image("google/nano-banana-2/text-to-image",
                    "a tiny red seal stamp on white paper, minimalist",
                    aspect_ratio="1:1", resolution="1k")
        print("image ok:", url)
