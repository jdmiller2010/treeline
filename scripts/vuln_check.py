#!/usr/bin/env python3
"""Ask OSV.dev whether anything in the bill of materials has a known vulnerability (or is known malware).

    python3 scripts/sbom.py -o sbom.json && python3 scripts/vuln_check.py sbom.json
    python3 scripts/vuln_check.py sbom.json --report report.md        also write the report as Markdown
    python3 scripts/vuln_check.py sbom.json --os-watch asterisk,caddy  Ubuntu packages whose findings count (see below)
    python3 scripts/vuln_check.py sbom.json --sync-issue               keep one GitHub issue in step with the result (CI)

Exit status: 0 nothing to act on; 1 something to act on; 2 the check itself could not be done (no network, an answer
we could not read, an ignore entry that is malformed or past its date). 2 is deliberately not 0: a scan that did not
run must never look like a clean one.

Three kinds of finding:
  act     a Python, npm, vendored or GitHub Actions component (unless in the ignore file). Fails the run: there is
          almost always a fixed version to move to.
  watch   an Ubuntu package whose source package is named by --os-watch (the daemons that face the internet). A fresh
          install already has Ubuntu's newest build, so an Ubuntu finding means "Ubuntu has no fixed package", and
          Ubuntu lists every CVE ever filed against a package it has not reviewed (76 for its Asterisk on the first
          real run, many of them about versions older than the one it ships). Failing every day on that list would
          teach the owner to ignore the check, so it does not fail the run: the list sits in the issue, and each NEW
          advisory is announced there with a comment. A new advisory is the thing to hear about.
  listed  every other Ubuntu package: in the report, nothing more. unattended-upgrades installs fixes when they exist.

The ignore file (.vuln-ignore, one per line):   <ID>  until=YYYY-MM-DD  why it does not apply to Treeline
An ID matches the advisory or any of its aliases. `until` is required and at most 90 days ahead, so an accepted risk
comes back for another look instead of being forgotten.

Standard library only. It sends package names and versions (all public: this repo is) to api.osv.dev and nothing else.
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

OSV = "https://api.osv.dev"
BATCH = 500
MAX_IGNORE_DAYS = 90
ISSUE_TITLE = "Vulnerability report: something Treeline uses needs attention"
ISSUE_MARK = "<!-- treeline-vuln-ids: %s -->"
BODY_LIMIT = 60000
UBUNTU_ECOSYSTEM = "Ubuntu:24.04:LTS"


class CheckError(Exception):
    """The check could not be completed (exit 2)."""


# ---------------------------------------------------------------- what to ask about
def prop(component, name, default=None):
    for p in component.get("properties", []):
        if p.get("name") == "treeline:" + name:
            return p.get("value")
    return default


def props(component, name):
    return [p.get("value") for p in component.get("properties", []) if p.get("name") == "treeline:" + name]


def queries_for(sbom):
    """[(query, component)]: one OSV query per component we can name exactly. Components we cannot (an action pinned
    only to `@v4`, a container tag) are returned separately so the report says what was NOT checked."""
    asked, skipped = [], []
    for c in sbom.get("components", []):
        eco = prop(c, "ecosystem")
        if eco in ("PyPI", "npm"):
            asked.append(({"package": {"ecosystem": eco, "name": c["name"]}, "version": c["version"]}, c))
        elif eco == "GitHub Actions":
            if prop(c, "exact-version") == "true":
                asked.append(({"package": {"ecosystem": eco, "name": c["name"]}, "version": c["version"]}, c))
            else:
                skipped.append(c)
        elif eco == "Ubuntu":
            source, version = prop(c, "source-package"), prop(c, "source-version")
            if not source or not version:
                raise CheckError("the SBOM's Ubuntu package %s has no source package or version" % c.get("name"))
            asked.append(({"package": {"ecosystem": UBUNTU_ECOSYSTEM, "name": source}, "version": version}, c))
        else:
            skipped.append(c)
    return asked, skipped


# ---------------------------------------------------------------- OSV
def http_json(url, body=None, timeout=60):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", "User-Agent": "treeline-vuln-check"})
    last = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code < 500 and e.code != 429:
                raise CheckError("%s answered HTTP %d: %s" % (url, e.code, e.read()[:300].decode("utf-8", "replace")))
            last = e
        except (urllib.error.URLError, OSError, ValueError) as e:
            last = e
    raise CheckError("could not reach %s after 3 tries: %s" % (url, last))


def query_batch(queries, fetch=None):
    """For each query, the list of advisory ids OSV has for that exact package version. Follows OSV's paging: a
    result with a next_page_token is asked again with that token until it has none."""
    fetch = fetch or http_json
    ids = [[] for _ in queries]
    pending = [(i, dict(q)) for i, q in enumerate(queries)]
    rounds = 0
    while pending:
        rounds += 1
        if rounds > 50:
            raise CheckError("OSV kept returning more pages; giving up rather than report half an answer")
        nxt = []
        for start in range(0, len(pending), BATCH):
            chunk = pending[start:start + BATCH]
            answer = fetch(OSV + "/v1/querybatch", {"queries": [q for _, q in chunk]})
            results = answer.get("results") if isinstance(answer, dict) else None
            if not isinstance(results, list) or len(results) != len(chunk):
                raise CheckError("OSV answered %s results for %d queries" % (len(results) if isinstance(results, list) else "no", len(chunk)))
            for (i, q), res in zip(chunk, results):
                res = res or {}
                for v in res.get("vulns") or []:
                    if not isinstance(v, dict) or not isinstance(v.get("id"), str):
                        raise CheckError("OSV returned an advisory without an id: %r" % (v,))
                    if v["id"] not in ids[i]:
                        ids[i].append(v["id"])
                if res.get("next_page_token"):
                    nxt.append((i, dict(q, page_token=res["next_page_token"])))
        pending = nxt
    return ids


def advisory(vuln_id, fetch=None):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9:._-]*", vuln_id):
        raise CheckError("refusing to look up an oddly named advisory: %r" % vuln_id)
    return (fetch or http_json)(OSV + "/v1/vulns/" + vuln_id)


def severity_of(adv):
    """The advisory's own word for how bad it is, when it has one (GitHub's HIGH/CRITICAL, Ubuntu's priority)."""
    ds = adv.get("database_specific") or {}
    if isinstance(ds.get("severity"), str):
        return ds["severity"].lower()
    for s in adv.get("severity") or []:
        if s.get("type") == "Ubuntu" and isinstance(s.get("score"), str):
            return s["score"].lower()
    for a in adv.get("affected") or []:
        es = a.get("ecosystem_specific") or {}
        for key in ("severity", "ubuntu_priority"):
            if isinstance(es.get(key), str):
                return es[key].lower()
    return "unknown"


