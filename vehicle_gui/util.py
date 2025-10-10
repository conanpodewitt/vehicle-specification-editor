import os
import sys


def which_all(cmd, mode=os.F_OK | os.X_OK, path=None):
    """Return a list of full paths to all executables named `cmd` on PATH."""
    if path is None:
        path = os.environ.get("PATH", os.defpath)
    paths = path.split(os.pathsep)

    # If cmd has a path separator, check it directly.
    if os.path.dirname(cmd):
        p = cmd
        return [p] if os.path.isfile(p) and os.access(p, mode) else []

    # Windows: respect PATHEXT; POSIX: just the name.
    exts = []
    if sys.platform == "win32":
        pathext = os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD")
        exts = [e.lower() for e in pathext.split(os.pathsep)]
        if any(cmd.lower().endswith(e) for e in exts):
            exts = [""]

    candidates = [cmd + ext for ext in (exts or [""])]

    found, seen = [], set()
    for d in paths:
        d = d.strip('"')
        if not d:
            continue
        for name in candidates:
            full = os.path.join(d, name)
            if os.path.isfile(full) and os.access(full, mode):
                # Deduplicate by real path to avoid repeats via symlinks.
                rp = os.path.realpath(full)
                if rp not in seen:
                    seen.add(rp)
                    found.append(full)
    return found