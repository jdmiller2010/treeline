"""The Asterisk build inside a release: what is accepted, and the many things that must be refused. No root, no Docker."""

import gzip
import hashlib
import json
import os
import pathlib
import shutil
import struct
import tarfile
import tempfile
import unittest

import helpers
from helpers import good_members, tar_bytes  # noqa: F401
import treeline_common as common  # noqa: E402
import treeline_release as rel  # noqa: E402

ID = helpers.ID
PREFIX = f"opt/asterisk/{ID}"


def make_release(root, data, ast_id=ID, sha=None, fmt=2, asterisk="default", extra_runtime=()):
    root = pathlib.Path(root)
    root.mkdir(parents=True, exist_ok=True)
    runtime = root / "asterisk" / "runtime"
    runtime.mkdir(parents=True)
    (runtime / f"asterisk-{ast_id}.tar.gz").write_bytes(data)
    for name in extra_runtime:
        (runtime / name).write_bytes(b"x")
    info = {"version": "v1.2.3", "schema": {"central": 1, "household": 1}, "format": fmt}
    if asterisk == "default":
        info["asterisk"] = {"id": ast_id, "sha256": sha or hashlib.sha256(data).hexdigest()}
    elif asterisk is not None:
        info["asterisk"] = asterisk
    (root / "release.json").write_text(json.dumps(info))
    return root


class Base(unittest.TestCase):
    def setUp(self):
        self.d = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.d, True)
        self.opt = self.d / "opt-asterisk"

    def release(self, members=None, **kw):
        data = tar_bytes(members if members is not None else good_members())
        return make_release(self.d / f"rel{len(list(self.d.iterdir()))}", data, **kw)

    def install(self, release):
        return rel.install_asterisk(str(release), opt=str(self.opt))

    def refuses(self, release, text=None):
        with self.assertRaises(rel.ReleaseError) as cm:
            self.install(release)
        if text:
            self.assertIn(text, str(cm.exception))
        self.assertFalse(any(n.startswith(".staging-") for n in os.listdir(self.opt)) if self.opt.exists() else False,
                         "a refused install must leave no staging directory")
        self.assertFalse((self.opt / ID).exists())


class ReadInfo(Base):
    def info(self, **kw):
        return rel.read_info(str(make_release(self.d / "ri", tar_bytes(good_members()), **kw)))

    def test_a_format_2_release_with_an_asterisk_is_read(self):
        self.assertEqual(self.info()["asterisk"]["id"], ID)

    def test_format_1_and_everything_else_is_refused_with_a_message_that_says_nothing_changed(self):
        for bad in (1, 3, "2", 2.0, True, None, [2]):
            shutil.rmtree(self.d / "ri", ignore_errors=True)
            with self.assertRaises(rel.ReleaseError, msg=repr(bad)) as cm:
                self.info(fmt=bad)
            self.assertIn("Nothing on this machine was changed", str(cm.exception))

    def test_the_asterisk_field_must_be_exactly_an_id_and_a_sha256(self):
        good = hashlib.sha256(b"x").hexdigest()
        for bad in (None, "x", [], {}, {"id": ID}, {"sha256": good}, {"id": ID, "sha256": good, "extra": 1},
                    {"id": "24.0.0", "sha256": good}, {"id": "24.0.0-t1\n", "sha256": good}, {"id": "../x-t1", "sha256": good},
                    {"id": ID, "sha256": good.upper()}, {"id": ID, "sha256": good[:-1]}, {"id": 5, "sha256": good},
                    {"id": ID, "sha256": 5}):
            shutil.rmtree(self.d / "ri", ignore_errors=True)
            with self.assertRaises(rel.ReleaseError, msg=repr(bad)):
                self.info(asterisk=bad)

    def test_a_test_id_is_refused_unless_this_is_the_ci_job(self):
        good = hashlib.sha256(b"x").hexdigest()
        for ident in ("24.0.0-t9", "24.0.0-t91"):
            shutil.rmtree(self.d / "ri", ignore_errors=True)
            folder = make_release(self.d / "ri", tar_bytes(good_members(ident)), ast_id=ident)
            with self.assertRaises(rel.ReleaseError):
                rel.read_info(str(folder))
            self.assertEqual(rel.read_info(str(folder), ci=True)["asterisk"]["id"], ident)
        shutil.rmtree(self.d / "ri", ignore_errors=True)
        make_release(self.d / "ri", tar_bytes(good_members("24.0.0-t19")), ast_id="24.0.0-t19")   # t19 is a real build number
        rel.read_info(str(self.d / "ri"))
        self.assertTrue(good)


