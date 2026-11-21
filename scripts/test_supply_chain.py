"""Tests for sbom.py and vuln_check.py:  python3 -m unittest scripts/test_supply_chain.py

No network: OSV and the GitHub API are stood in for by functions that answer in the shapes those services document
(https://google.github.io/osv.dev/post-v1-querybatch/, https://docs.github.com/en/rest/issues). The real OSV is
exercised by the `supply chain` workflow on every pull request, which is where a wrong assumption here would show.
"""

import datetime
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import sbom            # noqa: E402
import vuln_check      # noqa: E402

H = "a" * 64
TODAY = datetime.date(2026, 11, 20)


class Locks(unittest.TestCase):
    def test_a_lock_is_read_with_every_hash(self):
        text = "# Generated\nFlask==3.1.3 \\\n    --hash=sha256:%s \\\n    --hash=sha256:%s\nmarkupsafe==3.0.4 \\\n    --hash=sha256:%s\n" % (H, "b" * 64, H)
        self.assertEqual(sbom.parse_pip_lock(text), [("Flask", "3.1.3", [H, "b" * 64]), ("markupsafe", "3.0.4", [H])])

    def test_a_line_that_is_not_an_exact_pin_is_an_error_not_a_shorter_list(self):
        for bad in ("flask>=3.0\n", "flask==3.1.3\n-r other.txt\n", "flask @ https://example.com/f.whl\n", "--hash=sha256:%s\n" % H):
            with self.assertRaises(sbom.SbomError, msg=bad):
                sbom.parse_pip_lock(bad)
        with self.assertRaises(sbom.SbomError):
            sbom.parse_pip_lock("# nothing\n")

    def test_names_are_normalized_the_way_pypi_does(self):
        self.assertEqual(sbom.pypi_name("Python_Dateutil"), "python-dateutil")
        self.assertEqual(sbom.pypi_name("typing.extensions"), "typing-extensions")

    def test_direct_names_come_from_the_input_file(self):
        self.assertEqual(sbom.direct_names("# c\nboto3>=1.35\naws-cdk-lib==2.275.0  # pinned\n\nFlask>=3\n"), {"boto3", "aws-cdk-lib", "flask"})

    def test_npm_lock(self):
        lock = {"lockfileVersion": 3, "packages": {
            "": {"devDependencies": {"aws-cdk": "2.1.0"}},
            "node_modules/aws-cdk": {"version": "2.1.0", "integrity": "sha512-x"},
            "node_modules/@scope/dep": {"version": "1.0.0"},
            "node_modules/aws-cdk/node_modules/inner": {"version": "0.1.0"}}}
        got = sbom.parse_npm_lock(json.dumps(lock))
        self.assertIn(("aws-cdk", "2.1.0", "sha512-x", True), got)
        self.assertIn(("@scope/dep", "1.0.0", "", False), got)
        self.assertIn(("inner", "0.1.0", "", False), got)
        with self.assertRaises(sbom.SbomError):
            sbom.parse_npm_lock(json.dumps({"lockfileVersion": 1, "dependencies": {}}))

    def test_purls(self):
        self.assertEqual(sbom.purl("pypi", "flask", "3.1.3"), "pkg:pypi/flask@3.1.3")                 # repo-rules: allow (a package URL, not an address)
        self.assertEqual(sbom.purl("npm", "dep", "1.0.0", namespace="@scope"), "pkg:npm/%40scope/dep@1.0.0")   # repo-rules: allow (a package URL)
        self.assertEqual(sbom.purl("deb", "asterisk", "1:20.6.0~dfsg+~cs6-1", namespace="ubuntu", qualifiers={"arch": "amd64", "distro": "ubuntu-24.04"}),
                         "pkg:deb/ubuntu/asterisk@1:20.6.0~dfsg%2B~cs6-1?arch=amd64&distro=ubuntu-24.04")


