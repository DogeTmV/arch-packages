"""Pure rename-planning logic for batchrename. No Qt imports live here."""

import os


class BatchrenameError(Exception):
    """A user-facing error raised while planning renames."""


def expand_pattern(pattern, name, index, ext):
    """Substitute {name}, {n}, {nn} and {ext} in *pattern*."""
    return (
        str(pattern)
        .replace("{name}", str(name))
        .replace("{n}", str(index))
        .replace("{nn}", "%02d" % int(index))
        .replace("{ext}", str(ext))
    )


def build_plan(paths, pattern, start=1):
    """Return ordered (source, destination) pairs for *paths*.

    The original extension is appended unless the pattern contains {ext}.
    """
    plan = []
    used = set()
    for offset, path in enumerate(paths):
        source = os.fspath(path)
        stem, suffix = os.path.splitext(os.path.basename(source))
        ext = suffix.lstrip(".")
        new_name = expand_pattern(pattern, stem, int(start) + offset, ext)
        if "{ext}" not in str(pattern) and ext:
            new_name += "." + ext
        destination = os.path.join(os.path.dirname(source), new_name)
        if destination in used:
            raise BatchrenameError(
                "duplicate destination path: %s" % destination
            )
        used.add(destination)
        plan.append((source, destination))
    return plan


def apply_plan(plan, dry_run=False):
    """Rename every pair in *plan*, or just return the pairs when dry_run."""
    pairs = [(os.fspath(src), os.fspath(dst)) for src, dst in plan]
    if dry_run:
        return pairs
    for source, destination in pairs:
        os.rename(source, destination)
    return pairs
