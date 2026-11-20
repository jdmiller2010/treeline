#!/usr/bin/env python3
"""Checks that nothing that must not be public is committed. The rules are in docs/REPO_RULES.md.

  python3 scripts/check_repo_rules.py                 every tracked file (what ./dev check and CI run)
  python3 scripts/check_repo_rules.py --staged        what is staged for the next commit (the pre-commit hook)
  python3 scripts/check_repo_rules.py --range A..B    also every line those commits ADDED, so a secret that
                                                      was committed and then deleted is still caught (CI on a PR)

Findings print as  path:line: rule: first few characters...  and never the whole value.
Exit status 1 if there is any finding.

Extra deny patterns (the names of a park, a street or a family, which must not be written into a public
repo, not even here) come from .repo-rules.local (gitignored, one regex per line, # for comments) and
from the REPO_RULES_EXTRA environment variable (same format; CI can fill it from a repository secret).

A line that is fine on purpose can say  repo-rules: allow  in a comment.
"""

import argparse
import ipaddress
import math
import os
import re
import subprocess
import sys

ALLOW_MARKER = "repo-rules: allow"
MAX_CONTENT_BYTES = 1_000_000

# Files that must never be tracked at all.
FORBIDDEN_PATHS = [
    (re.compile(r"(^|/)\.env(\.|$)(?!example)"), "an .env file (use deploy/env.example with placeholders)"),
    (re.compile(r"\.(pem|key|p12|pfx|jks|keystore|agekey)$"), "a key or certificate file"),
    (re.compile(r"(^|/)id_(rsa|dsa|ecdsa|ed25519)(\.pub)?$"), "an SSH key"),
    (re.compile(r"\.(db|sqlite|sqlite3)(-wal|-shm|-journal)?$"), "a database file (data holds real families)"),
    (re.compile(r"\.age$"), "an encrypted backup (it holds real families' records)"),
    (re.compile(r"(^|/)(pre-migrate|backups|households)/"), "a household, backup or pre-migration folder (real families' records)"),
    (re.compile(r"(^|/)data/(?!\.gitkeep$)(?!generated/?$)[^/]+"), "something under data/ (it is for the live database and backups)"),
    (re.compile(r"(^|/)infra/\.local/"), "infra/.local (credentials waiting to be installed)"),
    (re.compile(r"(^|/)(cdk\.out/|cdk\.context\.json$)"), "CDK output or its lookup cache (holds account details)"),
    (re.compile(r"\.tfstate(\.backup)?$"), "infrastructure state"),
    (re.compile(r"(^|/)\.?(aws/)?credentials$"), "a credentials file"),
    (re.compile(r"(^|/)\.repo-rules\.local$"), "the local deny-list (it names the things we keep out)"),
]

# Not scanned for content (vendored or generated third-party code is full of false alarms).
SKIP_CONTENT = re.compile(r"(^|/)(vendor/|node_modules/|\.venv[^/]*/)|\.min\.(js|css)$|(^|/)(package-lock\.json|yarn\.lock)$")
BINARY_EXT = re.compile(r"\.(png|jpe?g|gif|ico|webp|woff2?|ttf|otf|wav|mp3|ogg|ulaw|alaw|gsm|sln\d*|pdf|zip|gz|tar|bin)$", re.I)

# Addresses that are fine to publish.
ALLOWED_EMAILS = {"jdmiller2010@gmail.com"}
ALLOWED_EMAIL_DOMAINS = {"example.com", "example.org", "example.net", "localhost", "treelinephone.com", "users.noreply.github.com"}
RESERVED_TLDS = {"invalid", "test", "example", "localhost"}      # RFC 2606: can never be a real address
TEST_PATHS = re.compile(r"(^|/)tests?/")                         # fixtures may use made-up client addresses
FILE_LIKE_TLDS = {"png", "jpg", "jpeg", "gif", "svg", "webp", "css", "js", "json", "ico", "woff", "woff2", "html", "md", "py", "txt"}

SECRET_WORDS = r"(?:password|passwd|secret|api[_-]?key|token|private[_-]?key)"
PLACEHOLDER_WORDS = ("example", "change", "placeholder", "your", "xxxx", "dummy", "treeline-dev", "replace")