class OtherSources(unittest.TestCase):
    def test_vendored_version_is_read_from_the_notices(self):
        notices = "| [JsSIP](https://github.com/versatica/JsSIP) 3.11.1 | SIP | MIT | x |\n| [Other](https://example.com) | y | MIT | z |\n"
        self.assertEqual(sbom.vendored_version(notices, "JsSIP"), "3.11.1")
        with self.assertRaises(sbom.SbomError):
            sbom.vendored_version(notices, "Other")           # listed, but with no version: must not pass as "unknown"

    def test_actions(self):
        wf = """
jobs:
  a:
    steps:
      - uses: actions/checkout@v4
      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262   # v4
      - uses: actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0 # v7.1.0
      - name: x
        uses: github/codeql-action/init@v4.39.4      # repo-rules: allow (an action at a version tag, not an address)
      - run: echo "uses: not/this@v1" > /dev/null
"""
        self.assertEqual(sbom.parse_actions(wf), [
            ("actions/checkout", "v4", None),
            ("actions/checkout", "11d5960a326750d5838078e36cf38b85af677262", None),
            ("actions/setup-python", "6d4fd22b20465ccc0f7354476588e8df7c9ca0e0", "7.1.0"),
            ("github/codeql-action/init", "v4.39.4", "4.39.4")])

    def test_images_and_pins_in_dockerfiles(self):
        df = "# c\nFROM --platform=linux/amd64 ubuntu:24.04 AS base\nFROM scratch\nRUN pip install --no-cache-dir --break-system-packages playwright==1.55.0\n"
        self.assertEqual(sbom.parse_images(df), ["ubuntu:24.04"])
        self.assertEqual(sbom.parse_dockerfile_pip(df), [("playwright", "1.55.0")])
        self.assertEqual(sbom.parse_images("services:\n  c:\n    image: caddy:2\n  d:\n    build: ./x\n", compose=True), ["caddy:2"])

    def test_the_apt_list_is_read_from_the_real_install_script(self):
        with open(os.path.join(ROOT, "deploy/native/install.sh")) as f:
            names = sbom.apt_packages(f.read())
        for must in ("caddy", "python3", "age", "unattended-upgrades", "fail2ban", "libssl3t64", "libsrtp2-1"):
            self.assertIn(must, names)
        self.assertNotIn("asterisk", names, "Asterisk is built from source (asterisk/build/), not installed from Ubuntu")
        for n in names:
            self.assertRegex(n, r"^[a-z0-9][a-z0-9+.-]+$")

    def test_an_apt_line_we_cannot_read_is_an_error(self):
        with self.assertRaises(sbom.SbomError):
            sbom.apt_packages("apt-get install -y $EXTRA_PACKAGES\n")
        with self.assertRaises(sbom.SbomError):
            sbom.apt_packages("echo nothing\n")

    def test_os_packages(self):
        text = "asterisk\t1:20.6.0-1\tasterisk\t1:20.6.0-1\tamd64\nlibssl3t64:amd64\t3.0.13-0ubuntu3.5\topenssl\t3.0.13-0ubuntu3.5\tamd64\nlibc6\t2.39-0ubuntu8.6\tglibc\t2.39-0ubuntu8.6\tamd64\n"
        got = sbom.parse_os_packages(text)
        self.assertEqual(got[1], {"name": "libssl3t64", "version": "3.0.13-0ubuntu3.5", "source": "openssl", "source_version": "3.0.13-0ubuntu3.5", "arch": "amd64"})
        with self.assertRaises(sbom.SbomError):
            sbom.parse_os_packages("asterisk 1:20\n")
        with self.assertRaises(sbom.SbomError):
            sbom.parse_os_packages("\n")


