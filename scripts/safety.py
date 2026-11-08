"""Small shared filesystem boundaries for generated project files."""
import os
from pathlib import Path


def component(value):
    """Keep ordinary labels (including spaces/quotes), never path syntax."""
    if not isinstance(value, (str, int)) or isinstance(value, bool):
        raise ValueError("identifier must be a string or integer path component")
    value = str(value)
    if (not value.strip() or value in (".", "..") or "/" in value or "\\" in value
            or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise ValueError("identifier must be a single safe path component")
    return value


def output_path(root, *parts):
    """Resolve existing symlinks before any generated-file write."""
    root = Path(root).resolve()
    path = root.joinpath(*parts)
    try:
        path.resolve().relative_to(root)
    except ValueError:
        raise ValueError("generated output escapes outside project root") from None
    if any(ord(c) < 32 or ord(c) == 127 for c in str(path)):
        raise ValueError("output path contains a control character")
    return str(path)


def validate_project(root, doc):
    """Preflight all output namespaces before uploads/submissions/media work.

    The caller selects the project root; absolute source media paths remain valid.
    Existing output symlinks may point within that root, but never outside it.
    """
    if "project" in doc:
        component(doc["project"])
    for beat in doc.get("beats", []):
        component(beat["id"])
        for shot in beat.get("shots") or []:
            if "id" in shot:
                component(shot["id"])
    for element in doc.get("elements", []):
        component(element["name"])
    for name in ("beats.json", "elements_spec.json", "keyframes", "clips", "clips/plates",
                 "audio", "audio/host", "segments", "elements", "style-bakeoff", "_seg",
                 "final.mp4", "final_mg.mp4"):
        path = output_path(root, name)
        if os.path.isdir(path):
            for parent, dirs, files in os.walk(path, followlinks=False):
                for child in dirs + files:
                    output_path(root, os.path.relpath(os.path.join(parent, child), root))


def concat_entry(path):
    """ffconcat uses single quotes, with quote escapes outside quoted spans."""
    path = os.path.abspath(path)
    if any(ord(c) < 32 or ord(c) == 127 for c in path):
        raise ValueError("ffconcat filename contains a control character")
    return "file '" + path.replace("'", "'\\''") + "'\n"