class Install(Base):
    def test_a_good_artifact_is_installed_exactly(self):
        r = self.release()
        self.assertTrue(self.install(r))
        tree = self.opt / ID
        self.assertTrue((tree / "sbin" / "asterisk").is_file())
        self.assertEqual(os.readlink(tree / "sbin" / "rasterisk"), "asterisk")
        self.assertEqual(os.readlink(tree / "share" / "asterisk" / "sounds"), rel.ASTERISK_SOUNDS_LINK)
        self.assertEqual(oct((tree / "sbin" / "asterisk").stat().st_mode & 0o777), "0o755")
        self.assertEqual(oct((tree / "lib" / "asterisk" / "modules" / "res_pjsip.so").stat().st_mode & 0o777), "0o755")
        self.assertEqual(oct((tree / "share" / "asterisk" / "rest-api" / "channels.json").stat().st_mode & 0o777), "0o644")
        self.assertEqual(sorted(n for n in os.listdir(self.opt)), [ID])           # no staging left behind

    def test_installing_again_is_a_no_op_that_checks_the_tree(self):
        r = self.release()
        self.assertTrue(self.install(r))
        self.assertFalse(self.install(r))

    def test_the_same_id_with_different_bytes_is_refused(self):
        self.install(self.release())
        other = self.release(good_members(binary=b"a different build\n"))
        with self.assertRaises(rel.ReleaseError):
            self.install(other)
        self.assertEqual((self.opt / ID / "sbin" / "asterisk").read_bytes(), b"#!not really elf\n")

    def test_a_tampered_or_extra_file_in_an_installed_tree_is_found(self):
        r = self.release()
        self.install(r)
        tree = self.opt / ID
        victim = tree / "sbin" / "asterisk"
        original = victim.read_bytes()
        for what in ("changed", "truncated", "mode", "extra", "link", "missing"):
            if what == "changed":
                victim.write_bytes(original.replace(b"not", b"NOT"))
            elif what == "truncated":
                victim.write_bytes(original[:3])
            elif what == "mode":
                os.chmod(victim, 0o4755)
            elif what == "extra":
                (tree / "lib" / "evil.so").write_bytes(b"x")
            elif what == "link":
                os.symlink("/etc/passwd", tree / "lib" / "l")
            elif what == "missing":
                os.remove(tree / "lib" / "libasteriskpj.so.2")
            with self.assertRaises(rel.ReleaseError, msg=what):
                rel.verify_asterisk_tree(str(tree), str(r), rel.read_info(str(r)))
            shutil.rmtree(tree)
            self.install(r)
            victim = tree / "sbin" / "asterisk"

    def test_tampered_nested_bytes_inside_a_release_are_refused_before_anything_is_unpacked(self):
        r = self.release()
        path = r / "asterisk" / "runtime" / f"asterisk-{ID}.tar.gz"
        path.write_bytes(path.read_bytes()[:-1] + b"!")
        self.refuses(r, "does not match the sha256")

    def test_a_release_whose_sha_names_another_artifact_is_refused(self):
        self.refuses(self.release(sha=hashlib.sha256(b"something else").hexdigest()), "does not match the sha256")

    def test_the_artifact_must_be_the_only_file_and_a_regular_file(self):
        self.refuses(self.release(extra_runtime=["note.txt"]), "must hold exactly")
        r = self.release()
        path = r / "asterisk" / "runtime" / f"asterisk-{ID}.tar.gz"
        data = path.read_bytes()
        path.unlink()
        other = self.d / "elsewhere.tar.gz"
        other.write_bytes(data)
        os.symlink(other, path)
        self.refuses(r)

    def test_a_missing_runtime_directory_is_refused(self):
        r = self.release()
        shutil.rmtree(r / "asterisk")
        self.refuses(r, "no asterisk/runtime")

    def test_an_id_that_does_not_match_the_paths_inside_is_refused(self):
        self.refuses(self.release(good_members("24.0.0-t2")), "outside opt/asterisk/")

    def test_hostile_archives_are_refused(self):
        p = PREFIX
        extra = {
            "absolute path": [("/etc/cron.d/x", "f", "x", None)],
            "parent path": [(f"{p}/../../etc/x", "f", "x", None)],
            "dot path": [(f"{p}/./x", "f", "x", None)],
            "outside the prefix": [("opt/other/x", "f", "x", None)],
            "relative link out": [(f"{p}/lib/x", "l", "../../../../etc/passwd", None)],
            "absolute link": [(f"{p}/lib/x", "l", "/etc/passwd", None)],
            "link to a non-sibling": [(f"{p}/lib/x", "l", "asterisk/modules/res_pjsip.so", None)],
            "link to nothing": [(f"{p}/lib/x", "l", "nothing-here", None)],
            "link to dot": [(f"{p}/lib/x", "l", ".", None)],
            "hard link": [(f"{p}/lib/x", "h", f"{p}/sbin/asterisk", None)],
            "device": [(f"{p}/lib/x", "c", None, None)],
            "setuid file": [(f"{p}/lib/x", "f", "x", 0o4755)],
            "setgid file": [(f"{p}/lib/x", "f", "x", 0o2755)],
            "group writable": [(f"{p}/lib/x", "f", "x", 0o775)],
            "world writable dir": [(f"{p}/lib/w", "d", None, 0o777)],
            "sticky": [(f"{p}/lib/x", "f", "x", 0o1755)],
            "duplicate": [(f"{p}/sbin/asterisk", "f", "second", 0o755)],
            "control character": [(f"{p}/lib/a\nb", "f", "x", None)],
            "backslash": [(f"{p}/lib/a\\b", "f", "x", None)],
        }
        for what, more in extra.items():
            with self.subTest(what):
                shutil.rmtree(self.opt, ignore_errors=True)
                r = self.release(good_members() + more)
                with self.assertRaises(rel.ReleaseError):
                    self.install(r)
                self.assertFalse(any(n.startswith(".staging-") for n in os.listdir(self.opt)) if self.opt.exists() else False)
                self.assertFalse((self.opt / ID).exists())

    def test_a_path_that_goes_through_a_link_is_refused(self):
        p = PREFIX
        members = good_members() + [(f"{p}/lib/a", "l", "asterisk", None), (f"{p}/lib/a/evil.so", "f", "x", None)]
        self.refuses(self.release(members))

    def test_a_missing_required_part_is_refused(self):
        for gone in ("sbin/asterisk", "sbin/rasterisk", "lib/asterisk/modules", "share/asterisk/rest-api", "share/asterisk/documentation"):
            members = [m for m in good_members() if not (m[0] == f"{PREFIX}/{gone}" or m[0].startswith(f"{PREFIX}/{gone}/"))]
            with self.subTest(gone):
                shutil.rmtree(self.opt, ignore_errors=True)
                with self.assertRaises(rel.ReleaseError):
                    self.install(self.release(members))

    def test_a_size_bomb_and_a_member_flood_are_refused(self):
        many = good_members() + [(f"{PREFIX}/lib/f{i}", "f", "x", None) for i in range(rel.ASTERISK_MAX_MEMBERS + 1)]
        self.refuses(self.release(many), "implausibly large")
        big = good_members() + [(f"{PREFIX}/lib/big", "f", b"\0" * (rel.ASTERISK_MAX_BYTES + 1), None)]
        with self.assertRaises(rel.ReleaseError):
            self.install(self.release(big))

    def test_garbage_is_refused_cleanly(self):
        for blob in (b"", b"not a tar", gzip.compress(b"also not a tar")):
            shutil.rmtree(self.opt, ignore_errors=True)
            r = make_release(self.d / f"g{len(blob)}", blob)
            with self.assertRaises(rel.ReleaseError):
                self.install(r)

    def test_a_leftover_staging_directory_is_not_overwritten_and_is_swept_under_the_lock(self):
        self.opt.mkdir()
        leftover = self.opt / f".staging-{os.getpid()}"
        leftover.mkdir()
        with self.assertRaises(rel.ReleaseError):
            self.install(self.release())
        self.assertEqual(rel.sweep_asterisk(str(self.opt)), [leftover.name] if False else [f".staging-{os.getpid()}"])
        self.assertTrue(self.install(self.release()))

    def test_nothing_is_installed_by_a_failed_install_and_an_existing_good_tree_is_untouched(self):
        self.install(self.release())
        before = rel.tree_actual(str(self.opt / ID))
        bad = self.release(good_members("24.0.0-t2") + [(f"opt/asterisk/24.0.0-t2/lib/x", "h", "opt/asterisk/24.0.0-t2/sbin/asterisk", None)],
                           ast_id="24.0.0-t2")
        with self.assertRaises(rel.ReleaseError):
            rel.install_asterisk(str(bad), opt=str(self.opt))
        self.assertEqual(rel.tree_actual(str(self.opt / ID)), before)
        self.assertEqual(sorted(os.listdir(self.opt)), [ID])