class TheRealRepo(unittest.TestCase):
    """The list built from this checkout: what a reader of the SBOM relies on."""

    @classmethod
    def setUpClass(cls):
        cls.os_text = "libsrtp2-1\t2.5.0-3build1\tlibsrtp2\t2.5.0-3build1\tamd64\nlibssl3t64:amd64\t3.0.13-0ubuntu3.5\topenssl\t3.0.13-0ubuntu3.5\tamd64\nlibc6\t2.39-0ubuntu8.6\tglibc\t2.39-0ubuntu8.6\tamd64\n"
        cls.components = sbom.collect(os_packages_text=cls.os_text)
        cls.by = {(c["ecosystem"], c["name"]): c for c in cls.components}

    def test_every_lock_and_every_vendored_file_is_in(self):
        sources = {s for c in self.components for s in c["sources"]}
        for lock, _, _, _ in sbom.PIP_LOCKS:
            self.assertIn(lock, sources)
        self.assertIn("infra/package-lock.json", sources)
        for v in sbom.VENDORED:
            self.assertIn(v["file"], sources)

    def test_the_asterisk_builds_pinned_inputs_are_in(self):
        # asterisk/build/sources.lock is what the build compiles: Asterisk, the pjproject it bundles, the toolchain image.
        import asterisk_build
        with open(os.path.join(ROOT, "asterisk", "build", "sources.lock")) as f:
            src = asterisk_build.parse_lock(f.read(), asterisk_build.SOURCES_FIELDS)
        ast = self.by[("Upstream source", "asterisk")]
        pj = self.by[("Upstream source", "pjproject")]
        self.assertEqual(ast["version"], src["ASTERISK_VERSION"])
        self.assertEqual(pj["version"], src["PJPROJECT_VERSION"])
        self.assertEqual(ast["purl"], "pkg:github/asterisk/asterisk@%s" % src["ASTERISK_VERSION"])
        self.assertEqual(pj["purl"], "pkg:github/pjsip/pjproject@%s" % src["PJPROJECT_VERSION"])
        self.assertEqual(ast["sha256"], [src["ASTERISK_SHA256"]])
        self.assertIn("asterisk/build/sources.lock", ast["sources"])
        self.assertFalse(pj["direct"])
        self.assertTrue(ast["production"] and pj["production"], "every release carries them and the VM runs them")
        # The toolchain image is the digest in the lock, and a `FROM ${BASE_IMAGE}` build argument is never a component.
        toolchain = [c for c in self.components if "asterisk-build-toolchain" in c["roles"]]
        self.assertEqual(len(toolchain), 1)
        self.assertIn("@sha256:", toolchain[0]["version"])
        self.assertFalse([c for c in self.components if "$" in c["name"]])

    def test_a_dockerfile_build_argument_is_not_an_image(self):
        self.assertEqual(sbom.parse_images("ARG BASE_IMAGE\nFROM ${BASE_IMAGE}\n"), [])
        self.assertEqual(sbom.parse_images("FROM ubuntu:24.04@sha256:" + "b" * 64 + "\n"), ["ubuntu:24.04@sha256:" + "b" * 64])

    def test_every_file_in_the_vendor_directory_is_declared(self):
        # A library dropped into web/phone/vendor/ without an entry in sbom.VENDORED would never be checked.
        declared = {os.path.basename(v["file"]) for v in sbom.VENDORED}
        for name in os.listdir(os.path.join(ROOT, "web/phone/vendor")):
            if name.endswith(".js"):
                self.assertIn(name, declared, "add %s to VENDORED in scripts/sbom.py (and to THIRD_PARTY_NOTICES.md)" % name)

    def test_what_runs_in_production_is_marked(self):
        self.assertTrue(self.by[("PyPI", "flask")]["production"])
        self.assertTrue(self.by[("PyPI", "flask")]["direct"])
        self.assertFalse(self.by[("PyPI", "jinja2")]["direct"])
        self.assertTrue(self.by[("PyPI", "boto3")]["production"])           # the root-run tools
        self.assertFalse(self.by[("PyPI", "aws-cdk-lib")]["production"])    # the owner's computer
        self.assertTrue(self.by[("npm", "jssip")]["production"])
        self.assertTrue(self.by[("Ubuntu", "libsrtp2-1")]["direct"])           # linked by Asterisk, installed by install.sh
        self.assertTrue(self.by[("Ubuntu", "libssl3t64")]["direct"])           # Asterisk links it, install.sh names it
        self.assertFalse(self.by[("Ubuntu", "libc6")]["direct"])               # pulled in by something else

    def test_versions_named_in_the_notices_match_the_locks(self):
        # THIRD_PARTY_NOTICES.md is the licenses page families see. `python3 scripts/sbom.py --sync-notices` fixes this.
        with open(os.path.join(ROOT, "THIRD_PARTY_NOTICES.md")) as f:
            notices = f.read()
        self.assertEqual(sbom.sync_notices(notices, self.components), notices,
                         "a version in THIRD_PARTY_NOTICES.md is not the one a lock pins: run scripts/sbom.py --sync-notices, then ./dev check")
        self.assertIn(("pywebpush", self.by[("PyPI", "pywebpush")]["version"]), sbom.notice_versions(notices))

    def test_sync_notices_changes_only_pinned_pypi_versions(self):
        comps = [{"ecosystem": "PyPI", "name": "pywebpush", "version": "2.6.0"}, {"ecosystem": "PyPI", "name": "two", "version": "1.0"},
                 {"ecosystem": "PyPI", "name": "two", "version": "2.0"}, {"ecosystem": "npm", "name": "jssip", "version": "9.9.9"}]
        text = "| [pywebpush](https://x) 2.5.0 and [py-vapid](https://y) 1.9.6 | a |\n| [JsSIP](https://z) 3.11.1 | b |\n| [two](https://t) 0.5 | c |\n| [Flask](https://f) | d |\n"
        self.assertEqual(sbom.sync_notices(text, comps),
                         "| [pywebpush](https://x) 2.6.0 and [py-vapid](https://y) 1.9.6 | a |\n| [JsSIP](https://z) 3.11.1 | b |\n| [two](https://t) 0.5 | c |\n| [Flask](https://f) | d |\n")

    def test_cyclonedx_shape(self):
        doc = sbom.cyclonedx(self.components, "v1.2.3")
        self.assertEqual((doc["bomFormat"], doc["specVersion"]), ("CycloneDX", "1.5"))
        self.assertEqual(doc["metadata"]["component"]["version"], "v1.2.3")
        refs = [c["bom-ref"] for c in doc["components"]]
        self.assertEqual(len(refs), len(set(refs)))
        flask = next(c for c in doc["components"] if c["name"] == "flask")
        self.assertEqual(flask["purl"], "pkg:pypi/flask@" + flask["version"])
        self.assertEqual(len(flask["hashes"][0]["content"]), 64)
        json.dumps(doc)

    def test_the_github_snapshot_has_only_what_github_cannot_read_itself(self):
        snap = sbom.github_snapshot(self.components, {"GITHUB_SHA": "f" * 40, "GITHUB_REF": "refs/heads/main", "GITHUB_RUN_ID": "7", "GITHUB_REPOSITORY": "o/r"})
        self.assertEqual(set(snap["manifests"]), {l for l, _, _, _ in sbom.PIP_LOCKS} | {v["file"] for v in sbom.VENDORED})
        app = snap["manifests"]["controller/requirements-prod.lock"]["resolved"]
        self.assertEqual(app["flask"]["relationship"], "direct")
        self.assertEqual(app["jinja2"], {"package_url": "pkg:pypi/jinja2@" + self.by[("PyPI", "jinja2")]["version"], "relationship": "indirect", "scope": "runtime"})
        self.assertEqual(snap["manifests"]["infra/requirements.lock"]["resolved"]["aws-cdk-lib"]["scope"], "development")
        self.assertEqual((snap["sha"], snap["job"]["correlator"], snap["version"]), ("f" * 40, "treeline-sbom", 0))


