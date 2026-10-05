#!/usr/bin/env python3
"""
Provider abstraction — the pluggable media backend the pipeline stages talk to.

Atlas Cloud is the default backend. Stages call a Provider (submit_image/video/
audio, remove_bg, get_status, upload, download) instead of a concrete client, so
adding a backend is: subclass Provider + one registry entry.
Pick a backend per project with beats.json `{"provider": "atlas_cloud"}` (default).

A backend also owns its MODEL IDS. Stage-level ids are per-catalog, so a stage
asks for a ROLE ("image", "video", "tts", ...) via model_for(role, default) and
the backend answers with an id from its own catalog. Atlas Cloud keeps using the
stage constant, so its behavior is unchanged.

The layer is a thin in-process wrapper — zero extra network hops, so it does NOT
slow the pipeline; the only cost is the API latency, which is unchanged.
"""
import os
import time
from abc import ABC, abstractmethod

import atlas_cloud
import modelrunner


class ProviderError(RuntimeError):
    pass


class Provider(ABC):
    """The surface the stages need. get_status normalizes every backend's polling
    response to {status: pending|completed|failed, output: <url|None>, error}."""
    name = "base"

    #: role -> model id in THIS backend's catalog. Empty means "use the stage's
    #: own constant", which is what keeps Atlas Cloud behaving exactly as before.
    MODELS: dict = {}

    def model_for(self, role, default=None):
        """Resolve a stage role ("image", "video", "tts", ...) to a model id.

        Falls back to the stage's own constant when the backend declares no id
        for that role; raises when the backend has a catalog of its own but no
        entry for this role, because silently sending another catalog's id would
        fail downstream on a job that has already been submitted.
        """
        if not self.MODELS:
            return default
        model = self.MODELS.get(role)
        if not model:
            raise ProviderError(
                f"provider '{self.name}' has no model for role '{role}'; "
                f"set one in {type(self).__name__}.MODELS or pick another provider")
        return model

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


class ModelRunnerProvider(Provider):
    """Wraps the modelrunner client — one hosted catalog behind a single key.

    Model ids are "owner/alias" from that catalog and each role default can be
    overridden with MODELRUNNER_MODEL_<ROLE> (e.g. MODELRUNNER_MODEL_IMAGE), so
    a project can swap a model without editing this file.
    """
    name = "modelrunner"

    MODELS = {
        "image": "google/nano-banana-2",
        "image_edit": "qwen/qwen-image-edit",
        "video": "bytedance/seedance-v1-pro-fast",
        "video_edit": "wan-video/wan-vace/video-edit",
        "video_ref": "bytedance/seedance-v2/reference-to-video",
        "tts": "minimax/speech-02-hd",
        "music": "ace-studio/ace-step",
        "rmbg": "bria/background/remove",
    }

    def model_for(self, role, default=None):
        override = os.environ.get(f"MODELRUNNER_MODEL_{role.upper()}")
        return override or super().model_for(role, default)

    def submit_image(self, model, prompt, **params):
        # Text-to-image models in this catalog take one `image_size` preset
        # instead of a separate aspect_ratio + resolution, so translate the
        # pair the stages build. Without this the aspect is dropped and a 16:9
        # keyframe comes back square.
        if "image_size" not in params and "image_size" in modelrunner.input_fields(model):
            preset = modelrunner.image_size_preset(params.get("aspect_ratio", ""),
                                                   params.get("resolution", ""))
            if preset:
                params = {k: v for k, v in params.items()
                          if k not in ("aspect_ratio", "resolution")}
                params["image_size"] = preset
        return modelrunner.submit(model, {"prompt": prompt, **params})

    def submit_video(self, model, prompt, **params):
        return modelrunner.submit(model, {"prompt": prompt, **params})

    def submit_audio(self, model, **params):
        return modelrunner.submit(model, params)

    def remove_bg(self, model, image_url, **params):
        # This catalog names the input image_url; the stages pass a bare URL.
        return modelrunner.submit(model, {"image_url": image_url, **params})

    def get_status(self, job_id):
        try:
            d = modelrunner.get(job_id)
        except modelrunner.ModelRunnerError as e:
            return {"status": "failed", "output": None, "error": str(e)}
        st = d.get("status")
        if st == "COMPLETED":
            return {"status": "completed",
                    "output": modelrunner.first_url(d.get("output")),
                    "error": None}
        if st in ("FAILED", "CANCELLED"):
            return {"status": "failed", "output": None, "error": d.get("error") or st}
        # IN_QUEUE covers the whole cold start; there may be no IN_PROGRESS.
        return {"status": "pending", "output": None, "error": None}

    def upload(self, path):
        return modelrunner.upload(path)

    def download(self, url, dest):
        return modelrunner.download(url, dest)


_REGISTRY = {"atlas_cloud": AtlasCloudProvider, "modelrunner": ModelRunnerProvider}


def get_provider(name=None):
    """Return a Provider instance by name (default 'atlas_cloud')."""
    name = (name or "atlas_cloud").lower()
    if name not in _REGISTRY:
        raise ProviderError(f"unknown provider '{name}'; available: {list(_REGISTRY)}")
    return _REGISTRY[name]()


def run_jobs(prov, specs, *, poll_s=3, stall_s=90, max_retries=2, deadline_s=900):
    """Submit + poll a batch of jobs, resubmitting any that FAIL or STALL.

    specs: dict of key -> submit() callable returning a job id. A job that fails,
    or stays pending past `stall_s`, is resubmitted (fresh id) up to `max_retries`
    times — this is what stops one stuck prediction from wasting the whole deadline.
    Returns key -> output URL (or None). Prints progress like the old loops did.
    """
    st = {}
    for key, submit in specs.items():
        st[key] = {"pid": submit(), "t": time.time(), "tries": 0}
        print(f"[{key}] submitted {st[key]['pid']}")

    done = {}
    deadline = time.time() + deadline_s
    while len(done) < len(specs) and time.time() < deadline:
        time.sleep(poll_s)
        now = time.time()
        for key, submit in specs.items():
            if key in done:
                continue
            s = st[key]
            r = prov.get_status(s["pid"])
            status = r["status"]
            if status == "completed":
                done[key] = r["output"]
                print(f"[{key}] done")
            elif status == "failed" or (status == "pending" and now - s["t"] > stall_s):
                if s["tries"] < max_retries:
                    s["tries"] += 1
                    s["pid"] = submit()
                    s["t"] = time.time()
                    why = "failed" if status == "failed" else f"stalled>{int(stall_s)}s"
                    print(f"[{key}] {why} -> resubmit #{s['tries']} ({s['pid']})")
                elif status == "failed":
                    done[key] = None
                    print(f"[{key}] FAILED: {(r.get('error') or '')[:120]}")
                # stalled + out of retries: keep waiting until the deadline
    for key in specs:
        done.setdefault(key, None)
    return done
