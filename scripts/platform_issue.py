#!/usr/bin/env python3
"""platform_issue.py — cross-platform issue/label/repo helper for backlog/start/bootstrap/sync skills.

Bridges `gh` (GitHub CLI) and `glab` (GitLab CLI) so SKILL.md files don't need
platform branching. Subcommands take a unified shape and emit a unified output
schema (GitHub-flavored field names) regardless of source platform.

See docs/15-三件套skill支持GitLab双轨/PLAN.md for design rationale.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

PLATFORM_GITHUB = "github"
PLATFORM_GITLAB = "gitlab"
PLATFORM_UNKNOWN = "unknown"

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_PLATFORM_UNKNOWN = 2
EXIT_AUTH_FAILED = 3
EXIT_CLI_MISSING = 4

DEBUG = False


def _dbg(*args):
    if DEBUG:
        print("[debug]", *args, file=sys.stderr)


def _run(cmd):
    _dbg("run:", " ".join(cmd))
    try:
        return subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        sys.stderr.write(f"error: command not found: {cmd[0]} (install it and retry)\n")
        sys.exit(EXIT_CLI_MISSING)


def _call_gh(args):
    return _run(["gh"] + args)


def _call_glab(args):
    return _run(["glab"] + args)


# ---------------------------------------------------------------- platform


def detect_platform():
    result = _run(["git", "remote", "get-url", "origin"])
    if result.returncode != 0:
        return PLATFORM_UNKNOWN
    url = result.stdout.strip().lower()
    if "github.com" in url:
        return PLATFORM_GITHUB
    if "gitlab" in url:
        return PLATFORM_GITLAB
    return PLATFORM_UNKNOWN


def resolve_platform(override):
    if override:
        return override
    return detect_platform()


# ---------------------------------------------------------------- color


def normalize_color(color, platform):
    raw = (color or "").lstrip("#")
    if platform == PLATFORM_GITLAB:
        return "#" + raw
    return raw


# ---------------------------------------------------------------- field map


def normalize_issue(raw, platform):
    if platform == PLATFORM_GITLAB:
        return {
            "number": raw.get("iid"),
            "title": raw.get("title", ""),
            "body": raw.get("description") or "",
            "url": raw.get("web_url", ""),
            "labels": list(raw.get("labels", []) or []),
        }
    labels = raw.get("labels", []) or []
    return {
        "number": raw.get("number"),
        "title": raw.get("title", ""),
        "body": raw.get("body") or "",
        "url": raw.get("url", ""),
        "labels": [lbl["name"] if isinstance(lbl, dict) else lbl for lbl in labels],
    }


# ---------------------------------------------------------------- yml parser


def _strip_trailing_comment(value):
    in_str = None
    for i, ch in enumerate(value):
        if in_str:
            if ch == in_str:
                in_str = None
            continue
        if ch in ('"', "'"):
            in_str = ch
            continue
        if ch == "#" and (i == 0 or value[i - 1].isspace()):
            return value[:i]
    return value


def parse_labels_yml(text):
    """Minimal parser for `templates/_common/__root__/.github/labels.yml` schema:
    top-level list of dicts with `name`/`color`/`description` string fields.
    Supports optional `---` doc header, `#` line/trailing comments, single/double
    quoted or bare scalar values. Not a general YAML parser — schema is fixed.
    """
    items = []
    current = None
    field_re = re.compile(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$")
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#") or stripped == "---":
            continue
        if stripped.startswith("- "):
            if current is not None:
                items.append(current)
            current = {}
            stripped = stripped[2:].strip()
        m = field_re.match(stripped)
        if not m:
            continue
        key, value = m.group(1), m.group(2)
        value = _strip_trailing_comment(value).strip()
        if len(value) >= 2 and value[0] in ('"', "'") and value[-1] == value[0]:
            value = value[1:-1]
        if current is None:
            current = {}
        current[key] = value
    if current is not None:
        items.append(current)
    return items


# ---------------------------------------------------------------- handlers


def cmd_detect_platform(args):
    plat = resolve_platform(args.platform)
    print(plat)
    return EXIT_OK if plat != PLATFORM_UNKNOWN else EXIT_PLATFORM_UNKNOWN


def cmd_auth_status(args):
    plat = resolve_platform(args.platform)
    if plat == PLATFORM_UNKNOWN:
        sys.stderr.write("error: cannot detect platform from git remote origin\n")
        return EXIT_PLATFORM_UNKNOWN
    if plat == PLATFORM_GITHUB:
        result = _call_gh(["auth", "status"])
    else:
        result = _call_glab(["auth", "status"])
    sys.stderr.write(result.stderr)
    sys.stdout.write(result.stdout)
    if result.returncode != 0:
        return EXIT_AUTH_FAILED
    print(f"\n{plat}: authenticated")
    return EXIT_OK


def cmd_repo_slug(args):
    plat = resolve_platform(args.platform)
    if plat == PLATFORM_UNKNOWN:
        sys.stderr.write("error: cannot detect platform from git remote origin\n")
        return EXIT_PLATFORM_UNKNOWN
    if plat == PLATFORM_GITHUB:
        result = _call_gh(
            ["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"]
        )
        if result.returncode != 0:
            sys.stderr.write(result.stderr)
            return EXIT_ERROR
        print(result.stdout.strip())
        return EXIT_OK
    result = _call_glab(["repo", "view", "-F", "json"])
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        return EXIT_ERROR
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"error: cannot parse glab repo view json: {e}\n")
        return EXIT_ERROR
    slug = data.get("path_with_namespace") or data.get("fullPath") or ""
    if not slug:
        sys.stderr.write("error: glab repo view json missing path_with_namespace\n")
        return EXIT_ERROR
    print(slug)
    return EXIT_OK


def build_issue_create_cmd(platform, title, body_file, body, labels, repo):
    """Build the gh/glab issue-create argv (pure, no execution).

    `repo` (owner/name slug) targets a cross-repo issue — e.g. filing a
    distillation issue to claude-code-global from inside another project.
    GitHub reads the body from --body-file; GitLab takes it inline via
    --description (so callers pass both body_file path and body text).
    """
    if platform == PLATFORM_GITHUB:
        cmd = ["gh", "issue", "create", "--title", title, "--body-file", str(body_file)]
    else:
        cmd = [
            "glab",
            "issue",
            "create",
            "--title",
            title,
            "--description",
            body,
            "--yes",
        ]
    if repo:
        cmd += ["--repo", repo]
    for lbl in labels or []:
        cmd += ["--label", lbl]
    return cmd


def cross_repo_label_guard_error(repo, labels, allow_no_label):
    """Guard cross-repo issue creation against being filed with zero labels.

    Distillation issues filed into claude-code-global from another project
    (`--repo` set) must carry classifying labels — a label-less cross-repo
    issue (e.g. a历史 #12 filed ad-hoc outside `/finish`) can't be triaged.
    Returns an error string when creation should be blocked, else None.
    In-repo creation (`repo` falsy, e.g. backlog/start) is never blocked here.
    """
    if repo and not (labels or []) and not allow_no_label:
        return (
            "cross-repo issue (--repo) requires at least one --label; "
            "三轴 label 是跨仓库沉淀 issue 的归类前提。"
            "pass --allow-no-label to override deliberately."
        )
    return None


def cmd_issue_create(args):
    plat = resolve_platform(args.platform)
    if plat == PLATFORM_UNKNOWN:
        sys.stderr.write("error: cannot detect platform from git remote origin\n")
        return EXIT_PLATFORM_UNKNOWN
    guard_err = cross_repo_label_guard_error(args.repo, args.label, args.allow_no_label)
    if guard_err:
        sys.stderr.write(f"error: {guard_err}\n")
        return EXIT_ERROR
    body_path = Path(args.body_file)
    if not body_path.exists():
        sys.stderr.write(f"error: body file not found: {body_path}\n")
        return EXIT_ERROR

    body = body_path.read_text() if plat == PLATFORM_GITLAB else ""
    cmd = build_issue_create_cmd(
        plat, args.title, str(body_path), body, args.label, args.repo
    )
    result = _run(cmd)

    if result.returncode != 0:
        sys.stderr.write(result.stderr or result.stdout)
        return EXIT_ERROR

    url_match = re.search(r"https?://\S+/issues?/\d+", result.stdout) or re.search(
        r"https?://\S+", result.stdout
    )
    if not url_match:
        sys.stderr.write(
            f"error: could not extract issue URL from output:\n{result.stdout}\n"
        )
        return EXIT_ERROR
    print(url_match.group(0))
    sys.stderr.write(f"created on {plat}\n")
    return EXIT_OK


def cmd_issue_view(args):
    plat = resolve_platform(args.platform)
    if plat == PLATFORM_UNKNOWN:
        sys.stderr.write("error: cannot detect platform from git remote origin\n")
        return EXIT_PLATFORM_UNKNOWN
    n = args.number
    if plat == PLATFORM_GITHUB:
        result = _call_gh(
            ["issue", "view", str(n), "--json", "number,title,body,url,labels"]
        )
    else:
        result = _call_glab(["issue", "view", str(n), "-F", "json"])
    if result.returncode != 0:
        sys.stderr.write(result.stderr or result.stdout)
        return EXIT_ERROR
    try:
        raw = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"error: cannot parse {plat} issue view output: {e}\n")
        return EXIT_ERROR
    print(json.dumps(normalize_issue(raw, plat), ensure_ascii=False, indent=2))
    return EXIT_OK


def build_label_list_cmd(platform, repo):
    """Build the gh/glab label-list argv (pure, no execution).

    `repo` (owner/name slug) lists labels of a repo other than cwd's origin —
    used by `/finish` to validate distillation labels against the *target*
    (cross) repo before creating the issue, so a wrong label name fails fast
    at selection time instead of aborting `gh issue create` mid-flight.
    """
    if platform == PLATFORM_GITHUB:
        cmd = ["gh", "label", "list", "--json", "name", "-q", ".[].name"]
    else:
        cmd = ["glab", "label", "list", "--output", "json"]
    if repo:
        cmd += ["--repo", repo]
    return cmd


def cmd_label_list(args):
    plat = resolve_platform(args.platform)
    if plat == PLATFORM_UNKNOWN:
        sys.stderr.write("error: cannot detect platform from git remote origin\n")
        return EXIT_PLATFORM_UNKNOWN
    result = _run(build_label_list_cmd(plat, args.repo))
    if plat == PLATFORM_GITHUB:
        if result.returncode != 0:
            sys.stderr.write(result.stderr)
            return EXIT_ERROR
        sys.stdout.write(result.stdout)
        return EXIT_OK
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        return EXIT_ERROR
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"error: cannot parse glab label list output: {e}\n")
        return EXIT_ERROR
    for entry in data:
        print(entry.get("name", ""))
    return EXIT_OK


def cmd_label_sync_from_file(args):
    plat = resolve_platform(args.platform)
    if plat == PLATFORM_UNKNOWN:
        sys.stderr.write(
            "error: cannot detect platform from git remote origin; skipping label sync\n"
        )
        return EXIT_PLATFORM_UNKNOWN

    yml_path = Path(args.path)
    if not yml_path.exists():
        sys.stderr.write(f"error: yml file not found: {yml_path}\n")
        return EXIT_ERROR

    items = parse_labels_yml(yml_path.read_text())
    if not items:
        sys.stderr.write(f"error: parsed 0 labels from {yml_path}\n")
        return EXIT_ERROR

    synced = 0
    errored = 0

    if plat == PLATFORM_GITHUB:
        for entry in items:
            name = entry.get("name", "")
            color = normalize_color(entry.get("color", ""), plat)
            desc = entry.get("description", "")
            r = _run(
                [
                    "gh",
                    "label",
                    "create",
                    "--force",
                    name,
                    "--color",
                    color,
                    "--description",
                    desc,
                ]
            )
            if r.returncode == 0:
                print(f"synced\t{name}")
                synced += 1
            else:
                msg = (r.stderr or r.stdout).strip().splitlines()[:1]
                msg = msg[0] if msg else "unknown error"
                print(f"error\t{name}\t{msg}")
                errored += 1
    else:
        # GitLab: list existing → build name→id map → create or edit per entry
        name_to_id = {}
        list_r = _call_glab(["label", "list", "--output", "json"])
        if list_r.returncode == 0:
            try:
                for entry in json.loads(list_r.stdout):
                    name_to_id[entry.get("name", "")] = entry.get("id")
            except json.JSONDecodeError:
                pass
        else:
            sys.stderr.write(
                f"warning: glab label list failed; will only attempt create:\n{list_r.stderr}"
            )

        for entry in items:
            name = entry.get("name", "")
            color = normalize_color(entry.get("color", ""), plat)
            desc = entry.get("description", "")
            if name in name_to_id and name_to_id[name] is not None:
                cmd = [
                    "glab",
                    "label",
                    "edit",
                    "-l",
                    str(name_to_id[name]),
                    "-c",
                    color,
                    "-d",
                    desc,
                ]
            else:
                cmd = [
                    "glab",
                    "label",
                    "create",
                    "-n",
                    name,
                    "-c",
                    color,
                    "-d",
                    desc,
                ]
            r = _run(cmd)
            if r.returncode == 0:
                print(f"synced\t{name}")
                synced += 1
            else:
                msg = (r.stderr or r.stdout).strip().splitlines()[:1]
                msg = msg[0] if msg else "unknown error"
                print(f"error\t{name}\t{msg}")
                errored += 1

    print(f"summary: {synced} synced, {errored} error")
    return EXIT_OK if errored == 0 else EXIT_ERROR


# ---------------------------------------------------------------- self-test


def cmd_self_test():
    failures = []

    sample_yml = """---
# top-level comment
- name: "type:feat"
  color: "0E8A16"
  description: "新功能"
- name: "type:bug"
  color: "B60205"
  description: "BUG"  # trailing comment
- name: 'priority:P0'
  color: '#D93F0B'
  description: 必须做
"""
    parsed = parse_labels_yml(sample_yml)
    expected = [
        {"name": "type:feat", "color": "0E8A16", "description": "新功能"},
        {"name": "type:bug", "color": "B60205", "description": "BUG"},
        {"name": "priority:P0", "color": "#D93F0B", "description": "必须做"},
    ]
    if parsed != expected:
        failures.append(f"yml parser: parsed={parsed!r}")

    gl_raw = {
        "iid": 7,
        "title": "T",
        "description": "D",
        "web_url": "https://gl.com/x/y/-/issues/7",
        "labels": ["a", "b"],
    }
    norm_gl = normalize_issue(gl_raw, PLATFORM_GITLAB)
    if norm_gl != {
        "number": 7,
        "title": "T",
        "body": "D",
        "url": "https://gl.com/x/y/-/issues/7",
        "labels": ["a", "b"],
    }:
        failures.append(f"normalize_issue gitlab: {norm_gl!r}")

    gh_raw = {
        "number": 7,
        "title": "T",
        "body": "D",
        "url": "https://gh.com/x/y/issues/7",
        "labels": [{"name": "a"}, {"name": "b"}],
    }
    norm_gh = normalize_issue(gh_raw, PLATFORM_GITHUB)
    if norm_gh != {
        "number": 7,
        "title": "T",
        "body": "D",
        "url": "https://gh.com/x/y/issues/7",
        "labels": ["a", "b"],
    }:
        failures.append(f"normalize_issue github: {norm_gh!r}")

    color_cases = [
        ("0E8A16", PLATFORM_GITHUB, "0E8A16"),
        ("0E8A16", PLATFORM_GITLAB, "#0E8A16"),
        ("#0E8A16", PLATFORM_GITHUB, "0E8A16"),
        ("#0E8A16", PLATFORM_GITLAB, "#0E8A16"),
        ("", PLATFORM_GITHUB, ""),
        ("", PLATFORM_GITLAB, "#"),
    ]
    for raw, plat, expected_c in color_cases:
        got = normalize_color(raw, plat)
        if got != expected_c:
            failures.append(
                f"normalize_color({raw!r}, {plat}) = {got!r}, want {expected_c!r}"
            )

    create_cmd_cases = [
        (
            (PLATFORM_GITHUB, "T", "/tmp/b.md", "BODY", [], None),
            ["gh", "issue", "create", "--title", "T", "--body-file", "/tmp/b.md"],
        ),
        (
            (
                PLATFORM_GITHUB,
                "T",
                "/tmp/b.md",
                "BODY",
                ["type:feat", "area:skill"],
                "o/x",
            ),
            [
                "gh",
                "issue",
                "create",
                "--title",
                "T",
                "--body-file",
                "/tmp/b.md",
                "--repo",
                "o/x",
                "--label",
                "type:feat",
                "--label",
                "area:skill",
            ],
        ),
        (
            (PLATFORM_GITLAB, "T", "/tmp/b.md", "BODY", ["type:feat"], "o/x"),
            [
                "glab",
                "issue",
                "create",
                "--title",
                "T",
                "--description",
                "BODY",
                "--yes",
                "--repo",
                "o/x",
                "--label",
                "type:feat",
            ],
        ),
        (
            (PLATFORM_GITLAB, "T", "/tmp/b.md", "BODY", [], None),
            [
                "glab",
                "issue",
                "create",
                "--title",
                "T",
                "--description",
                "BODY",
                "--yes",
            ],
        ),
    ]
    for (plat, title, bf, body, labels, repo), expected_cmd in create_cmd_cases:
        got_cmd = build_issue_create_cmd(plat, title, bf, body, labels, repo)
        if got_cmd != expected_cmd:
            failures.append(
                f"build_issue_create_cmd({plat}, repo={repo!r}): {got_cmd!r} != {expected_cmd!r}"
            )

    # 跨仓库零-label 护栏：跨仓库(--repo)创建必须带 label，除非显式逃生
    guard_cases = [
        # (repo, labels, allow_no_label) -> should_block(bool)
        (("o/x", [], False), True),  # 跨仓库零 label → 拦截（#12 场景）
        (("o/x", ["type:feat"], False), False),  # 跨仓库有 label → 放行
        (("o/x", [], True), False),  # 显式逃生舱 → 放行
        ((None, [], False), False),  # in-repo（backlog/start）→ 不受护栏约束
    ]
    for (repo, labels, allow), should_block in guard_cases:
        err = cross_repo_label_guard_error(repo, labels, allow)
        if bool(err) != should_block:
            failures.append(
                f"cross_repo_label_guard_error(repo={repo!r}, labels={labels!r}, "
                f"allow={allow}) -> {err!r}, should_block={should_block}"
            )

    label_list_cmd_cases = [
        (
            (PLATFORM_GITHUB, None),
            ["gh", "label", "list", "--json", "name", "-q", ".[].name"],
        ),
        (
            (PLATFORM_GITHUB, "o/x"),
            [
                "gh",
                "label",
                "list",
                "--json",
                "name",
                "-q",
                ".[].name",
                "--repo",
                "o/x",
            ],
        ),
        (
            (PLATFORM_GITLAB, None),
            ["glab", "label", "list", "--output", "json"],
        ),
        (
            (PLATFORM_GITLAB, "o/x"),
            ["glab", "label", "list", "--output", "json", "--repo", "o/x"],
        ),
    ]
    for (plat, repo), expected_cmd in label_list_cmd_cases:
        got_cmd = build_label_list_cmd(plat, repo)
        if got_cmd != expected_cmd:
            failures.append(
                f"build_label_list_cmd({plat}, repo={repo!r}): {got_cmd!r} != {expected_cmd!r}"
            )

    if failures:
        for f in failures:
            print(f"FAIL: {f}", file=sys.stderr)
        return EXIT_ERROR
    print("self-test: OK")
    return EXIT_OK


# ---------------------------------------------------------------- argparse


def build_parser():
    p = argparse.ArgumentParser(prog="platform_issue.py", description=__doc__)
    p.add_argument(
        "--platform",
        choices=[PLATFORM_GITHUB, PLATFORM_GITLAB],
        default=None,
        help="Override platform detection (default: detect via git remote origin)",
    )
    p.add_argument(
        "--debug", action="store_true", help="Print internal CLI calls to stderr"
    )
    p.add_argument("--self-test", action="store_true", help=argparse.SUPPRESS)

    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("detect-platform")
    sub.add_parser("auth-status")
    sub.add_parser("repo-slug")
    p_label_list = sub.add_parser("label-list")
    p_label_list.add_argument(
        "--repo",
        default=None,
        help="Target repo slug (owner/name) to list labels of a repo other "
        "than cwd's origin; used to validate cross-repo distillation labels",
    )

    p_create = sub.add_parser("issue-create")
    p_create.add_argument("--title", required=True)
    p_create.add_argument("--body-file", required=True)
    p_create.add_argument("--label", action="append", default=[])
    p_create.add_argument(
        "--repo",
        default=None,
        help="Target repo slug (owner/name) for cross-repo issue creation; "
        "combine with --platform to file into a repo other than cwd's origin",
    )
    p_create.add_argument(
        "--allow-no-label",
        action="store_true",
        help="Permit a cross-repo (--repo) issue with zero labels; by default "
        "such a label-less distillation issue is refused",
    )

    p_view = sub.add_parser("issue-view")
    p_view.add_argument("number", type=int)

    p_sync = sub.add_parser("label-sync-from-file")
    p_sync.add_argument("path")

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    global DEBUG
    DEBUG = args.debug

    if args.self_test:
        return cmd_self_test()

    if not args.cmd:
        parser.print_help(sys.stderr)
        return EXIT_ERROR

    handlers = {
        "detect-platform": cmd_detect_platform,
        "auth-status": cmd_auth_status,
        "repo-slug": cmd_repo_slug,
        "issue-create": cmd_issue_create,
        "issue-view": cmd_issue_view,
        "label-list": cmd_label_list,
        "label-sync-from-file": cmd_label_sync_from_file,
    }
    try:
        return handlers[args.cmd](args)
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"error: {e.__class__.__name__}: {e}\n")
        if DEBUG:
            import traceback

            traceback.print_exc(file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