# ---------------------------------------------------------------- vuln_check
def component(eco, name, version, production=True, **extra):
    props = [{"name": "treeline:ecosystem", "value": eco}, {"name": "treeline:production", "value": "true" if production else "false"},
             {"name": "treeline:source", "value": "some.lock"}]
    props += [{"name": "treeline:" + k.replace("_", "-"), "value": v} for k, v in extra.items()]
    return {"name": name, "version": version, "properties": props}


class FakeOsv:
    """Answers like api.osv.dev: querybatch gives ids only, in the order asked; /v1/vulns/<id> gives the record."""

    def __init__(self, hits, records, page_after=None):
        self.hits, self.records, self.page_after, self.calls = hits, records, page_after, []

    def __call__(self, url, body=None, timeout=60):
        self.calls.append((url, body))
        if url.endswith("/v1/querybatch"):
            results = []
            for q in body["queries"]:
                ids = self.hits.get((q["package"]["ecosystem"], q["package"]["name"], q["version"]), [])
                if self.page_after and len(ids) > self.page_after:
                    if "page_token" not in q:
                        results.append({"vulns": [{"id": i, "modified": "x"} for i in ids[:self.page_after]], "next_page_token": "t"})
                        continue
                    ids = ids[self.page_after:]
                results.append({"vulns": [{"id": i, "modified": "x"} for i in ids]} if ids else {})
            return {"results": results}
        return self.records[url.rsplit("/", 1)[1]]