def fixed_versions(adv, package_name):
    out = []
    for a in adv.get("affected") or []:
        if (a.get("package") or {}).get("name", "").lower() != package_name.lower():
            continue
        for r in a.get("ranges") or []:
            for e in r.get("events") or []:
                if e.get("fixed") and e["fixed"] not in out:
                    out.append(e["fixed"])
    return out


# ---------------------------------------------------------------- the ignore file
def parse_ignores(text, today):
    """{ID: (until, reason)}. A bad or expired line is an error: an ignore nobody can read or that has run out must
    stop the check, not quietly keep hiding a finding (or quietly stop hiding it without anyone deciding)."""
    out = {}
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.fullmatch(r"(\S+)\s+until=(\d{4}-\d{2}-\d{2})\s+(\S.*)", line)
        if not m:
            raise CheckError(".vuln-ignore line %d: expected `<ID> until=YYYY-MM-DD <reason>`, got %r" % (n, raw))
        try:
            until = datetime.date.fromisoformat(m.group(2))
        except ValueError:
            raise CheckError(".vuln-ignore line %d: %s is not a date" % (n, m.group(2)))
        if until < today:
            raise CheckError(".vuln-ignore line %d: the ignore for %s ran out on %s. Look again: fix it, or renew it with a reason"
                             % (n, m.group(1), until))
        if (until - today).days > MAX_IGNORE_DAYS:
            raise CheckError(".vuln-ignore line %d: %s is more than %d days away; an ignore must come back for review"
                             % (n, until, MAX_IGNORE_DAYS))
        out[m.group(1).upper()] = (until, m.group(3))
    return out


