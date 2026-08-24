#!/usr/bin/env python3
"""
Provider abstraction — the pluggable media backend the pipeline stages talk to.

Atlas Cloud is the default and, for now, the only backend. Stages call a Provider
(submit_image/video/audio, remove_bg, get_status, upload, download) instead of a
concrete client, so adding a backend is: subclass Provider + one registry entry.
Pick a backend per project with beats.json `{"provider": "atlas_cloud"}` (default).

The layer is a thin in-process wrapper — zero extra network hops, so it does NOT
slow the pipeline; the only cost is the API latency, which is unchanged.
"""
import time
from abc import ABC, abstractmethod

import atlas_cloud


class ProviderError(RuntimeError):
    pass


class Provider(ABC):
    """The surface the stages need. get_status normalizes every backend's polling
    response to {status: pending|completed|failed, output: <url|None>, error}."""
    name = "base"

    @abstractmethod
    def submit_image(self, model, prompt, **params): ...
    @abstractmethod
    def submit_video(self, model, prompt, **params): ...
    @abstractmethod
    def submit_audio(self, model, **params): ...
    @abstractmethod
    def remove_bg(self, model, image_url, **params): ...
    @abstractmethod
    def get_status(self, job_id): ...
    @abstractmethod
    def upload(self, path): ...
    @abstractmethod
    def download(self, url, dest): ...


class AtlasCloudProvider(Provider):
    """Wraps the atlas_cloud client — identical behavior to calling it directly."""
    name = "atlas_cloud"

    def submit_image(self, model, prompt, **params):
        return atlas_cloud.submit_image(model, prompt, **params)

    def submit_video(self, model, prompt, **params):
        return atlas_cloud.submit_video(model, prompt, **params)

    def submit_audio(self, model, **params):
        return atlas_cloud.submit_media(model, **params)

    def remove_bg(self, model, image_url, **params):
        body = {"model": model, "image": image_url, **params}
        return atlas_cloud._post("/model/generateImage", body)["data"]["id"]

    def get_status(self, job_id):
        try:
            d = atlas_cloud._get(f"/model/prediction/{job_id}").get("data", {})
        except atlas_cloud.AtlasCloudError as e:
            return {"status": "failed", "output": None, "error": str(e)}
        st = d.get("status")
        if st in ("completed", "succeeded"):
            out = d.get("outputs") or d.get("output")
            out = out[0] if isinstance(out, list) else out
            return {"status": "completed", "output": out, "error": None}
        if st == "failed":
            return {"status": "failed", "output": None, "error": d.get("error", "")}
        return {"status": "pending", "output": None, "error": None}

    def upload(self, path):
        return atlas_cloud.upload(path)

    def download(self, url, dest):
        return atlas_cloud.download(url, dest)


_REGISTRY = {"atlas_cloud": AtlasCloudProvider}


def get_provider(name=None):
    """Return a Provider instance by name (default 'atlas_cloud')."""
    name = (name or "atlas_cloud").lower()
    if name not in _REGISTRY:
        raise ProviderError(f"unknown provider '{name}'; available: {list(_REGISTRY)}")
    return _REGISTRY[name]()


def run_jobs(prov, specs, *, poll_s=3, stall_s=90, deadline_s=900):
    """Submit each job once, then poll without creating replacement tasks.

    specs: dict of key -> submit() callable returning a job id. Failed, stalled,
    or timed-out jobs return None together with their prediction id so callers can
    inspect them and decide whether a new billable submission is appropriate.
    """
    st = {}
    for key, submit in specs.items():
        st[key] = {"pid": submit(), "t": time.time()}
        print(f"[{key}] submitted {st[key]['pid']}")

    done = {}
    deadline = time.time() + deadline_s
    while len(done) < len(specs) and time.time() < deadline:
        time.sleep(poll_s)
        now = time.time()
        for key in specs:
            if key in done:
                continue
            s = st[key]
            r = prov.get_status(s["pid"])
            status = r["status"]
            if status == "completed":
                done[key] = r["output"]
                print(f"[{key}] done")
            elif status == "failed":
                done[key] = None
                print(f"[{key}] FAILED ({s['pid']}): {(r.get('error') or '')[:120]}")
            elif status == "pending" and now - s["t"] > stall_s:
                done[key] = None
                print(f"[{key}] STALLED>{int(stall_s)}s ({s['pid']}): not resubmitted")
    for key in specs:
        if key not in done:
            done[key] = None
            print(f"[{key}] TIMED OUT ({st[key]['pid']}): not resubmitted")
    return done