GHSA = {"id": "GHSA-aaaa-bbbb-cccc", "aliases": ["CVE-2026-0001"], "summary": "Flask does a bad thing | with a pipe",
        "database_specific": {"severity": "HIGH"},
        "affected": [{"package": {"name": "flask", "ecosystem": "PyPI"}, "ranges": [{"type": "ECOSYSTEM", "events": [{"introduced": "0"}, {"fixed": "3.1.4"}]}]}]}
MAL = {"id": "MAL-2026-1", "summary": "Malicious code in jssip", "affected": [{"package": {"name": "jssip", "ecosystem": "npm"}}]}
GONE = {"id": "GHSA-gone-gone-gone", "withdrawn": "2026-01-01T00:00:00Z", "summary": "withdrawn"}
UBU = {"id": "UBUNTU-CVE-2026-9", "summary": "asterisk thing", "severity": [{"type": "Ubuntu", "score": "medium"}],
       "affected": [{"package": {"name": "asterisk", "ecosystem": "Ubuntu:24.04:LTS"}, "ranges": [{"events": [{"introduced": "0"}]}]}]}
UBU2 = {"id": "UBUNTU-CVE-2026-10", "summary": "sox thing", "affected": [{"package": {"name": "sox", "ecosystem": "Ubuntu:24.04:LTS"}}]}

SBOM = {"components": [
    component("PyPI", "flask", "3.1.3"),
    component("PyPI", "jinja2", "3.1.6"),
    component("npm", "jssip", "3.11.1"),
    component("GitHub Actions", "actions/checkout", "v4", production=False, exact_version="false"),
    component("GitHub Actions", "actions/setup-python", "7.1.0", production=False, exact_version="true"),
    component("container", "ubuntu", "24.04", production=False),
    component("Ubuntu", "asterisk", "1:20.6.0-1", source_package="asterisk", source_version="1:20.6.0-1"),
    component("Ubuntu", "asterisk-modules", "1:20.6.0-1", source_package="asterisk", source_version="1:20.6.0-1"),
    component("Ubuntu", "libsox3", "14.4.2-1", source_package="sox", source_version="14.4.2-1"),
]}
HITS = {("PyPI", "flask", "3.1.3"): ["GHSA-aaaa-bbbb-cccc", "GHSA-gone-gone-gone"], ("npm", "jssip", "3.11.1"): ["MAL-2026-1"],
        ("Ubuntu:24.04:LTS", "asterisk", "1:20.6.0-1"): ["UBUNTU-CVE-2026-9"], ("Ubuntu:24.04:LTS", "sox", "14.4.2-1"): ["UBUNTU-CVE-2026-10"]}
RECORDS = {r["id"]: r for r in (GHSA, MAL, GONE, UBU, UBU2)}


