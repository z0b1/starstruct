# checker.py
# Validates a submitted file tree against a template.

from __future__ import annotations
import fnmatch
from template_defs import TEMPLATES

# Folders that are collapsed in the tree by default (never recursed into).
# Templates can extend this list via an "ignore" key.
DEFAULT_IGNORE: set[str] = {
    "node_modules",
    ".next",
    ".nuxt",
    ".svelte-kit",
    "__pycache__",
    ".venv",
    "venv",
    ".git",
    "dist",
    "build",
    ".cache",
    ".parcel-cache",
    "coverage",
    ".turbo",
    ".vercel",
    ".output",
}


def _normalise(paths: list[str]) -> set[str]:
    """Normalise all paths to forward-slash, lowercase for comparison."""
    return {p.replace("\\", "/").lower() for p in paths}


def _matches(pattern: str, paths: set[str]) -> bool:
    """Return True if any path in `paths` matches `pattern` (fnmatch-style)."""
    normalised = pattern.replace("\\", "/").lower()
    for p in paths:
        if fnmatch.fnmatch(p, normalised):
            return True
        if "/" not in normalised and fnmatch.fnmatch(p.split("/")[-1], normalised):
            return True
    return False


def _build_root_dict(paths: list[str], max_depth: int | None, ignore: set[str]) -> dict:
    """Build a nested dict from flat paths, respecting depth and ignore list."""
    root: dict = {}
    for path in sorted(paths):
        parts = path.replace("\\", "/").split("/")

        # Skip any path whose first segment (after project root) is ignored.
        # parts[0] is the project root folder itself, so check from parts[1].
        if any(p.lower() in ignore for p in parts[1:]):
            # Still add the ignored folder as an empty node (so it shows in tree)
            # but don't recurse into it.
            if len(parts) > 1:
                node = root
                node = node.setdefault(parts[0], {})
                ignored_part = next(p for p in parts[1:] if p.lower() in ignore)
                idx = parts.index(ignored_part)
                for part in parts[1:idx + 1]:
                    node = node.setdefault(part, {})
            continue

        if max_depth is not None:
            parts = parts[:max_depth]

        node = root
        for part in parts:
            node = node.setdefault(part, {})

    return root


def build_tree_lines(
    paths: list[str],
    max_depth: int | None = None,
    ignore: set[str] | None = None,
) -> list[str]:
    """
    Given a flat list of relative file paths, produce tree-style lines.
    max_depth : levels to show (None = unlimited).
    ignore    : folder names to collapse (show but not recurse into).
    """
    effective_ignore = ignore if ignore is not None else DEFAULT_IGNORE
    root = _build_root_dict(paths, max_depth, effective_ignore)

    def walk(node: dict, acc: list[str], prefix: str = "", depth: int = 1) -> list[str]:
        if max_depth is not None and depth > max_depth:
            return acc
        items = sorted(node.keys())
        for i, name in enumerate(items):
            is_last  = i == len(items) - 1
            connector = "└── " if is_last else "├── "
            child    = node[name]
            is_dir   = bool(child)
            is_ignored = name.lower() in effective_ignore

            if is_ignored:
                acc.append(f"{prefix}{connector}{name}/  ✂ ignored")
            else:
                label = name + ("/" if is_dir else "")
                acc.append(f"{prefix}{connector}{label}")
                if is_dir:
                    extension = "    " if is_last else "│   "
                    walk(child, acc, prefix + extension, depth + 1)
        return acc

    return walk(root, [])


def check(
    file_paths: list[str],
    template_id: str,
    max_depth: int | None = None,
    extra_ignore: list[str] | None = None,
) -> dict:
    """
    Validate `file_paths` against the named template.

    extra_ignore : additional folder names to ignore (from the frontend).
    """
    if template_id not in TEMPLATES:
        raise ValueError(f"Unknown template: '{template_id}'. "
                         f"Available: {list(TEMPLATES.keys())}")

    tpl = TEMPLATES[template_id]

    # Merge default + template-level + user-supplied ignore lists
    ignore: set[str] = DEFAULT_IGNORE.copy()
    ignore.update(tpl.get("ignore", []))
    if extra_ignore:
        ignore.update(i.lower() for i in extra_ignore)

    paths = _normalise(file_paths)

    major_missing:   list[str] = []
    major_forbidden: list[str] = []
    minor_missing:   list[str] = []

    for req in tpl.get("required", []):
        if not _matches(req, paths):
            major_missing.append(req)

    for fbd in tpl.get("forbidden", []):
        if _matches(fbd, paths):
            major_forbidden.append(fbd)

    for rec in tpl.get("recommended", []):
        if not _matches(rec, paths):
            minor_missing.append(rec)

    has_major = bool(major_missing or major_forbidden)
    has_minor = bool(minor_missing)

    if has_major:
        status = "error"
    elif has_minor:
        status = "warning"
    else:
        status = "ok"

    markdown: str | None = None
    if not has_major:
        tree_lines = build_tree_lines(file_paths, max_depth, ignore)
        root_name  = _guess_root(file_paths)
        depth_note = f" (depth: {max_depth})" if max_depth is not None else ""

        md_parts = [f"# `{root_name}` — structure{depth_note}", ""]
        md_parts.append("```")
        md_parts.append(root_name + "/")
        md_parts.extend(tree_lines)
        md_parts.append("```")
        md_parts.append("")

        if status == "ok":
            md_parts.append("✅ **Passes** the `" + tpl["label"] + "` template.")
        else:
            md_parts.append("⚠️ **Passes with warnings** — `" + tpl["label"] + "` template.")
            md_parts.append("")
            md_parts.append("### Recommended files not found")
            for m in minor_missing:
                md_parts.append(f"- `{m}`")

        markdown = "\n".join(md_parts)

    return {
        "status":          status,
        "template":        tpl["label"],
        "markdown":        markdown,
        "major_missing":   major_missing,
        "major_forbidden": major_forbidden,
        "minor_missing":   minor_missing,
    }


def _guess_root(paths: list[str]) -> str:
    if not paths:
        return "project"
    parts = paths[0].replace("\\", "/").split("/")
    if len(parts) > 1:
        return parts[0]
    return "project"


def list_templates() -> list[dict]:
    return [{"id": k, "label": v["label"]} for k, v in TEMPLATES.items()]