class Sweep(Base):
    def test_old_builds_go_and_the_ones_named_stay(self):
        self.opt.mkdir()
        for name in ("24.0.0-t1", "24.0.0-t2", "24.0.0-t3", "not-a-build", ".staging-1", ".trash-2-old"):
            (self.opt / name).mkdir()
            (self.opt / name / "f").write_text("x")
        removed = rel.sweep_asterisk(str(self.opt), keep=("24.0.0-t2", "24.0.0-t3"))
        self.assertEqual(sorted(removed), [".staging-1", ".trash-2-old", "24.0.0-t1"])
        self.assertEqual(sorted(os.listdir(self.opt)), ["24.0.0-t2", "24.0.0-t3", "not-a-build"])

    def test_a_missing_directory_is_fine(self):
        self.assertEqual(rel.sweep_asterisk(str(self.d / "nope")), [])


# ---------------------------------------------------------------- reading ELF files
def fake_elf(needed=(), runpath=None, rpath=None, interp="/lib64/ld-linux-x86-64.so.2"):
    """A minimal 64-bit LE ELF with one PT_LOAD, a PT_INTERP, and a PT_DYNAMIC: enough for elf_dynamic to read."""
    strs, offs = b"\0", {}
    for s in list(needed) + [x for x in (runpath, rpath) if x is not None]:
        offs[s] = len(strs)
        strs += s.encode() + b"\0"
    dyn = b""
    for n in needed:
        dyn += struct.pack("<qQ", 1, offs[n])
    if runpath is not None:
        dyn += struct.pack("<qQ", 29, offs[runpath])
    if rpath is not None:
        dyn += struct.pack("<qQ", 15, offs[rpath])
    base = 64 + 56 * 3
    interp_b = interp.encode() + b"\0"
    str_off = base + len(interp_b)
    dyn_off = str_off + len(strs)
    dyn += struct.pack("<qQ", 5, str_off) + struct.pack("<qQ", 0, 0)       # DT_STRTAB (a virtual address == its file offset), DT_NULL
    total = dyn_off + len(dyn)
    hdr = b"\x7fELF" + bytes([2, 1, 1, 0]) + b"\0" * 8 + struct.pack("<HHIQQQIHHHHHH", 3, 62, 1, 0, 64, 0, 0, 64, 56, 3, 0, 0, 0)
    ph = struct.pack("<IIQQQQQQ", 1, 5, 0, 0, 0, total, total, 0x1000)                         # PT_LOAD of the whole file
    ph += struct.pack("<IIQQQQQQ", 3, 4, base, base, base, len(interp_b), len(interp_b), 1)    # PT_INTERP
    ph += struct.pack("<IIQQQQQQ", 2, 6, dyn_off, dyn_off, dyn_off, len(dyn), len(dyn), 8)     # PT_DYNAMIC
    return hdr + ph + interp_b + strs + dyn