class Asking(unittest.TestCase):
    def test_only_exact_versions_are_asked_about_and_the_rest_is_reported_as_not_checked(self):
        asked, skipped = vuln_check.queries_for(SBOM)
        self.assertEqual(len(asked), 7)
        self.assertIn({"package": {"ecosystem": "Ubuntu:24.04:LTS", "name": "sox"}, "version": "14.4.2-1"}, [q for q, _ in asked])
        self.assertIn({"package": {"ecosystem": "GitHub Actions", "name": "actions/setup-python"}, "version": "7.1.0"}, [q for q, _ in asked])
        self.assertEqual(sorted(c["name"] for c in skipped), ["actions/checkout", "ubuntu"])

    def test_paging_is_followed(self):
        osv = FakeOsv({("PyPI", "flask", "3.1.3"): ["A-1", "A-2", "A-3"]}, {}, page_after=2)
        ids = vuln_check.query_batch([{"package": {"ecosystem": "PyPI", "name": "flask"}, "version": "3.1.3"},
                                      {"package": {"ecosystem": "PyPI", "name": "jinja2"}, "version": "3.1.6"}], osv)
        self.assertEqual(ids, [["A-1", "A-2", "A-3"], []])
        self.assertEqual(osv.calls[1][1]["queries"], [{"package": {"ecosystem": "PyPI", "name": "flask"}, "version": "3.1.3", "page_token": "t"}])

    def test_an_answer_of_the_wrong_shape_is_an_error_never_a_clean_result(self):
        q = [{"package": {"ecosystem": "PyPI", "name": "flask"}, "version": "3.1.3"}]
        for answer in ({}, {"results": []}, {"results": "no"}, [], {"results": [{"vulns": [{"modified": "x"}]}]}):
            with self.assertRaises(vuln_check.CheckError, msg=answer):
                vuln_check.query_batch(q, lambda url, body=None: answer)

    def test_an_odd_advisory_id_is_never_put_in_a_url(self):
        with self.assertRaises(vuln_check.CheckError):
            vuln_check.advisory("../../x?y", lambda url, body=None: {})


class Checking(unittest.TestCase):
    def run_check(self, ignores=None, watch=("asterisk",)):
        return vuln_check.check(SBOM, ignores or {}, watch, FakeOsv(HITS, RECORDS))

    def test_findings_are_sorted_into_act_listed_and_withdrawn_ones_dropped(self):
        r = self.run_check()
        self.assertEqual([(f["id"], f["status"]) for f in r["findings"]],
                         [("MAL-2026-1", "act"), ("GHSA-aaaa-bbbb-cccc", "act"), ("UBUNTU-CVE-2026-9", "watch"), ("UBUNTU-CVE-2026-10", "listed")])
        flask = next(f for f in r["findings"] if f["package"] == "flask")
        self.assertEqual((flask["severity"], flask["fixed"], flask["aliases"]), ("high", ["3.1.4"], ["CVE-2026-0001"]))
        self.assertTrue(r["findings"][0]["malware"])
        self.assertEqual(next(f for f in r["findings"] if f["package"] == "asterisk")["severity"], "medium")
        self.assertEqual((len(r["act"]), len(r["watch"])), (2, 1))

    def test_two_binaries_of_one_source_package_are_one_finding(self):
        self.assertEqual(sum(1 for f in self.run_check()["findings"] if f["id"] == "UBUNTU-CVE-2026-9"), 1)

    def test_ubuntu_packages_never_fail_the_run_watched_or_not(self):
        # Watched ones are announced through the issue (TheIssue below); neither kind is in "act", which is the exit status.
        self.assertEqual({f["package"] for f in self.run_check(watch=())["act"]}, {"flask", "jssip"})
        self.assertEqual({f["package"] for f in self.run_check(watch=("asterisk", "sox"))["act"]}, {"flask", "jssip"})
        self.assertEqual({f["package"] for f in self.run_check(watch=("asterisk", "sox"))["watch"]}, {"asterisk", "sox"})
        only_os = {"components": [c for c in SBOM["components"] if c["name"].startswith("asterisk")]}
        r = vuln_check.check(only_os, {}, ("asterisk",), FakeOsv(HITS, RECORDS))
        self.assertEqual((r["act"], len(r["watch"])), ([], 1))

    def test_an_ignore_matches_by_alias_and_is_reported_and_unused_ones_are_named(self):
        ign = {"CVE-2026-0001": (datetime.date(2026, 12, 1), "not reachable: we never call that"), "GHSA-NOPE": (datetime.date(2026, 12, 1), "old")}
        r = self.run_check(ign)
        flask = next(f for f in r["findings"] if f["package"] == "flask")
        self.assertEqual((flask["status"], flask["ignore_reason"]), ("ignored", "not reachable: we never call that"))
        self.assertEqual(r["unused_ignores"], ["GHSA-NOPE"])
        text = vuln_check.report(r, TODAY)
        self.assertIn("Accepted for now", text)
        self.assertIn("`GHSA-NOPE`", text)

    def test_the_report_says_what_was_found_and_what_was_not_checked(self):
        text = vuln_check.report(self.run_check(), TODAY)
        self.assertIn("**2 findings to act on.**", text)
        self.assertIn("Watched Ubuntu packages", text)
        self.assertIn("**MALWARE**", text)
        self.assertIn("with a pipe".replace("with", "\\| with"), text)        # a `|` in a summary must not break the table
        self.assertIn("3.1.4", text)
        self.assertIn("Not checked here", text)
        self.assertIn("actions/checkout `v4`", text)
        clean = vuln_check.report(vuln_check.check({"components": [component("PyPI", "jinja2", "3.1.6")]}, {}, (), FakeOsv({}, {})), TODAY)
        self.assertIn("**Nothing to act on.**", clean)


