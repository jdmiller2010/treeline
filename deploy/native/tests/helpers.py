"""Load the root-run tools (scripts without a .py extension) as modules, and make test releases."""

import gzip
import importlib.machinery
import importlib.util
import io
import os
import pathlib
import subprocess
import sys
import tarfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
BIN = ROOT / "deploy" / "native" / "bin"
sys.path.insert(0, str(BIN))


def load(name):
    path = str(BIN / name)
    loader = importlib.machinery.SourceFileLoader(name.replace("-", "_"), path)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def keygen(directory, name="key"):
    key = pathlib.Path(directory) / name
    subprocess.run(["ssh-keygen", "-t", "ed25519", "-N", "", "-q", "-f", str(key), "-C", "test"], check=True)
    pub = pathlib.Path(str(key) + ".pub").read_text().strip()
    signers = pathlib.Path(directory) / f"{name}.signers"
    signers.write_text(f'treeline-release namespaces="treeline-release" {pub}\n')
    return key, signers


ID = "24.0.0-t1"


def tar_bytes(members):
    """members: list of (name, kind, payload, mode); kind in d f l h(ard link) c(har device)."""
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.GNU_FORMAT) as tf:
        for name, kind, payload, mode in members:
            ti = tarfile.TarInfo(name)
            ti.mtime = 0
            if kind == "d":
                ti.type, ti.mode = tarfile.DIRTYPE, mode if mode is not None else 0o755
                tf.addfile(ti)
            elif kind == "f":
                data = payload if isinstance(payload, bytes) else payload.encode()
                ti.size, ti.mode = len(data), mode if mode is not None else 0o644
                tf.addfile(ti, io.BytesIO(data))
            elif kind == "l":
                ti.type, ti.linkname, ti.mode = tarfile.SYMTYPE, payload, 0o777
                tf.addfile(ti)
            elif kind == "h":
                ti.type, ti.linkname, ti.mode = tarfile.LNKTYPE, payload, 0o644
                tf.addfile(ti)
            elif kind == "c":
                ti.type, ti.devmajor, ti.devminor, ti.mode = tarfile.CHRTYPE, 1, 3, 0o600
                tf.addfile(ti)
    out = io.BytesIO()
    with gzip.GzipFile(fileobj=out, mode="wb", mtime=0) as gz:
        gz.write(raw.getvalue())
    return out.getvalue()


def good_members(ast_id=ID, binary=b"#!not really elf\n"):
    p = f"opt/asterisk/{ast_id}"
    return [
        (p, "d", None, None), (f"{p}/sbin", "d", None, None), (f"{p}/sbin/asterisk", "f", binary, 0o755),
        (f"{p}/sbin/rasterisk", "l", "asterisk", None),
        (f"{p}/lib", "d", None, None), (f"{p}/lib/libasteriskpj.so.2", "f", b"pj", 0o755),
        (f"{p}/lib/libasteriskpj.so", "l", "libasteriskpj.so.2", None),
        (f"{p}/lib/asterisk", "d", None, None), (f"{p}/lib/asterisk/modules", "d", None, None),
        (f"{p}/lib/asterisk/modules/res_pjsip.so", "f", b"module", 0o755),
        (f"{p}/share", "d", None, None), (f"{p}/share/asterisk", "d", None, None),
        (f"{p}/share/asterisk/rest-api", "d", None, None), (f"{p}/share/asterisk/rest-api/channels.json", "f", "{}", None),
        (f"{p}/share/asterisk/documentation", "d", None, None), (f"{p}/share/asterisk/documentation/core.xml", "f", "<x/>", None),
    ]


def artifact(directory, ast_id=ID, members=None):
    """A small stand-in for the Asterisk build, with the real layout, written as asterisk-<id>.tar.gz."""
    path = pathlib.Path(directory) / f"asterisk-{ast_id}.tar.gz"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(tar_bytes(members if members is not None else good_members(ast_id)))
    return path


def sign(tarball, key):
    """Sign a release tarball the way scripts/build_release.sh --sign does (the script refuses to sign a test artifact)."""
    tarball = pathlib.Path(tarball)
    sig = pathlib.Path(str(tarball) + ".sig")
    if sig.exists():
        sig.unlink()
    subprocess.run(["ssh-keygen", "-Y", "sign", "-q", "-f", str(key), "-n", "treeline-release", str(tarball)], check=True)
    return sig


def build(version, out, key=None, env=None, asterisk=None, extra=()):
    """Build a release with a stand-in Asterisk (--asterisk-unlocked), and sign it here if a key is given."""
    out = pathlib.Path(out)
    asterisk = asterisk or artifact(out / "ast")
    cmd = [str(ROOT / "scripts" / "build_release.sh"), version, "--allow-dirty", "--out", str(out),
           "--asterisk-unlocked", str(asterisk), *extra]
    done = subprocess.run(cmd, capture_output=True, text=True, env=dict(os.environ, **(env or {})))
    if done.returncode != 0:
        raise AssertionError(done.stdout + done.stderr)
    tarball = out / f"treeline-{version}.tar.gz"
    if key:
        sign(tarball, key)
    return tarball