class Elf(Base):
    def tree(self, **files):
        t = self.d / "tree"
        (t / "lib").mkdir(parents=True)
        (t / "sbin").mkdir()
        for name, blob in files.items():
            (t / name.replace("__", "/")).write_bytes(blob)
        return t

    def test_the_headers_of_a_real_looking_elf_are_read(self):
        p = self.d / "x"
        p.write_bytes(fake_elf(needed=["libc.so.6", "libasteriskpj.so.2"], runpath=f"/opt/asterisk/{ID}/lib"))
        got = rel.elf_dynamic(str(p))
        self.assertEqual(got["needed"], ["libc.so.6", "libasteriskpj.so.2"])
        self.assertEqual(got["runpath"], [f"/opt/asterisk/{ID}/lib"])
        self.assertEqual(got["rpath"], [])

    def test_a_good_build_passes(self):
        system = self.d / "sys"
        system.mkdir()
        (system / "libc.so.6").write_bytes(b"")
        t = self.tree(sbin__asterisk=fake_elf(["libc.so.6", "libx.so.1"], f"/opt/asterisk/{ID}/lib"), lib__libx_so_1=b"")
        (t / "lib" / "libx.so.1").write_bytes(b"")
        rel.check_elf_needs(str(t), ID, system_dirs=(str(system),))

    def test_what_must_be_refused(self):
        system = self.d / "sys"
        system.mkdir()
        (system / "libc.so.6").write_bytes(b"")
        right = f"/opt/asterisk/{ID}/lib"
        cases = {
            "an RPATH": fake_elf(["libc.so.6"], right, rpath="/tmp"),
            "an $ORIGIN runpath": fake_elf(["libc.so.6"], "$ORIGIN/../lib"),
            "the wrong build's runpath": fake_elf(["libc.so.6"], "/opt/asterisk/24.0.0-t2/lib"),
            "two runpath entries": fake_elf(["libc.so.6"], right + ":/tmp"),
            "a library named by a path": fake_elf(["/tmp/evil.so"], right),
            "a library nobody has": fake_elf(["libmissing.so.9"], right),
            "an odd interpreter": fake_elf(["libc.so.6"], right, interp="/tmp/ld.so"),
        }
        for what, blob in cases.items():
            with self.subTest(what):
                shutil.rmtree(self.d / "tree", ignore_errors=True)
                t = self.tree(sbin__asterisk=blob)
                with self.assertRaises(rel.ReleaseError):
                    rel.check_elf_needs(str(t), ID, system_dirs=(str(system),))

    def test_a_file_that_is_not_elf_is_not_a_library_problem_but_a_broken_elf_is_an_error(self):
        t = self.tree(sbin__script=b"#!/bin/sh\n")
        rel.check_elf_needs(str(t), ID, system_dirs=())
        with self.assertRaises(rel.ReleaseError):
            p = self.d / "bad"
            p.write_bytes(b"\x7fELF\x01\x01\x01" + b"\0" * 100)       # 32-bit
            rel.elf_dynamic(str(p))