# ---------------------------------------------------------------- the check
def check(sbom, ignores=None, os_watch=(), fetch=None):
    """Returns a dict: findings (each: id, aliases, summary, severity, fixed, component..., status), skipped, counts.
    status is 'act' (fails the run), 'watch' (a watched Ubuntu package: announced, not failed), 'ignored' (in
    .vuln-ignore) or 'listed' (any other Ubuntu package)."""
    ignores = ignores or {}
    os_watch = {w.strip().lower() for w in os_watch if w.strip()}
    asked, skipped = queries_for(sbom)
    ids = query_batch([q for q, _ in asked], fetch)
    cache, findings, used_ignores = {}, [], set()
    for (query, comp), vuln_ids in zip(asked, ids):
        for vid in vuln_ids:
            if vid not in cache:
                cache[vid] = advisory(vid, fetch)
            adv = cache[vid]
            if not isinstance(adv, dict) or adv.get("id") is None:
                raise CheckError("OSV returned no record for %s" % vid)
            if adv.get("withdrawn"):
                continue
            names = [vid] + [a for a in adv.get("aliases") or [] if isinstance(a, str)]
            eco = prop(comp, "ecosystem")
            ignored = next((n for n in names if n.upper() in ignores), None)
            if ignored:
                status = "ignored"
                used_ignores.add(ignored.upper())
            elif eco == "Ubuntu":
                status = "watch" if query["package"]["name"].lower() in os_watch else "listed"
            else:
                status = "act"
            findings.append({
                "id": vid, "aliases": names[1:], "summary": (adv.get("summary") or (adv.get("details") or "").strip().split("\n")[0])[:200],
                "severity": severity_of(adv), "fixed": fixed_versions(adv, query["package"]["name"]),
                "malware": vid.upper().startswith("MAL-"),
                "ecosystem": eco, "package": query["package"]["name"], "version": query["version"],
                "component": comp["name"], "production": prop(comp, "production") == "true",
                "sources": props(comp, "source"), "status": status,
                "ignore_reason": ignores[ignored.upper()][1] if ignored else None,
                "ignore_until": str(ignores[ignored.upper()][0]) if ignored else None,
            })
    # One row per advisory and source package (several Ubuntu binaries share a source package).
    seen, unique = set(), []
    for f in findings:
        key = (f["id"], f["ecosystem"], f["package"], f["version"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(f)
    order = {"act": 0, "watch": 1, "ignored": 2, "listed": 3}
    unique.sort(key=lambda f: (order[f["status"]], not f["malware"], not f["production"], f["ecosystem"], f["package"], f["id"]))
    return {
        "findings": unique, "skipped": skipped, "asked": len(asked),
        "unused_ignores": sorted(set(ignores) - used_ignores),
        "act": [f for f in unique if f["status"] == "act"],
        "watch": [f for f in unique if f["status"] == "watch"],
    }


# ---------------------------------------------------------------- the report
def md(text):
    return str(text).replace("|", "\\|").replace("\n", " ").replace("<", "&lt;")


def report(result, today):
    act, watch = result["act"], result["watch"]
    ignored = [f for f in result["findings"] if f["status"] == "ignored"]
    listed = [f for f in result["findings"] if f["status"] == "listed"]
    lines = ["# Treeline vulnerability report, %s" % today, ""]
    if act:
        lines.append("**%d finding%s to act on.** %d component versions were checked against [OSV.dev](https://osv.dev)."
                     % (len(act), "" if len(act) == 1 else "s", result["asked"]))
    else:
        lines.append("**Nothing to act on.** %d component versions were checked against [OSV.dev](https://osv.dev)." % result["asked"])
    lines.append("")

    def rows(items):
        out = ["| Advisory | Severity | Component | Version | Fixed in | In production | Where | What |", "|---|---|---|---|---|---|---|---|"]
        for f in items:
            out.append("| [%s](https://osv.dev/vulnerability/%s)%s | %s | %s (%s) | %s | %s | %s | %s | %s |" % (
                md(f["id"]), md(f["id"]), (" " + md(", ".join(f["aliases"][:3]))) if f["aliases"] else "",
                "**MALWARE**" if f["malware"] else md(f["severity"]), md(f["package"]), md(f["ecosystem"]), md(f["version"]),
                md(", ".join(f["fixed"]) or "no fix listed"), "yes" if f["production"] else "no",
                md(", ".join(f["sources"])), md(f["summary"])))
        return out

    if act:
        lines += ["## To act on", ""] + rows(act) + [""]
        lines += ["What to do: `docs/SUPPLY_CHAIN.md`, \"When the report finds something\".", ""]
    if watch:
        lines += ["## Watched Ubuntu packages: advisories with no fixed package from Ubuntu (%d)" % len(watch), "",
                  "These do not fail the check; each new one is announced with a comment on the issue. Ubuntu lists every CVE filed "
                  "against a package until someone there reviews it, so some of these are about versions older than the one installed. "
                  "What to do about the list as a whole: `docs/SUPPLY_CHAIN.md`, \"Asterisk and Caddy come from Ubuntu\".", "",
                  "<details><summary>%d advisories</summary>" % len(watch), ""] + rows(watch) + ["", "</details>", ""]
    if ignored:
        lines += ["## Accepted for now (.vuln-ignore)", "", "| Advisory | Component | Until | Reason |", "|---|---|---|---|"]
        lines += ["| %s | %s %s | %s | %s |" % (md(f["id"]), md(f["package"]), md(f["version"]), f["ignore_until"], md(f["ignore_reason"])) for f in ignored]
        lines.append("")
    if listed:
        lines += ["## Ubuntu packages with advisories that have no fixed package yet (listed, not counted)", "",
                  "These are in the packages a fresh VM installs. Ubuntu has published no fix, so there is nothing to update to; "
                  "`unattended-upgrades` on the VM installs the fix when there is one.", "",
                  "<details><summary>%d advisories</summary>" % len(listed), ""] + rows(listed) + ["", "</details>", ""]
    if result["unused_ignores"]:
        lines += ["## Ignore entries that no longer match anything", "",
                  "Remove these from `.vuln-ignore`: " + ", ".join("`%s`" % i for i in result["unused_ignores"]), ""]
    if result["skipped"]:
        lines += ["## Not checked here", "",
                  "No exact version to ask about (GitHub's own Dependabot alerts cover the actions; container tags float by design):", ""]
        lines += ["- %s `%s` (%s)" % (md(c["name"]), md(c["version"]), md(", ".join(props(c, "source")))) for c in result["skipped"]]
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------- one GitHub issue kept in step (CI only)
def gh_api(args, body=None):
    cmd = ["gh", "api", "-H", "Accept: application/vnd.github+json"] + args
    p = subprocess.run(cmd + (["--input", "-"] if body is not None else []), input=None if body is None else json.dumps(body),
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise CheckError("gh api %s failed: %s" % (" ".join(args), p.stderr.strip()[:500]))
    return json.loads(p.stdout) if p.stdout.strip() else None


def sync_issue(repo, result, text, api=None):
    """One open issue (opened by the Actions bot, with ISSUE_TITLE) says what needs attention: the findings to act on
    and the watched Ubuntu ones. New findings open it or add a comment (both notify the owner); when there is nothing
    of either kind it is closed. Returns what was done, for the log."""
    api = api or gh_api
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo or ""):
        raise CheckError("--sync-issue needs GITHUB_REPOSITORY (owner/name)")
    # Only an issue the Actions bot itself opened: anyone can open an issue with our title in a public repo.
    mine = None
    page = 1
    while mine is None:
        batch = api(["repos/%s/issues?state=open&per_page=100&page=%d" % (repo, page)]) or []
        for i in batch:
            user = i.get("user") or {}
            if i.get("title") == ISSUE_TITLE and "pull_request" not in i and user.get("login") == "github-actions[bot]" and user.get("type") == "Bot":
                mine = i
                break
        if len(batch) < 100:
            break
        page += 1
    by_id = {f["id"]: f for f in result["watch"] + result["act"]}
    ids = sorted(by_id)
    body = (text[:BODY_LIMIT] + ("\n\n(cut short: the full report is attached to the workflow run)" if len(text) > BODY_LIMIT else "")
            + "\n\n" + ISSUE_MARK % ",".join(ids))
    if not ids:
        if mine is None:
            return "clean, no issue open"
        api(["-X", "POST", "repos/%s/issues/%d/comments" % (repo, mine["number"])], {"body": "The latest check found nothing left to act on or watch. Closing."})
        api(["-X", "PATCH", "repos/%s/issues/%d" % (repo, mine["number"])], {"state": "closed", "body": body})
        return "clean, closed #%d" % mine["number"]
    if mine is None:
        made = api(["-X", "POST", "repos/%s/issues" % repo], {"title": ISSUE_TITLE, "body": body})
        return "opened #%s" % (made or {}).get("number")
    m = re.search(r"<!-- treeline-vuln-ids: ([^>]*?) -->", mine.get("body") or "")
    before = set(filter(None, (m.group(1) if m else "").split(",")))
    new = [i for i in ids if i not in before]
    api(["-X", "PATCH", "repos/%s/issues/%d" % (repo, mine["number"])], {"body": body})
    if new:
        api(["-X", "POST", "repos/%s/issues/%d/comments" % (repo, mine["number"])],
            {"body": "New since the last check: " + ", ".join(
                "[%s](https://osv.dev/vulnerability/%s) (%s %s)" % (i, i, by_id[i]["package"], "to act on" if by_id[i]["status"] == "act" else "watched")
                for i in new) + ". The report above is updated."})
        return "updated #%d, new: %s" % (mine["number"], ", ".join(new))
    return "updated #%d, nothing new" % mine["number"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("sbom", help="CycloneDX JSON from scripts/sbom.py")
    ap.add_argument("--ignore-file", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".vuln-ignore"))
    ap.add_argument("--os-watch", default="", help="comma-separated Ubuntu source packages whose findings count")
    ap.add_argument("--report", metavar="FILE", help="write the Markdown report here too")
    ap.add_argument("--sync-issue", action="store_true", help="open, update or close the one GitHub issue (needs gh and GITHUB_REPOSITORY)")
    args = ap.parse_args(argv)
    today = datetime.datetime.now(datetime.timezone.utc).date()
    try:
        with open(args.sbom, encoding="utf-8") as f:
            sbom = json.load(f)
        ignores = {}
        if os.path.exists(args.ignore_file):
            with open(args.ignore_file, encoding="utf-8") as f:
                ignores = parse_ignores(f.read(), today)
        result = check(sbom, ignores, args.os_watch.split(","))
        text = report(result, today)
        if args.report:
            with open(args.report, "w", encoding="utf-8") as f:
                f.write(text + "\n")
        print(text)
        if args.sync_issue:
            print("issue: " + sync_issue(os.environ.get("GITHUB_REPOSITORY", ""), result, text), file=sys.stderr)
    except (CheckError, OSError, ValueError) as e:
        print("vuln_check: COULD NOT CHECK: %s" % e, file=sys.stderr)
        return 2
    return 1 if result["act"] else 0


if __name__ == "__main__":
    sys.exit(main())
