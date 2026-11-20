#!/usr/bin/env python3
"""The software bill of materials: every third-party thing Treeline runs, builds with or ships, in one list.

    python3 scripts/sbom.py                          CycloneDX 1.5 JSON on stdout
    python3 scripts/sbom.py -o sbom.json             ... to a file
    python3 scripts/sbom.py --os-packages FILE       also the VM's Ubuntu packages (FILE comes from scripts/os_packages.sh)
    python3 scripts/sbom.py --table                  a readable table instead of JSON
    python3 scripts/sbom.py --github-snapshot        the hash-pinned Python locks and the vendored browser libraries, in the
                                                     shape GitHub's dependency submission API takes (so Dependabot alerts see
                                                     them: GitHub does not read our *.lock files or web/phone/vendor/)
    python3 scripts/sbom.py --apt-packages           the package names install.sh installs, one per line
    python3 scripts/sbom.py --sync-notices           after a lock changes: put the new versions into THIRD_PARTY_NOTICES.md

Standard library only, and it executes nothing it reads (docs/SUPPLY_CHAIN.md says why). What it reads:

    controller/requirements-prod.lock        the app on the VM                      (PyPI)
    deploy/native/requirements-tools.lock    the VM's root-run tools                (PyPI)
    infra/requirements.lock                  the CDK app, owner's computer and CI   (PyPI)
    infra/restore/requirements.lock          restore.py, owner's computer           (PyPI)
    infra/package-lock.json                  the CDK command line                   (npm)
    web/phone/vendor/ + THIRD_PARTY_NOTICES  libraries copied into the softphone    (npm names)
    .github/workflows/*.yml                  the actions CI runs                    (GitHub Actions)
    Dockerfiles and compose files            base images, and pip pins inside them  (inventory)
    deploy/native/install.sh                 the Ubuntu packages the VM installs    (with --os-packages)

`scripts/vuln_check.py` takes the JSON this writes and asks OSV.dev about each entry.
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (lock file, the file that names what we asked for, role, is it part of what runs in production?)
PIP_LOCKS = [
    ("controller/requirements-prod.lock", "controller/requirements.txt", "vm-app", True),
    ("deploy/native/requirements-tools.lock", "deploy/native/requirements-tools.in", "vm-root-tools", True),
    ("infra/requirements.lock", "infra/requirements.in", "owner-infra", False),
    ("infra/restore/requirements.lock", "infra/restore/requirements.in", "owner-restore", False),
]
NPM_LOCKS = [("infra/package-lock.json", "owner-infra-cli", False)]

# Libraries copied into the repo. The version is whatever THIRD_PARTY_NOTICES.md says (one place to keep right), so a
# vendored file changed without its notice is caught by scripts/test_supply_chain.py, which also checks the files exist.
VENDORED = [
    {"name": "jssip", "notice": "JsSIP", "file": "web/phone/vendor/jssip.min.js"},
    {"name": "qrcode-generator", "notice": "qrcode-generator", "file": "web/phone/vendor/qrcode.js"},
]

UBUNTU_RELEASE = "24.04"          # the VM's release (deploy/native/install.sh); OSV calls it "Ubuntu:24.04:LTS"
SKIP_DIRS = {".git", "node_modules", "cdk.out", ".venv", ".venv-dev", "dist", "data", "__pycache__"}


class SbomError(Exception):
    pass


def read(path, root=ROOT):
    with open(os.path.join(root, path), encoding="utf-8") as f:
        return f.read()


def pypi_name(name):
    """PEP 503: the one spelling of a PyPI project name (what OSV and GitHub both index by)."""
    return re.sub(r"[-_.]+", "-", name).lower()


def purl(kind, name, version, namespace=None, qualifiers=None):
    q = urllib.parse.quote
    out = "pkg:" + kind + "/"
    if namespace:
        out += "/".join(q(p, safe="") for p in namespace.split("/")) + "/"
    out += q(name, safe="") + "@" + q(version, safe=":~.-_")
    if qualifiers:
        out += "?" + "&".join("%s=%s" % (k, q(v, safe=".-_")) for k, v in sorted(qualifiers.items()))
    return out


# ---------------------------------------------------------------- readers
def parse_pip_lock(text, path="<lock>"):
    """[(name, version, [sha256, ...])] from a scripts/make_locks.sh lock. Anything that is not a comment, an exact
    `name==version` or a `--hash=sha256:` line is an error: a lock we cannot fully read must not look like a short one."""
    out, cur = [], None
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip().rstrip("\\").strip()
        if not line or line.startswith("#"):
            continue
        m = re.fullmatch(r"([A-Za-z0-9][A-Za-z0-9._-]*)==([A-Za-z0-9][A-Za-z0-9.!+_-]*)", line)
        if m:
            cur = (m.group(1), m.group(2), [])
            out.append(cur)
            continue
        m = re.fullmatch(r"--hash=sha256:([0-9a-f]{64})", line)
        if m and cur:
            cur[2].append(m.group(1))
            continue
        raise SbomError("%s:%d: not an exact pin or a hash: %r" % (path, n, raw))
    if not out:
        raise SbomError("%s: no pinned packages" % path)
    return out


def direct_names(text):
    """The project names a requirements input asks for (what is 'direct'; the rest of a lock came along with them)."""
    names = set()
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        m = re.match(r"([A-Za-z0-9][A-Za-z0-9._-]*)", line)
        if m:
            names.add(pypi_name(m.group(1)))
    return names


def parse_npm_lock(text, path="<package-lock.json>"):
    """[(name, version, integrity, is_direct)] from a lockfileVersion 2/3 package-lock.json."""
    lock = json.loads(text)
    packages = lock.get("packages")
    if not isinstance(packages, dict):
        raise SbomError("%s: no \"packages\" map (lockfileVersion 2 or 3 is needed)" % path)
    top = packages.get("", {})
    direct = set(top.get("dependencies", {})) | set(top.get("devDependencies", {})) | set(top.get("optionalDependencies", {}))
    out = []
    for key, info in sorted(packages.items()):
        if not key or info.get("link"):
            continue
        name = info.get("name") or key.rsplit("node_modules/", 1)[-1]
        if "version" not in info:
            raise SbomError("%s: %s has no version" % (path, key))
        out.append((name, info["version"], info.get("integrity", ""), key == "node_modules/" + name and name in direct))
    return out


def vendored_version(notices, label):
    """The version THIRD_PARTY_NOTICES.md gives a vendored library: `| [JsSIP](https://...) 3.11.1 | ...`."""
    m = re.search(r"^\|\s*\[%s\]\([^)]*\)\s+v?(\d+(?:\.\d+)+)\s*\|" % re.escape(label), notices, re.M)
    if not m:
        raise SbomError("THIRD_PARTY_NOTICES.md has no version for the vendored library %r "
                        "(expected a row starting `| [%s](url) <version> |`)" % (label, label))
    return m.group(1)


NOTICE_VERSION = re.compile(r"(\[([^\]]+)\]\([^)]*\)\s+)v?(\d+(?:\.\d+)+)")


def notice_versions(notices):
    """[(label, version)] for every `[label](url) 1.2.3` in THIRD_PARTY_NOTICES.md."""
    return [(m.group(2), m.group(3)) for m in NOTICE_VERSION.finditer(notices)]


def sync_notices(notices, components):
    """THIRD_PARTY_NOTICES.md with the version after each `[name](url)` set to what the locks pin, for the names that
    are PyPI packages pinned at exactly one version. Vendored libraries are left alone: for those the notice is the
    source of the version, and it changes by hand together with the file."""
    pinned = {}
    for c in components:
        if c["ecosystem"] == "PyPI":
            pinned.setdefault(c["name"], set()).add(c["version"])

    def fix(m):
        versions = pinned.get(pypi_name(m.group(2)))
        return m.group(1) + (next(iter(versions)) if versions and len(versions) == 1 else m.group(3))
    return NOTICE_VERSION.sub(fix, notices)


USES = re.compile(r"^[ \t]*(?:-[ \t]*)?uses:[ \t]*['\"]?([A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+)@([A-Za-z0-9_./-]+)['\"]?[ \t]*(?:#[ \t]*(\S+))?", re.M)


def parse_actions(text):
    """[(owner/repo[/path], ref, version or None)] for every `uses:` in a workflow. The version is the ref if it is a
    full x.y.z tag, else the `# v1.2.3` comment after a pinned commit; a bare `@v4` gives no exact version."""
    out = []
    for name, ref, comment in USES.findall(text):
        version = None
        for cand in (ref, comment or ""):
            m = re.fullmatch(r"v?(\d+\.\d+\.\d+)", cand)
            if m:
                version = m.group(1)
                break
        out.append((name, ref, version))
    return out


def parse_images(text, compose=False):
    """Image references: FROM lines of a Dockerfile, or `image:` lines of a compose file."""
    pat = r"^\s*image:\s*['\"]?([^\s'\"#]+)" if compose else r"^\s*FROM\s+(?:--\S+\s+)*([^\s]+)"
    return [i for i in re.findall(pat, text, re.M | (0 if compose else re.I)) if i.lower() != "scratch"]


def parse_dockerfile_pip(text):
    """Exact pip pins written straight into a Dockerfile (`pip install ... playwright==1.55.0`)."""
    out = []
    for line in re.findall(r"pip3?\s+install\b[^\n]*", text):
        out += re.findall(r"(?<![\w.-])([A-Za-z0-9][A-Za-z0-9._-]*)==([A-Za-z0-9][A-Za-z0-9.!+_-]*)", line)
    return out


def apt_packages(install_sh):
    """The package names deploy/native/install.sh hands to `apt-get install` (fail2ban included: it is skipped only in CI)."""
    joined = re.sub(r"\\\n", " ", install_sh)
    names = []
    for line in re.findall(r"^\s*apt-get install\b([^\n]*)", joined, re.M):
        line = re.sub(r"\$\(\[[^\]]*\]\s*\|\|\s*echo\s+([a-z0-9+.-]+)\s*\)", r" \1 ", line)     # $([ "$CI" = 1 ] || echo fail2ban)
        line = line.split(">", 1)[0]
        for word in line.split():
            if word.startswith("-"):
                continue
            if not re.fullmatch(r"[a-z0-9][a-z0-9+.-]+", word):
                raise SbomError("install.sh: cannot read the apt package list (unexpected word %r)" % word)
            names.append(word)
    if not names:
        raise SbomError("install.sh: no `apt-get install` line found")
    return sorted(set(names))


def parse_os_packages(text):
    """Rows written by scripts/os_packages.sh: binary package, version, source package, source version, architecture."""
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        cols = line.split("\t")
        if len(cols) != 5 or not all(cols):
            raise SbomError("os packages line %d: expected five tab-separated fields, got %r" % (n, line))
        name, version, source, source_version, arch = (c.strip() for c in cols)
        out.append({"name": name.split(":")[0], "version": version, "source": source, "source_version": source_version, "arch": arch})
    if not out:
        raise SbomError("the os packages file is empty")
    return out


def walk(root, wanted):
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(files):
            rel = os.path.relpath(os.path.join(base, name), root)
            if wanted(rel, name):
                yield rel


# ---------------------------------------------------------------- the list
def collect(root=ROOT, os_packages_text=None):
    """Every component, as dicts: ecosystem, name, version, purl, role, production, direct, sources (and more per kind).
    One entry per (ecosystem, name, version); a package in two locks is one entry with two sources."""
    found = {}

    def add(ecosystem, name, version, purl_, source, role, production, direct=True, **extra):
        key = (ecosystem, name, version)
        c = found.get(key)
        if c is None:
            c = found[key] = dict(ecosystem=ecosystem, name=name, version=version, purl=purl_, roles=[], sources=[],
                                  production=False, direct=False, **extra)
        if role not in c["roles"]:
            c["roles"].append(role)
        if source not in c["sources"]:
            c["sources"].append(source)
        c["production"] = c["production"] or production
        c["direct"] = c["direct"] or direct
        for k, v in extra.items():
            if isinstance(v, list):
                c[k] = sorted(set(c.get(k, [])) | set(v))
        return c

    for lock, inputs, role, production in PIP_LOCKS:
        asked = direct_names(read(inputs, root))
        for name, version, hashes in parse_pip_lock(read(lock, root), lock):
            norm = pypi_name(name)
            add("PyPI", norm, version, purl("pypi", norm, version), lock, role, production, direct=norm in asked, sha256=hashes)

    for lock, role, production in NPM_LOCKS:
        for name, version, integrity, direct in parse_npm_lock(read(lock, root), lock):
            ns, _, short = name.rpartition("/")
            add("npm", name, version, purl("npm", short, version, namespace=ns or None), lock, role, production, direct=direct,
                integrity=integrity)

    notices = read("THIRD_PARTY_NOTICES.md", root)
    for v in VENDORED:
        with open(os.path.join(root, v["file"]), "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        version = vendored_version(notices, v["notice"])
        add("npm", v["name"], version, purl("npm", v["name"], version), v["file"], "browser-vendored", True, sha256=[digest])

    wf_dir = os.path.join(root, ".github", "workflows")
    for wf in sorted(os.listdir(wf_dir)) if os.path.isdir(wf_dir) else []:
        if not wf.endswith((".yml", ".yaml")):
            continue
        rel = ".github/workflows/" + wf
        for name, ref, version in parse_actions(read(rel, root)):
            repo = "/".join(name.split("/")[:2])
            owner, short = repo.split("/")
            add("GitHub Actions", repo, version or ref, purl("github", short, version or ref, namespace=owner), rel, "ci", False,
                ref=ref, exact=version is not None)

    for rel in walk(root, lambda rel, name: name == "Dockerfile" or re.fullmatch(r"docker-compose[\w.-]*\.ya?ml", name)):
        text = read(rel, root)
        compose = not rel.endswith("Dockerfile")
        for image in parse_images(text, compose):
            repo, _, tag = image.partition(":") if "@" not in image else (image, "", "")
            add("container", repo, tag or "latest", purl("docker", repo.rsplit("/", 1)[-1], tag or "latest",
                namespace=repo.rsplit("/", 1)[0] if "/" in repo else None), rel, "container-base", False)
        if not compose:
            for name, version in parse_dockerfile_pip(text):
                norm = pypi_name(name)
                add("PyPI", norm, version, purl("pypi", norm, version), rel, "dev-container", False)

    if os_packages_text is not None:
        for p in parse_os_packages(os_packages_text):
            add("Ubuntu", p["name"], p["version"],
                purl("deb", p["name"], p["version"], namespace="ubuntu", qualifiers={"arch": p["arch"], "distro": "ubuntu-" + UBUNTU_RELEASE}),
                "deploy/native/install.sh", "vm-os", True, direct=False, source_package=p["source"], source_version=p["source_version"])
        wanted = set(apt_packages(read("deploy/native/install.sh", root)))
        for c in found.values():
            if c["ecosystem"] == "Ubuntu" and c["name"] in wanted:
                c["direct"] = True

    return sorted(found.values(), key=lambda c: (c["ecosystem"], c["name"], c["version"]))


# ---------------------------------------------------------------- outputs
def now_iso():
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    t = datetime.datetime.fromtimestamp(int(epoch), datetime.timezone.utc) if epoch else datetime.datetime.now(datetime.timezone.utc)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def cyclonedx(components, version="unreleased"):
    out = []
    for c in components:
        props = [{"name": "treeline:ecosystem", "value": c["ecosystem"]},
                 {"name": "treeline:production", "value": "true" if c["production"] else "false"},
                 {"name": "treeline:direct", "value": "true" if c["direct"] else "false"}]
        props += [{"name": "treeline:role", "value": r} for r in c["roles"]]
        props += [{"name": "treeline:source", "value": s} for s in c["sources"]]
        for key in ("source_package", "source_version", "ref"):
            if c.get(key):
                props.append({"name": "treeline:" + key.replace("_", "-"), "value": c[key]})
        if c["ecosystem"] == "GitHub Actions":
            props.append({"name": "treeline:exact-version", "value": "true" if c.get("exact") else "false"})
        entry = {"type": "container" if c["ecosystem"] == "container" else "library", "bom-ref": c["purl"], "name": c["name"],
                 "version": c["version"], "purl": c["purl"], "scope": "required" if c["production"] else "excluded",
                 "properties": props}
        if c.get("sha256"):
            entry["hashes"] = [{"alg": "SHA-256", "content": h} for h in c["sha256"]]
        out.append(entry)
    return {
        "bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
        "metadata": {
            "timestamp": now_iso(),
            "tools": [{"name": "treeline scripts/sbom.py"}],
            "component": {"type": "application", "bom-ref": "treeline", "name": "treeline", "version": version},
        },
        "components": out,
    }


def github_snapshot(components, env=None):
    """What GitHub cannot work out for itself: the pinned Python locks and the vendored browser libraries. Actions and
    package-lock.json are read by GitHub directly, and it has no advisories for Ubuntu packages, so those are left out."""
    env = os.environ if env is None else env
    manifests = {}
    for c in components:
        if c["ecosystem"] not in ("PyPI", "npm") or "owner-infra-cli" in c["roles"] or c["roles"] == ["dev-container"]:
            continue
        for source in c["sources"]:
            if source.endswith("Dockerfile") or source.endswith("package-lock.json"):
                continue
            m = manifests.setdefault(source, {"name": source, "file": {"source_location": source}, "resolved": {}})
            m["resolved"][c["name"]] = {"package_url": c["purl"], "relationship": "direct" if c["direct"] else "indirect",
                                        "scope": "runtime" if c["production"] else "development"}
    return {
        "version": 0,
        "sha": env.get("GITHUB_SHA", "0" * 40),
        "ref": env.get("GITHUB_REF", "refs/heads/main"),
        "job": {"id": env.get("GITHUB_RUN_ID", "local"), "correlator": "treeline-sbom"},
        "detector": {"name": "treeline-sbom", "version": "1", "url": "https://github.com/%s/blob/main/scripts/sbom.py" % env.get("GITHUB_REPOSITORY", "")},
        "scanned": now_iso(),
        "manifests": manifests,
    }


def table(components):
    rows = [("ecosystem", "name", "version", "prod", "where")]
    rows += [(c["ecosystem"], c["name"], c["version"], "yes" if c["production"] else "", ", ".join(c["sources"])) for c in components]
    widths = [max(len(r[i]) for r in rows) for i in range(4)]
    return "\n".join("  ".join(r[i].ljust(widths[i]) for i in range(4)) + "  " + r[4] for r in rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("-o", "--output", help="write here instead of stdout")
    ap.add_argument("--os-packages", metavar="FILE", help="the VM's Ubuntu packages, from scripts/os_packages.sh")
    ap.add_argument("--version", default=os.environ.get("TREELINE_VERSION", "unreleased"), help="the Treeline version this describes")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--table", action="store_true")
    mode.add_argument("--github-snapshot", action="store_true")
    mode.add_argument("--apt-packages", action="store_true")
    mode.add_argument("--sync-notices", action="store_true", help="set the PyPI versions named in THIRD_PARTY_NOTICES.md to what the locks pin")
    args = ap.parse_args(argv)
    try:
        if args.apt_packages:
            text = "\n".join(apt_packages(read("deploy/native/install.sh")))
        elif args.sync_notices:
            before = read("THIRD_PARTY_NOTICES.md")
            after = sync_notices(before, collect())
            if after != before:
                with open(os.path.join(ROOT, "THIRD_PARTY_NOTICES.md"), "w", encoding="utf-8") as f:
                    f.write(after)
            print("THIRD_PARTY_NOTICES.md: %s" % ("versions updated (now run scripts/build_licenses.py)" if after != before else "already in step"), file=sys.stderr)
            return 0
        else:
            os_text = None
            if args.os_packages:
                with open(args.os_packages, encoding="utf-8") as f:
                    os_text = f.read()
            components = collect(os_packages_text=os_text)
            if args.table:
                text = table(components)
            elif args.github_snapshot:
                text = json.dumps(github_snapshot(components), indent=1)
            else:
                text = json.dumps(cyclonedx(components, args.version), indent=1)
    except (SbomError, OSError, ValueError) as e:
        print("sbom: %s" % e, file=sys.stderr)
        return 2
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
