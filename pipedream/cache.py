"""Content-addressed result cache built on pickle + sha256."""
from __future__ import annotations

import hashlib
import os
import pickle
import re
import shutil


def hash_params(params):
    """Stable hash of a pipeline parameter mapping."""
    blob = "\x00".join(f"{key}={params[key]!r}" for key in sorted(params))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _slug(name):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(name)).strip("_") or "default"


class Cache:
    """Disk cache for step results.

    An entry is keyed by the step's identity (name + source hash), the
    pipeline parameters and the pickled upstream results, so editing a step's
    code, changing a parameter or changing any upstream output invalidates
    the entry automatically.

    ``lookup`` returns ``(found, value)`` because ``None`` is a perfectly
    cacheable result.  All failures (un-picklable values, corrupt files, full
    disks) degrade gracefully to cache misses rather than failing the run.
    """

    def __init__(self, root, namespace="default"):
        self.dir = os.path.join(os.path.abspath(os.path.expanduser(str(root))), _slug(namespace))

    def key(self, step, params_hash, inputs):
        """Cache key for a step, or ``None`` when inputs cannot be hashed.

        Each input is pickled with a fresh memo so that the key depends only
        on values, never on which objects happen to be shared between
        inputs (plain pickle would emit memo references for shared strings,
        making keys unstable across cache round-trips).
        """
        try:
            digest = hashlib.sha256()
            for item in inputs:
                digest.update(pickle.dumps(item, protocol=4))
        except Exception:
            return None
        digest.update(step.name.encode("utf-8"))
        digest.update(step.source_hash.encode("utf-8"))
        digest.update(params_hash.encode("utf-8"))
        return digest.hexdigest()

    def lookup(self, key):
        """Return ``(found, value)`` for a cache key."""
        if key is None:
            return False, None
        path = os.path.join(self.dir, key + ".result")
        if not os.path.exists(path):
            return False, None
        try:
            with open(path, "rb") as fh:
                return True, pickle.load(fh)
        except Exception:
            try:
                os.remove(path)  # corrupt entry: better to delete than crash
            except OSError:
                pass
            return False, None

    def store(self, key, value):
        """Best-effort write; returns True when the value was cached."""
        if key is None:
            return False
        path = os.path.join(self.dir, key + ".result")
        try:
            os.makedirs(self.dir, exist_ok=True)
            tmp = path + "." + str(os.getpid()) + ".tmp"
            with open(tmp, "wb") as fh:
                pickle.dump(value, fh, protocol=pickle.HIGHEST_PROTOCOL)
            os.replace(tmp, path)
            return True
        except Exception:
            return False

    def clear(self):
        """Delete every cached entry for this namespace; returns the count."""
        if not os.path.isdir(self.dir):
            return 0
        count = sum(1 for f in os.listdir(self.dir) if f.endswith(".result"))
        shutil.rmtree(self.dir, ignore_errors=True)
        return count