class Ignores(unittest.TestCase):
    def test_a_good_file(self):
        got = vuln_check.parse_ignores("# why\n\nGHSA-aaaa-bbbb-cccc  until=2026-12-31  only in the debug server, which we never start\n", TODAY)
        self.assertEqual(got, {"GHSA-AAAA-BBBB-CCCC": (datetime.date(2026, 12, 31), "only in the debug server, which we never start")})

    def test_expired_too_far_and_malformed_entries_stop_the_check(self):
        for bad in ("GHSA-x until=2026-11-19 ran out yesterday", "GHSA-x until=2027-06-01 forever", "GHSA-x no date here",
                    "GHSA-x until=2026-12-01", "GHSA-x until=2026-13-45 reason"):
            with self.assertRaises(vuln_check.CheckError, msg=bad):
                vuln_check.parse_ignores(bad + "\n", TODAY)


class FakeGitHub:
    def __init__(self, issues):
        self.issues, self.calls = issues, []

    def __call__(self, args, body=None):
        self.calls.append((args, body))
        if args[0].startswith("repos/o/r/issues?"):
            return self.issues
        if args[:2] == ["-X", "POST"] and args[2] == "repos/o/r/issues":
            return {"number": 12}
        return {}


def issue(number, body, login="github-actions[bot]", kind="Bot", title=vuln_check.ISSUE_TITLE, **extra):
    return dict({"number": number, "title": title, "body": body, "user": {"login": login, "type": kind}}, **extra)