CONTENT_RULES = [
    ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA|AGPA|AIDA|AROA)[0-9A-Z]{16}\b")),
    ("aws-secret-key", re.compile(r"(?i)aws_?secret_?access_?key[\"'\s:=]+[A-Za-z0-9/+=]{40}\b")),
    ("private-key", re.compile(r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----")),
    ("age-secret-key", re.compile(r"AGE-SECRET-KEY-1[A-Z0-9]{20,}")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{40,}\b")),
    ("slack-token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("google-secret", re.compile(r"\bGOCSPX-[A-Za-z0-9_-]{20,}|\bAIza[0-9A-Za-z_-]{35}\b")),
    ("aws-arn-with-account-id", re.compile(r"arn:aws[a-z-]*:[a-z0-9-]+:[a-z0-9-]*:(?!123456789012:|000000000000:)\d{12}:")),
]
GENERIC_SECRET = re.compile(r"(?i)\b[\w.-]*" + SECRET_WORDS + r"[\w.-]*\s*[:=]\s*[\"']?([A-Za-z0-9+/_=-]{20,})")
IPV4 = re.compile(r"(?<![\w.])((?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3})(?![\w.])")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)")


def entropy(s):
    return -sum(s.count(c) / len(s) * math.log2(s.count(c) / len(s)) for c in set(s))


def redact(s):
    return (s[:5] + "…") if len(s) > 5 else "…"


def scan_line(line, extra, path=""):
    """Yield (rule, snippet) for one line of text."""
    if ALLOW_MARKER in line:
        return
    for name, rx in CONTENT_RULES:
        for m in rx.finditer(line):
            yield name, redact(m.group(0))
    for m in GENERIC_SECRET.finditer(line):
        v = m.group(1)
        if (len(v) >= 20 and entropy(v) >= 3.5 and re.search(r"\d", v) and re.search(r"[A-Za-z]", v)
                and not any(w in v.lower() for w in PLACEHOLDER_WORDS)):
            yield "secret-looking-value", redact(v)
    for m in IPV4.finditer(line if not TEST_PATHS.search(path) else ""):
        try:
            if ipaddress.ip_address(m.group(1)).is_global:
                yield "public-ip-address", redact(m.group(1))
        except ValueError:
            pass
    for m in EMAIL.finditer(line):
        domain = m.group(1).lower()
        if (m.group(0).lower() in ALLOWED_EMAILS or domain.rsplit(".", 1)[-1] in FILE_LIKE_TLDS | RESERVED_TLDS
                or any(domain == d or domain.endswith("." + d) for d in ALLOWED_EMAIL_DOMAINS)):
            continue
        yield "email-address", redact(m.group(0))
    for rx in extra:
        m = rx.search(line)
        if m:
            yield "local-deny-list", redact(m.group(0))


def load_extra(root):
    lines = []
    path = os.path.join(root, ".repo-rules.local")
    if os.path.exists(path):
        lines += open(path, encoding="utf-8").read().splitlines()
    lines += os.environ.get("REPO_RULES_EXTRA", "").splitlines()
    return [re.compile(l.strip(), re.I) for l in lines if l.strip() and not l.strip().startswith("#")]


def check_path(path, extra):
    out = []
    for rx, what in FORBIDDEN_PATHS:
        if rx.search(path):
            out.append((path, 0, "forbidden-file", what))
    for rx in extra:
        if rx.search(path):
            out.append((path, 0, "local-deny-list", "in the file name"))
    return out


def scan_text(path, text, extra, first_line=1):
    out = []
    if SKIP_CONTENT.search(path) or BINARY_EXT.search(path):
        return out
    for i, line in enumerate(text.splitlines(), first_line):
        for rule, snip in scan_line(line, extra, path):
            out.append((path, i, rule, snip))
    return out


def git(*args, check=True):
    return subprocess.run(["git", *args], capture_output=True, check=check).stdout


def tracked_files():
    return [p for p in git("ls-files", "-z").decode().split("\0") if p]


def staged_files():
    return [p for p in git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z").decode().split("\0") if p]


def read_blob(path, staged):
    data = git("show", f":{path}") if staged else open(path, "rb").read()
    return None if (b"\0" in data[:8000] or len(data) > MAX_CONTENT_BYTES) else data.decode("utf-8", "replace")


def scan_range(rng, extra):
    """Every line added by the commits in rng (git log -p), so a deleted secret is still found."""
    out, path, lineno = [], None, 0
    log = git("log", "-p", "--format=%x00%h", "--unified=0", "--no-color", "--no-renames", rng).decode("utf-8", "replace")
    commit = ""
    for line in log.splitlines():
        if line.startswith("\0"):
            commit = line[1:]
        elif line.startswith("+++ b/"):
            path = line[6:]
            out += [(f"{path} (commit {commit})", n, r, s) for _, n, r, s in [(path, *f[1:]) for f in check_path(path, extra)]]
        elif line.startswith("@@"):
            m = re.search(r"\+(\d+)", line)
            lineno = int(m.group(1)) if m else 0
        elif line.startswith("+") and not line.startswith("+++") and path:
            if not (SKIP_CONTENT.search(path) or BINARY_EXT.search(path)):
                for rule, snip in scan_line(line[1:], extra, path):
                    out.append((f"{path} (commit {commit})", lineno, rule, snip))
            lineno += 1
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--staged", action="store_true", help="scan what is staged (pre-commit)")
    ap.add_argument("--range", help="also scan the lines added by these commits, e.g. origin/main..HEAD")
    args = ap.parse_args(argv)

    root = git("rev-parse", "--show-toplevel").decode().strip()
    os.chdir(root)
    extra = load_extra(root)
    findings = []
    files = staged_files() if args.staged else tracked_files()
    for path in files:
        findings += check_path(path, extra)
        text = read_blob(path, args.staged)
        if text is not None:
            findings += scan_text(path, text, extra)
    if args.range:
        findings += scan_range(args.range, extra)

    for path, line, rule, snippet in sorted(set(findings)):
        where = f"{path}:{line}" if line else path
        print(f"{where}: {rule}: {snippet}")
    if findings:
        print(f"\n{len(set(findings))} finding(s). If one is a mistake: remove it and, if it was a real secret, rotate it now "
              f"(deleting it from git does not un-leak it). If it is fine on purpose: add '{ALLOW_MARKER}' in a comment on that line. "
              f"Rules: docs/REPO_RULES.md", file=sys.stderr)
        return 1
    print(f"repo rules ok ({len(files)} files{', plus the commits in ' + args.range if args.range else ''}"
          f"{'' if extra else '; no local deny-list loaded'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
