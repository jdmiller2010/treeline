"""AWS access for the VM's root-run tools: one place that builds a boto3 client from the VM user's key file and reads SSM.

The key file is /etc/treeline/aws-credentials (root only). `/etc/treeline/aws-endpoint` exists only on the CI job's
install (install.sh --ci) and points boto3 at a fake; production never has that file.
"""

import os

import treeline_common as common

PREFIX = "/treeline"


def client(service, etc=None, region=None):
    etc = etc or common.ETC
    endpoint = os.path.join(etc, "aws-endpoint")
    if os.path.exists(endpoint) and common.host_settings(etc).get("TREELINE_CI") != "1":
        raise SystemExit(f"{endpoint} exists but this is not a CI install: refusing to send AWS calls anywhere but AWS")
    import boto3
    from botocore.config import Config
    os.environ["AWS_SHARED_CREDENTIALS_FILE"] = os.path.join(etc, "aws-credentials")
    os.environ["AWS_CONFIG_FILE"] = os.devnull
    os.environ.pop("AWS_PROFILE", None)
    kwargs = {"region_name": region or common.host_settings(etc).get("TREELINE_AWS_REGION", "us-west-2")}
    if os.path.exists(endpoint):
        with open(endpoint, encoding="utf-8") as f:
            kwargs["endpoint_url"] = f.read().strip()
        kwargs["config"] = Config(s3={"addressing_style": "path"})        # a fake has no wildcard DNS for bucket names
    session = boto3.session.Session(profile_name="treeline-vm")
    return session.client(service, **kwargs)


def fetch(ssm, mapping):
    """{ENV_NAME: value} for {ssm name under /treeline: ENV_NAME}; a missing parameter is a hard failure naming it."""
    names = [f"{PREFIX}/{n}" for n in mapping]
    got = ssm.get_parameters(Names=names, WithDecryption=True)
    have = {p["Name"] for p in got["Parameters"]}
    missing = sorted(set(got.get("InvalidParameters", [])) | {n for n in names if n not in have})
    if missing:
        raise SystemExit("missing SSM parameter(s): " + ", ".join(missing) + " (run infra/bootstrap/bootstrap.sh check)")
    values = {p["Name"][len(PREFIX) + 1:]: p["Value"] for p in got["Parameters"]}
    return {mapping[n]: values[n] for n in mapping}