class TheIssue(unittest.TestCase):
    def setUp(self):
        self.result = vuln_check.check(SBOM, {}, ("asterisk",), FakeOsv(HITS, RECORDS))
        self.clean = vuln_check.check({"components": []}, {}, (), FakeOsv({}, {}))

    def test_first_finding_opens_an_issue(self):
        gh = FakeGitHub([])
        self.assertEqual(vuln_check.sync_issue("o/r", self.result, "REPORT", gh), "opened #12")
        args, body = gh.calls[-1]
        self.assertEqual((args, body["title"]), (["-X", "POST", "repos/o/r/issues"], vuln_check.ISSUE_TITLE))
        self.assertIn("<!-- treeline-vuln-ids: GHSA-aaaa-bbbb-cccc,MAL-2026-1,UBUNTU-CVE-2026-9 -->", body["body"])

    def test_a_new_finding_adds_a_comment_and_a_repeat_does_not(self):
        gh = FakeGitHub([issue(5, "old\n<!-- treeline-vuln-ids: GHSA-aaaa-bbbb-cccc,MAL-2026-1 -->")])
        self.assertEqual(vuln_check.sync_issue("o/r", self.result, "REPORT", gh), "updated #5, new: UBUNTU-CVE-2026-9")
        self.assertEqual([c[0][:3] for c in gh.calls[1:]], [["-X", "PATCH", "repos/o/r/issues/5"], ["-X", "POST", "repos/o/r/issues/5/comments"]])
        self.assertIn("(asterisk watched)", gh.calls[-1][1]["body"])
        gh = FakeGitHub([issue(5, "<!-- treeline-vuln-ids: GHSA-aaaa-bbbb-cccc,MAL-2026-1,UBUNTU-CVE-2026-9 -->")])
        self.assertEqual(vuln_check.sync_issue("o/r", self.result, "REPORT", gh), "updated #5, nothing new")
        self.assertEqual(len(gh.calls), 2)

    def test_a_clean_result_closes_it_and_does_nothing_when_none_is_open(self):
        gh = FakeGitHub([issue(5, "<!-- treeline-vuln-ids: X -->")])
        self.assertEqual(vuln_check.sync_issue("o/r", self.clean, "REPORT", gh), "clean, closed #5")
        self.assertEqual(gh.calls[-1][1]["state"], "closed")
        gh = FakeGitHub([])
        self.assertEqual(vuln_check.sync_issue("o/r", self.clean, "REPORT", gh), "clean, no issue open")
        self.assertEqual(len(gh.calls), 1)

    def test_someone_elses_issue_with_our_title_is_never_touched(self):
        # Anyone can open an issue in a public repo; ours is only the one the Actions bot opened. Pull requests are not issues.
        gh = FakeGitHub([issue(3, "x", login="stranger", kind="User"), issue(4, "x", login="github-actions[bot]", kind="User"),
                         issue(6, "x", pull_request={})])
        self.assertEqual(vuln_check.sync_issue("o/r", self.result, "REPORT", gh), "opened #12")

    def test_a_watched_ubuntu_finding_alone_opens_the_issue_but_is_not_a_failure(self):
        only_os = {"components": [c for c in SBOM["components"] if c["name"].startswith("asterisk")]}
        r = vuln_check.check(only_os, {}, ("asterisk",), FakeOsv(HITS, RECORDS))
        gh = FakeGitHub([])
        self.assertEqual(vuln_check.sync_issue("o/r", r, "REPORT", gh), "opened #12")
        self.assertEqual(r["act"], [])

    def test_a_very_long_report_is_cut_to_fit_an_issue(self):
        gh = FakeGitHub([])
        vuln_check.sync_issue("o/r", self.result, "x" * 200000, gh)
        self.assertLess(len(gh.calls[-1][1]["body"]), 65536)


class ExitCodes(unittest.TestCase):
    def run_main(self, fetch, sbom_doc=None, ignore_text=None):
        d = tempfile.mkdtemp()
        path = os.path.join(d, "sbom.json")
        with open(path, "w") as f:
            json.dump(SBOM if sbom_doc is None else sbom_doc, f)
        ign = os.path.join(d, ".vuln-ignore")
        if ignore_text is not None:
            with open(ign, "w") as f:
                f.write(ignore_text)
        real, vuln_check.http_json = vuln_check.http_json, fetch
        out, sys.stdout = sys.stdout, open(os.devnull, "w")
        err, sys.stderr = sys.stderr, open(os.devnull, "w")
        try:
            return vuln_check.main([path, "--ignore-file", ign, "--report", os.path.join(d, "r.md")])
        finally:
            sys.stdout.close(); sys.stderr.close()
            sys.stdout, sys.stderr, vuln_check.http_json = out, err, real

    def test_findings_are_1_and_clean_is_0(self):
        self.assertEqual(self.run_main(FakeOsv(HITS, RECORDS)), 1)
        self.assertEqual(self.run_main(FakeOsv({}, {})), 0)

    def test_a_check_that_could_not_run_is_2_never_0(self):
        def down(url, body=None, timeout=60):
            raise vuln_check.CheckError("could not reach OSV")
        self.assertEqual(self.run_main(down), 2)
        self.assertEqual(self.run_main(FakeOsv({}, {}), ignore_text="GHSA-x until=2020-01-01 long gone\n"), 2)
        self.assertEqual(self.run_main(FakeOsv({}, {}), sbom_doc={"components": [component("Ubuntu", "x", "1")]}), 2)


if __name__ == "__main__":
    unittest.main()