class BuildRelease(Base):
    """scripts/build_release.sh: what it refuses, and that what it makes is exactly what the agent installs."""

    def run_build(self, *args, version="v0.0.9"):
        import subprocess
        out = self.d / "out"
        done = subprocess.run([str(helpers.ROOT / "scripts" / "build_release.sh"), version, "--allow-dirty", "--out", str(out), *args],
                              capture_output=True, text=True)
        return done, out

    def test_a_release_without_an_asterisk_is_refused(self):
        done, out = self.run_build()
        self.assertEqual(done.returncode, 2)
        self.assertIn("--asterisk", done.stderr)
        self.assertFalse(out.exists() and list(out.glob("*.tar.gz")))

    def test_an_unlocked_artifact_cannot_be_signed(self):
        key, _ = helpers.keygen(self.d)
        art = helpers.artifact(self.d / "a")
        done, out = self.run_build("--asterisk-unlocked", str(art), "--sign", str(key))
        self.assertEqual(done.returncode, 2)
        self.assertIn("cannot be combined with --sign", done.stderr)
        self.assertFalse(out.exists() and list(out.glob("*")))

    def test_a_file_that_is_not_the_locked_artifact_is_refused(self):
        art = helpers.artifact(self.d / "a")
        done, out = self.run_build("--asterisk", str(art))
        self.assertEqual(done.returncode, 1)
        self.assertIn("artifact.lock names", done.stderr)

    def test_a_link_instead_of_a_file_is_refused(self):
        art = helpers.artifact(self.d / "a")
        link = self.d / "link.tar.gz"
        os.symlink(art, link)
        done, _ = self.run_build("--asterisk-unlocked", str(link))
        self.assertEqual(done.returncode, 2)

    def test_a_hostile_artifact_is_refused_with_the_agents_own_reason(self):
        bad = helpers.artifact(self.d / "a", members=helpers.good_members() + [(f"{PREFIX}/lib/x", "h", f"{PREFIX}/sbin/asterisk", None)])
        done, out = self.run_build("--asterisk-unlocked", str(bad))
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("not acceptable", done.stderr)
        self.assertFalse(out.exists() and list(out.glob("*.tar.gz")))

    def test_an_unlocked_artifact_must_be_named_for_its_id(self):
        art = helpers.artifact(self.d / "a")
        odd = self.d / "whatever.tar.gz"
        shutil.copy(art, odd)
        done, _ = self.run_build("--asterisk-unlocked", str(odd))
        self.assertEqual(done.returncode, 2)

    def test_the_release_it_makes_carries_the_artifact_and_installs_exactly_what_was_built(self):
        key, signers = helpers.keygen(self.d)
        art = helpers.artifact(self.d / "a")
        done, out = self.run_build("--asterisk-unlocked", str(art), version="v0.0.9")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        tarball = out / "treeline-v0.0.9.tar.gz"
        helpers.sign(tarball, key)
        rel.verify(str(tarball), str(tarball) + ".sig", str(signers))
        folder = self.d / "unpacked"
        rel.extract(str(tarball), str(folder))
        info = rel.read_info(str(folder), ci=False)
        self.assertEqual(info["format"], 2)
        self.assertEqual(info["asterisk"], {"id": ID, "sha256": hashlib.sha256(art.read_bytes()).hexdigest()})
        self.assertEqual(os.listdir(folder / "asterisk" / "runtime"), [f"asterisk-{ID}.tar.gz"])
        self.assertEqual((folder / "asterisk" / "runtime" / f"asterisk-{ID}.tar.gz").read_bytes(), art.read_bytes())
        self.assertTrue((folder / "asterisk" / "SOURCE.txt").is_file())
        for name in ("ASTERISK-COPYING.txt", "PJPROJECT-COPYING.txt"):
            self.assertIn("GNU GENERAL PUBLIC LICENSE", (folder / "asterisk" / "licenses" / name).read_text())
        self.assertTrue((folder / "asterisk" / "build" / "build.sh").is_file())               # the GPL build instructions travel with it
        for left_out in ("Dockerfile", "entrypoint.sh", "runtime-deps.txt", "dev"):
            self.assertFalse((folder / "asterisk" / left_out).exists(), left_out)             # the dev image's files are not the VM's
        self.assertTrue(rel.install_asterisk(str(folder), opt=str(self.opt)))
        self.assertEqual((self.opt / ID / "sbin" / "asterisk").read_bytes(), good_members()[2][2])

    def test_the_same_inputs_give_the_same_release_bytes(self):
        art = helpers.artifact(self.d / "a")
        first, out1 = self.run_build("--asterisk-unlocked", str(art))
        data1 = (out1 / "treeline-v0.0.9.tar.gz").read_bytes()
        shutil.rmtree(out1)
        second, out2 = self.run_build("--asterisk-unlocked", str(art))
        self.assertEqual(first.returncode, 0)
        self.assertEqual(second.returncode, 0)
        self.assertEqual(data1, (out2 / "treeline-v0.0.9.tar.gz").read_bytes())


if __name__ == "__main__":
    unittest.main()
