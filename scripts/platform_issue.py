#!/usr/bin/env python3
"""platform_issue.py — cross-platform issue/label/repo helper for backlog/start/bootstrap/sync skills.

Bridges `gh` (GitHub CLI) and `glab` (GitLab CLI) so SKILL.md files don't need
platform branching. Subcommands take a unified shape and emit a unified output
schema (GitHub-flavored field names) regardless of source platform.

See docs/15-三件套skill支持GitLab双轨/PLAN.md for design rationale.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
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


def normalize_comments(raw_comments, platform):
    """Normalize issue comments to {author, authorAssociation, body, createdAt}.

    GitLab returns [] unconditionally: `glab`'s notes capability was never
    verified (it isn't installed on the machine this was written on), and
    guessing a command that "looks right" is exactly how a silently-empty
    result gets shipped. Callers get an explicit not-supported note on stderr
    instead — see cmd_issue_view.
    """
    if platform == PLATFORM_GITLAB:
        return []
    out = []
    for c in raw_comments or []:
        author = c.get("author") or {}
        out.append(
            {
                "author": author.get("login", "") if isinstance(author, dict) else "",
                "authorAssociation": c.get("authorAssociation", "") or "",
                "body": c.get("body", "") or "",
                "createdAt": c.get("createdAt", "") or "",
            }
        )
    return out


def latest_owner_comment(comments):
    """Body of the newest OWNER-authored comment, else None.

    This is `/routine-dev`'s authorization judgement, deliberately pushed down
    into code: this repo is public, so *anyone* can comment on an issue, and
    only `authorAssociation == "OWNER"` proves the mark came from the repo
    owner. COLLABORATOR/CONTRIBUTOR are not enough — they're a weaker grant
    than the `auto:take` label the mark is paired with. Keeping it here (and
    under self-test) beats asking the model to re-derive the check each run.
    """
    for c in reversed(comments or []):
        if c.get("authorAssociation") == "OWNER":
            return c.get("body") or ""
    return None


def normalize_issue(raw, platform, with_comments=False):
    if platform == PLATFORM_GITLAB:
        out = {
            "number": raw.get("iid"),
            "title": raw.get("title", ""),
            "body": raw.get("description") or "",
            "url": raw.get("web_url", ""),
            "labels": list(raw.get("labels", []) or []),
        }
    else:
        labels = raw.get("labels", []) or []
        out = {
            "number": raw.get("number"),
            "title": raw.get("title", ""),
            "body": raw.get("body") or "",
            "url": raw.get("url", ""),
            "labels": [lbl["name"] if isinstance(lbl, dict) else lbl for lbl in labels],
        }
    if with_comments:
        comments = normalize_comments(raw.get("comments"), platform)
        out["comments"] = comments
        out["ownerHint"] = latest_owner_comment(comments)
    return out


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


def build_issue_comment_cmd(platform, number, body_file, body, repo):
    """Build the gh/glab issue-comment argv (pure, no execution).

    The two platforms disagree on both the subcommand name and how the body
    gets in: GitHub reads it from --body-file, GitLab has no such flag and
    takes it inline via -m (so callers pass both the path and the text).
    Papering over that split is exactly why this helper exists — skills must
    not reach for `gh` / `glab` directly.

    Long bodies are safe here: everything is executed as an argv list via
    subprocess (never through a shell), so backticks / $VAR / quotes in the
    markdown are passed through literally with no escaping needed.
    """
    if platform == PLATFORM_GITHUB:
        cmd = ["gh", "issue", "comment", str(number), "--body-file", str(body_file)]
    else:
        cmd = ["glab", "issue", "note", str(number), "-m", body]
    if repo:
        cmd += ["--repo", repo]
    return cmd


def cmd_issue_comment(args):
    plat = resolve_platform(args.platform)
    if plat == PLATFORM_UNKNOWN:
        sys.stderr.write("error: cannot detect platform from git remote origin\n")
        return EXIT_PLATFORM_UNKNOWN
    body_path = Path(args.body_file)
    if not body_path.exists():
        sys.stderr.write(f"error: body file not found: {body_path}\n")
        return EXIT_ERROR

    body = body_path.read_text() if plat == PLATFORM_GITLAB else ""
    result = _run(
        build_issue_comment_cmd(plat, args.issue, str(body_path), body, args.repo)
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr or result.stdout)
        return EXIT_ERROR

    url_match = re.search(r"https?://\S+", result.stdout)
    if url_match:
        print(url_match.group(0))
    else:
        # The comment *did* post (returncode 0); only the URL is unavailable.
        # glab's `issue note` output schema is unverified, so failing here
        # would turn a successful side effect into a spurious error.
        sys.stderr.write(f"warn: comment posted on {plat} but no URL found in output\n")
    return EXIT_OK


def build_issue_label_cmd(platform, number, labels, remove, repo):
    """Build the gh/glab argv that adds or removes labels on an issue (pure).

    The two platforms disagree on the subcommand *and* on both flag names
    (`issue edit --add-label/--remove-label` vs `issue update
    --label/--unlabel`), which is the usual reason a caller must come through
    this helper instead of reaching for the CLI.

    Each label gets its own flag rather than one comma-joined value: a label
    name may itself contain a comma, and joining would have the platform
    split it into two names that exist nowhere.

    Semantics are incremental on both ends — the labels already on the issue
    are left alone. That matters for the `auto:skip` writer in /routine-dev:
    a replace-style call would silently drop the three-axis labels.

    GitLab side is unverified (no `glab` on the dev machine) — see
    scripts/platform_issue.md.
    """
    if platform == PLATFORM_GITHUB:
        flag = "--remove-label" if remove else "--add-label"
        cmd = ["gh", "issue", "edit", str(number)]
    else:
        flag = "--unlabel" if remove else "--label"
        cmd = ["glab", "issue", "update", str(number)]
    for label in labels:
        cmd += [flag, label]
    if repo:
        cmd += ["--repo", repo]
    return cmd


def _cmd_issue_label(args, remove):
    plat = resolve_platform(args.platform)
    if plat == PLATFORM_UNKNOWN:
        sys.stderr.write("error: cannot detect platform from git remote origin\n")
        return EXIT_PLATFORM_UNKNOWN
    result = _run(
        build_issue_label_cmd(plat, args.issue, args.label, remove, args.repo)
    )
    if result.returncode != 0:
        # 原样透传底层错误：打标是为了持久化一个判断，谎报成功比失败更坏
        sys.stderr.write(result.stderr or result.stdout)
        return EXIT_ERROR
    verb = "removed" if remove else "added"
    print(f"{verb} on {plat}: #{args.issue} {' '.join(args.label)}")
    return EXIT_OK


def cmd_issue_label_add(args):
    return _cmd_issue_label(args, remove=False)


def cmd_issue_label_remove(args):
    return _cmd_issue_label(args, remove=True)


def build_issue_view_cmd(platform, number, with_comments=False):
    """Build the gh/glab issue-view argv (pure, no execution).

    `with_comments` only widens GitHub's --json field list; the default field
    set is untouched so existing consumers (/start et al.) see the exact same
    schema they always have.
    """
    if platform == PLATFORM_GITHUB:
        fields = "number,title,body,url,labels"
        if with_comments:
            fields += ",comments"
        return ["gh", "issue", "view", str(number), "--json", fields]
    return ["glab", "issue", "view", str(number), "-F", "json"]


def cmd_issue_view(args):
    plat = resolve_platform(args.platform)
    if plat == PLATFORM_UNKNOWN:
        sys.stderr.write("error: cannot detect platform from git remote origin\n")
        return EXIT_PLATFORM_UNKNOWN
    n = args.number
    with_comments = getattr(args, "with_comments", False)
    if with_comments and plat == PLATFORM_GITLAB:
        sys.stderr.write(
            "note: --with-comments is not supported on gitlab; "
            "comments will be empty (glab notes capability unverified)\n"
        )
    result = _run(build_issue_view_cmd(plat, n, with_comments))
    if result.returncode != 0:
        sys.stderr.write(result.stderr or result.stdout)
        return EXIT_ERROR
    try:
        raw = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"error: cannot parse {plat} issue view output: {e}\n")
        return EXIT_ERROR
    print(
        json.dumps(
            normalize_issue(raw, plat, with_comments), ensure_ascii=False, indent=2
        )
    )
    return EXIT_OK


def build_issue_list_cmd(platform, limit, repo):
    """Build the gh/glab issue-list argv (pure, no execution).

    Emits the same field set as issue-view so both subcommands normalize into
    one schema — consumers (/triage) read `labels` for the priority axis and
    `body` for the scope field without caring which platform answered.
    Only open issues: the sole consumer is "what should I pick up next".
    """
    if platform == PLATFORM_GITHUB:
        cmd = [
            "gh",
            "issue",
            "list",
            "--state",
            "open",
            "--limit",
            str(limit),
            "--json",
            "number,title,body,url,labels",
        ]
    else:
        cmd = ["glab", "issue", "list", "--output", "json", "--per-page", str(limit)]
    if repo:
        cmd += ["--repo", repo]
    return cmd


def cmd_issue_list(args):
    plat = resolve_platform(args.platform)
    if plat == PLATFORM_UNKNOWN:
        sys.stderr.write("error: cannot detect platform from git remote origin\n")
        return EXIT_PLATFORM_UNKNOWN
    result = _run(build_issue_list_cmd(plat, args.limit, args.repo))
    if result.returncode != 0:
        sys.stderr.write(result.stderr or result.stdout)
        return EXIT_ERROR
    try:
        raw = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"error: cannot parse {plat} issue list output: {e}\n")
        return EXIT_ERROR
    if not isinstance(raw, list):
        sys.stderr.write(f"error: expected a json array from {plat} issue list\n")
        return EXIT_ERROR
    print(
        json.dumps(
            [normalize_issue(r, plat) for r in raw], ensure_ascii=False, indent=2
        )
    )
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


def _sandbox_issue_comment():
    """Sandbox `issue-comment` end-to-end with stubbed gh/glab CLIs.

    Follows playbooks/shell.md §4: stub the external CLI, put it on PATH, and
    assert on the *real argv the stub received* rather than on what we printed.
    The long-body case is the point — GitLab passes the markdown inline via
    -m, and that path is where quoting/length problems would show up.
    """
    failures = []
    body = "标题`反引号` $HOME \"引号\" 'single'\n\n```sh\necho $PATH\n```\n" * 300

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        argv_log = tmp / "argv.log"
        body_file = tmp / "body.md"
        body_file.write_text(body)

        # 桩把 argv 原样存成 JSON —— 正文本身含换行，按行存会把一个参数拆成好几个
        for name, url in (("gh", "https://gh.test/x/y/issues/7#note_1"), ("glab", "")):
            stub = tmp / name
            stub.write_text(
                "#!/usr/bin/env python3\n"
                "import json, sys, pathlib\n"
                f"pathlib.Path({str(argv_log)!r}).write_text("
                "json.dumps(sys.argv))\n"
                f"print({url!r})\n"
            )
            stub.chmod(0o755)

        env_path = f"{tmp}{os.pathsep}{os.environ.get('PATH', '')}"
        base = [sys.executable, str(Path(__file__).resolve()), "--platform"]

        cases = [
            (
                PLATFORM_GITHUB,
                ["gh", "issue", "comment", "7", "--body-file", str(body_file)],
            ),
            (PLATFORM_GITLAB, ["glab", "issue", "note", "7", "-m", body]),
        ]
        for plat, want_argv in cases:
            proc = subprocess.run(
                base
                + [
                    plat,
                    "issue-comment",
                    "--issue",
                    "7",
                    "--body-file",
                    str(body_file),
                ],
                capture_output=True,
                text=True,
                env={**os.environ, "PATH": env_path},
            )
            if proc.returncode != EXIT_OK:
                failures.append(
                    f"sandbox issue-comment {plat}: exit {proc.returncode}, "
                    f"stderr={proc.stderr.strip()!r}"
                )
                continue
            got_argv = json.loads(argv_log.read_text())
            # argv[0] 是桩的解析后全路径，取 basename 才能与期望的裸命令名比
            got_argv[0] = Path(got_argv[0]).name
            if got_argv != want_argv:
                # 只报差异位置，长正文整段打出来没法看
                diff = next(
                    (
                        f"[{i}] {g!r} != {w!r}"
                        for i, (g, w) in enumerate(zip(got_argv, want_argv))
                        if g != w
                    ),
                    f"len {len(got_argv)} != {len(want_argv)}",
                )
                failures.append(f"sandbox issue-comment {plat} argv mismatch: {diff}")

        # 正文文件不存在 → 明确报错，不静默发空评论
        proc = subprocess.run(
            base
            + [
                PLATFORM_GITHUB,
                "issue-comment",
                "--issue",
                "7",
                "--body-file",
                str(tmp / "nope.md"),
            ],
            capture_output=True,
            text=True,
            env={**os.environ, "PATH": env_path},
        )
        if proc.returncode != EXIT_ERROR:
            failures.append(
                f"sandbox issue-comment missing body-file: exit {proc.returncode}, want {EXIT_ERROR}"
            )

    return failures


def _sandbox_issue_label():
    """Sandbox `issue-label-add` / `-remove` end-to-end with stubbed gh/glab.

    Pins two things the pure argv builder cannot: labels arrive as separate
    repeated flags with spaces / CJK intact, and a non-zero exit from the
    underlying CLI surfaces as EXIT_ERROR. The second matters more than it
    looks — /routine-dev writes this label to persist a triage verdict, so a
    failed write reported as success would leave it re-reading the same issue
    bodies every run while believing the mark had landed.
    """
    failures = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        argv_log = tmp / "argv.log"

        def write_stub(name, exit_code=0, stderr=""):
            stub = tmp / name
            stub.write_text(
                "#!/usr/bin/env python3\n"
                "import json, sys, pathlib\n"
                f"pathlib.Path({str(argv_log)!r}).write_text(json.dumps(sys.argv))\n"
                f"sys.stderr.write({stderr!r})\n"
                f"sys.exit({exit_code})\n"
            )
            stub.chmod(0o755)

        env_path = f"{tmp}{os.pathsep}{os.environ.get('PATH', '')}"
        base = [sys.executable, str(Path(__file__).resolve()), "--platform"]

        cases = [
            (
                PLATFORM_GITHUB,
                [
                    "issue-label-add",
                    "--issue",
                    "7",
                    "--label",
                    "auto:skip",
                    "--label",
                    "help wanted",
                ],
                [
                    "gh",
                    "issue",
                    "edit",
                    "7",
                    "--add-label",
                    "auto:skip",
                    "--add-label",
                    "help wanted",
                ],
            ),
            (
                PLATFORM_GITLAB,
                ["issue-label-remove", "--issue", "7", "--label", "auto:skip"],
                ["glab", "issue", "update", "7", "--unlabel", "auto:skip"],
            ),
        ]
        for plat, argv_in, want_argv in cases:
            write_stub("gh")
            write_stub("glab")
            proc = subprocess.run(
                base + [plat] + argv_in,
                capture_output=True,
                text=True,
                env={**os.environ, "PATH": env_path},
            )
            if proc.returncode != EXIT_OK:
                failures.append(
                    f"sandbox {argv_in[0]} {plat}: exit {proc.returncode}, "
                    f"stderr={proc.stderr.strip()!r}"
                )
                continue
            got_argv = json.loads(argv_log.read_text())
            got_argv[0] = Path(got_argv[0]).name
            if got_argv != want_argv:
                failures.append(
                    f"sandbox {argv_in[0]} {plat} argv: {got_argv!r} != {want_argv!r}"
                )

        # 底层 CLI 非零退出必须透传：打标失败却报成功，会让 routine 以为
        # 结论已持久化，下次照样把同一批正文重读一遍
        write_stub("gh", exit_code=1, stderr="HTTP 403: Resource not accessible\n")
        proc = subprocess.run(
            base
            + [
                PLATFORM_GITHUB,
                "issue-label-add",
                "--issue",
                "7",
                "--label",
                "auto:skip",
            ],
            capture_output=True,
            text=True,
            env={**os.environ, "PATH": env_path},
        )
        if proc.returncode != EXIT_ERROR:
            failures.append(
                f"sandbox issue-label-add 失败透传: exit {proc.returncode}, want {EXIT_ERROR}"
            )
        if "403" not in proc.stderr:
            failures.append(f"sandbox issue-label-add 失败 stderr 未透传: {proc.stderr!r}")

        # 缺 --label 必须被拒，不许对平台发一次空的 label 编辑
        write_stub("gh")
        proc = subprocess.run(
            base + [PLATFORM_GITHUB, "issue-label-add", "--issue", "7"],
            capture_output=True,
            text=True,
            env={**os.environ, "PATH": env_path},
        )
        if proc.returncode == EXIT_OK:
            failures.append("sandbox issue-label-add 缺 --label 应当拒绝")

    return failures


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

    # issue-comment：两端子命令名与正文传入方式都不同，是 helper 存在的理由本身
    long_body = '行首`反引号` $VAR "双引号"\n\n```python\nx = 1\n```\n' * 200
    comment_cmd_cases = [
        (
            (PLATFORM_GITHUB, 7, "/tmp/c.md", "BODY", None),
            ["gh", "issue", "comment", "7", "--body-file", "/tmp/c.md"],
        ),
        (
            (PLATFORM_GITHUB, 7, "/tmp/c.md", "BODY", "o/x"),
            [
                "gh",
                "issue",
                "comment",
                "7",
                "--body-file",
                "/tmp/c.md",
                "--repo",
                "o/x",
            ],
        ),
        (
            (PLATFORM_GITLAB, 7, "/tmp/c.md", "BODY", None),
            ["glab", "issue", "note", "7", "-m", "BODY"],
        ),
        (
            (PLATFORM_GITLAB, 7, "/tmp/c.md", "BODY", "o/x"),
            ["glab", "issue", "note", "7", "-m", "BODY", "--repo", "o/x"],
        ),
        # 长正文 + shell 元字符：走 argv 不经 shell，必须原样落在参数里
        (
            (PLATFORM_GITLAB, 7, "/tmp/c.md", long_body, None),
            ["glab", "issue", "note", "7", "-m", long_body],
        ),
    ]
    for (plat, num, bf, body, repo), expected_cmd in comment_cmd_cases:
        got_cmd = build_issue_comment_cmd(plat, num, bf, body, repo)
        if got_cmd != expected_cmd:
            failures.append(
                f"build_issue_comment_cmd({plat}, repo={repo!r}): "
                f"{got_cmd!r} != {expected_cmd!r}"
            )

    # issue-label-add / -remove：两端连子命令名带 flag 名都不同（edit/--add-label
    # 对 update/--label），且**每个 label 各带一次 flag** —— 拼成 "a,b" 会让名字里
    # 本来就含逗号的 label 被平台侧拆成两个。
    label_cmd_cases = [
        (
            (PLATFORM_GITHUB, 7, ["auto:skip"], False, None),
            ["gh", "issue", "edit", "7", "--add-label", "auto:skip"],
        ),
        (
            (PLATFORM_GITHUB, 7, ["auto:skip", "type:docs"], False, None),
            [
                "gh",
                "issue",
                "edit",
                "7",
                "--add-label",
                "auto:skip",
                "--add-label",
                "type:docs",
            ],
        ),
        (
            (PLATFORM_GITHUB, 7, ["auto:skip"], True, None),
            ["gh", "issue", "edit", "7", "--remove-label", "auto:skip"],
        ),
        (
            (PLATFORM_GITHUB, 7, ["auto:skip"], False, "o/x"),
            [
                "gh",
                "issue",
                "edit",
                "7",
                "--add-label",
                "auto:skip",
                "--repo",
                "o/x",
            ],
        ),
        (
            (PLATFORM_GITLAB, 7, ["auto:skip"], False, None),
            ["glab", "issue", "update", "7", "--label", "auto:skip"],
        ),
        (
            (PLATFORM_GITLAB, 7, ["auto:skip"], True, "o/x"),
            [
                "glab",
                "issue",
                "update",
                "7",
                "--unlabel",
                "auto:skip",
                "--repo",
                "o/x",
            ],
        ),
        # label 名里的空格 / 中文原样进 argv（不经 shell，无需转义）
        (
            (PLATFORM_GITHUB, 7, ["help wanted", "待确认"], False, None),
            [
                "gh",
                "issue",
                "edit",
                "7",
                "--add-label",
                "help wanted",
                "--add-label",
                "待确认",
            ],
        ),
    ]
    for (plat, num, labels, remove, repo), expected_cmd in label_cmd_cases:
        got_cmd = build_issue_label_cmd(plat, num, labels, remove, repo)
        if got_cmd != expected_cmd:
            failures.append(
                f"build_issue_label_cmd({plat}, remove={remove}, repo={repo!r}): "
                f"{got_cmd!r} != {expected_cmd!r}"
            )

    list_cmd_cases = [
        (
            (PLATFORM_GITHUB, 100, None),
            [
                "gh",
                "issue",
                "list",
                "--state",
                "open",
                "--limit",
                "100",
                "--json",
                "number,title,body,url,labels",
            ],
        ),
        (
            (PLATFORM_GITHUB, 30, "o/x"),
            [
                "gh",
                "issue",
                "list",
                "--state",
                "open",
                "--limit",
                "30",
                "--json",
                "number,title,body,url,labels",
                "--repo",
                "o/x",
            ],
        ),
        (
            (PLATFORM_GITLAB, 100, None),
            ["glab", "issue", "list", "--output", "json", "--per-page", "100"],
        ),
        (
            (PLATFORM_GITLAB, 30, "o/x"),
            [
                "glab",
                "issue",
                "list",
                "--output",
                "json",
                "--per-page",
                "30",
                "--repo",
                "o/x",
            ],
        ),
    ]
    for (plat, limit, repo), expected_cmd in list_cmd_cases:
        got_cmd = build_issue_list_cmd(plat, limit, repo)
        if got_cmd != expected_cmd:
            failures.append(
                f"build_issue_list_cmd({plat}, limit={limit}, repo={repo!r}): "
                f"{got_cmd!r} != {expected_cmd!r}"
            )

    # issue-list 归一：两端逐条复用 normalize_issue，schema 与 issue-view 对齐
    gl_list_raw = [
        {
            "iid": 3,
            "title": "T3",
            "description": "D3",
            "web_url": "https://gl/x/-/issues/3",
            "labels": ["priority:P0"],
        }
    ]
    norm_list = [normalize_issue(r, PLATFORM_GITLAB) for r in gl_list_raw]
    if norm_list != [
        {
            "number": 3,
            "title": "T3",
            "body": "D3",
            "url": "https://gl/x/-/issues/3",
            "labels": ["priority:P0"],
        }
    ]:
        failures.append(f"issue-list gitlab normalize: {norm_list!r}")

    # 沙盘：桩掉 gh / glab，断言**真实传参**而非日志字符串（playbooks/shell.md §4）
    failures.extend(_sandbox_issue_comment())
    failures.extend(_sandbox_issue_label())

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

    issue_view_cmd_cases = [
        (
            (PLATFORM_GITHUB, 7, False),
            ["gh", "issue", "view", "7", "--json", "number,title,body,url,labels"],
        ),
        (
            (PLATFORM_GITHUB, 7, True),
            [
                "gh",
                "issue",
                "view",
                "7",
                "--json",
                "number,title,body,url,labels,comments",
            ],
        ),
        ((PLATFORM_GITLAB, 7, False), ["glab", "issue", "view", "7", "-F", "json"]),
        ((PLATFORM_GITLAB, 7, True), ["glab", "issue", "view", "7", "-F", "json"]),
    ]
    for (plat, num, with_c), expected_cmd in issue_view_cmd_cases:
        got_cmd = build_issue_view_cmd(plat, num, with_c)
        if got_cmd != expected_cmd:
            failures.append(
                f"build_issue_view_cmd({plat}, {num}, with_comments={with_c}): "
                f"{got_cmd!r} != {expected_cmd!r}"
            )

    gh_comments_raw = [
        {
            "author": {"login": "outsider"},
            "authorAssociation": "NONE",
            "body": "任何人都能发这条",
            "createdAt": "2026-08-01T00:00:00Z",
        },
        {
            "author": {"login": "pkulijing"},
            "authorAssociation": "OWNER",
            "body": "第一条 owner 说明",
            "createdAt": "2026-08-02T00:00:00Z",
        },
        {
            "author": {"login": "pkulijing"},
            "authorAssociation": "OWNER",
            "body": "改主意了，按这条来",
            "createdAt": "2026-08-03T00:00:00Z",
        },
        {
            "author": {},
            "body": "缺字段的畸形评论",
        },
    ]
    norm_c = normalize_comments(gh_comments_raw, PLATFORM_GITHUB)
    if len(norm_c) != 4 or norm_c[0] != {
        "author": "outsider",
        "authorAssociation": "NONE",
        "body": "任何人都能发这条",
        "createdAt": "2026-08-01T00:00:00Z",
    }:
        failures.append(f"normalize_comments github: {norm_c!r}")
    if norm_c[3] != {
        "author": "",
        "authorAssociation": "",
        "body": "缺字段的畸形评论",
        "createdAt": "",
    }:
        failures.append(f"normalize_comments 缺字段容错: {norm_c[3]!r}")
    if normalize_comments(gh_comments_raw, PLATFORM_GITLAB) != []:
        failures.append(
            "normalize_comments gitlab 应返回空列表（glab notes 能力未实测）"
        )

    # owner 背书提取：只认 OWNER、取最新一条 —— /routine-dev 的授权判据，
    # 下沉到代码是为了让它被单测覆盖，而不是靠模型每次自觉过滤身份。
    owner_hint_cases = [
        (norm_c, "改主意了，按这条来"),  # 多条 OWNER → 取最后一条
        ([], None),  # 无评论
        (normalize_comments(gh_comments_raw[:1], PLATFORM_GITHUB), None),  # 只有外人
        (
            normalize_comments(
                [
                    {
                        "author": {"login": "helper"},
                        "authorAssociation": "COLLABORATOR",
                        "body": "协作者也不算",
                        "createdAt": "2026-08-01T00:00:00Z",
                    }
                ],
                PLATFORM_GITHUB,
            ),
            None,
        ),
    ]
    for comments, expected_hint in owner_hint_cases:
        got_hint = latest_owner_comment(comments)
        if got_hint != expected_hint:
            failures.append(
                f"latest_owner_comment({comments!r}) = {got_hint!r}, want {expected_hint!r}"
            )

    # 默认 schema 零变化（/start 等既有消费方的回归保护）
    gh_raw_with_c = dict(gh_raw, comments=gh_comments_raw)
    if "comments" in normalize_issue(gh_raw_with_c, PLATFORM_GITHUB):
        failures.append("normalize_issue 默认不应带 comments 字段")
    norm_with_c = normalize_issue(gh_raw_with_c, PLATFORM_GITHUB, with_comments=True)
    if norm_with_c.get("ownerHint") != "改主意了，按这条来":
        failures.append(f"normalize_issue ownerHint: {norm_with_c.get('ownerHint')!r}")
    if len(norm_with_c.get("comments") or []) != 4:
        failures.append(f"normalize_issue comments: {norm_with_c!r}")

    # 两条边界：issue 本来就没有评论、以及 GitLab 端走 with_comments。
    # 二者都不该炸，且都该给出「空但存在」的字段——调用方只读 ownerHint 就够。
    no_comment_cases = [
        (gh_raw, PLATFORM_GITHUB),  # raw 里根本没有 comments 键
        (gl_raw, PLATFORM_GITLAB),  # GitLab 端恒空（glab notes 能力未实测）
    ]
    for raw_case, plat_case in no_comment_cases:
        norm_empty = normalize_issue(raw_case, plat_case, with_comments=True)
        if norm_empty.get("comments") != [] or norm_empty.get("ownerHint") is not None:
            failures.append(
                f"normalize_issue({plat_case}, 无评论) comments/ownerHint: {norm_empty!r}"
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
    p_view.add_argument(
        "--with-comments",
        action="store_true",
        help="additionally emit `comments` and `ownerHint` (newest OWNER comment)",
    )

    p_list = sub.add_parser("issue-list")
    p_list.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Max issues to return (default 100)",
    )
    p_list.add_argument(
        "--repo",
        default=None,
        help="Target repo slug (owner/name) to list issues of a repo other "
        "than cwd's origin",
    )

    p_comment = sub.add_parser("issue-comment")
    p_comment.add_argument("--issue", type=int, required=True)
    p_comment.add_argument("--body-file", required=True)
    p_comment.add_argument(
        "--repo",
        default=None,
        help="Target repo slug (owner/name) to comment on an issue in a repo "
        "other than cwd's origin",
    )

    for name, verb in (("issue-label-add", "add"), ("issue-label-remove", "remove")):
        p_label = sub.add_parser(name)
        p_label.add_argument("--issue", type=int, required=True)
        p_label.add_argument(
            "--label",
            action="append",
            required=True,
            help=f"Label to {verb}; repeat for several. Incremental — labels "
            "already on the issue are untouched",
        )
        p_label.add_argument(
            "--repo",
            default=None,
            help="Target repo slug (owner/name) to label an issue in a repo "
            "other than cwd's origin",
        )

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
        "issue-list": cmd_issue_list,
        "issue-comment": cmd_issue_comment,
        "issue-label-add": cmd_issue_label_add,
        "issue-label-remove": cmd_issue_label_remove,
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
