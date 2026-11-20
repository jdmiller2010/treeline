"""Load the root-run tools (scripts without a .py extension) as modules, and make test releases."""

import importlib.machinery
import importlib.util
import os
import pathlib
import subprocess
import sys

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


def build(version, out, key=None, env=None):
    cmd = [str(ROOT / "scripts" / "build_release.sh"), version, "--allow-dirty", "--out", str(out)]
    if key:
        cmd += ["--sign", str(key)]
    done = subprocess.run(cmd, capture_output=True, text=True, env=dict(os.environ, **(env or {})))
    if done.returncode != 0:
        raise AssertionError(done.stdout + done.stderr)
    return pathlib.Path(out) / f"treeline-{version}.tar.gz"
