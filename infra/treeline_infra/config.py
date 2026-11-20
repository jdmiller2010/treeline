"""Everything environment-specific comes from the environment at deploy time (infra/deploy.sh reads SSM and the account),
never from a file in this repository: docs/REPO_RULES.md. Names that must match other code are constants here, and the tests
check them against infra/bootstrap/bootstrap.sh."""

import ipaddress
import os
import re

REGION = "us-west-2"
ZONE_NAME = "treelinephone.com"
DEFAULT_APP_HOST = "app.treelinephone.com"
BUCKET_PREFIX = "treeline-backups"          # the bucket is <prefix>-<account>-<region>; bootstrap.sh's BUCKET_BASE
STATE_DISK_NAME = "treeline-state"
INSTANCE_NAME = "treeline-vm"
STATIC_IP_NAME = "treeline-ip"
STATE_DISK_PATH = "/dev/xvdf"
STATE_DISK_GB = 8                           # Lightsail's smallest disk; the databases are small. Grow it here (never shrinks).
BACKUP_RETENTION_DAYS = 7
BLUEPRINT_ID = "ubuntu_24_04"
DEFAULT_BUNDLE_ID = "nano_3_0"              # planned: the 0.5 GB bundle. Bundles and prices change: deploy.sh prints what it is
MONTHLY_BUDGET_USD = 20


class ConfigError(Exception):
    pass


def _cidr(value, what):
    try:
        net = ipaddress.ip_network(value.strip(), strict=False)
    except ValueError as err:
        raise ConfigError(f"{what}: {value!r} is not a network") from err
    if net.version != 4:
        raise ConfigError(f"{what}: {value!r} is IPv6; the firewall is IPv4 only (docs/DEPLOY_AWS.md requirement 7)")
    return str(net)


def from_environment(env=None):
    env = os.environ if env is None else env
    missing = [k for k in ("TREELINE_ADMIN_CIDR", "TREELINE_ALERT_EMAIL", "TREELINE_HOSTED_ZONE_ID") if not env.get(k)]
    if missing:
        raise ConfigError("set " + ", ".join(missing) + " (infra/deploy.sh reads them from SSM and Route 53)")
    admin = _cidr(env["TREELINE_ADMIN_CIDR"], "TREELINE_ADMIN_CIDR")
    if admin in ("0.0.0.0/0",) or ipaddress.ip_network(admin).prefixlen < 16:
        raise ConfigError("TREELINE_ADMIN_CIDR must be your own address (SSH is never open to the world)")
    beta = [_cidr(c, "TREELINE_BETA_CIDRS") for c in env.get("TREELINE_BETA_CIDRS", "").split(",") if c.strip()]
    email = env["TREELINE_ALERT_EMAIL"].strip()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise ConfigError("TREELINE_ALERT_EMAIL is not an email address")
    zone_id = env["TREELINE_HOSTED_ZONE_ID"].strip()
    if not re.match(r"^Z[A-Z0-9]{6,31}$", zone_id):
        raise ConfigError("TREELINE_HOSTED_ZONE_ID does not look like a Route 53 zone id")
    host = env.get("TREELINE_APP_HOST", DEFAULT_APP_HOST).strip().lower()
    if not host.endswith("." + ZONE_NAME):
        raise ConfigError(f"TREELINE_APP_HOST must be inside {ZONE_NAME}")
    return {"admin_cidr": admin, "beta_cidrs": beta, "alert_email": email, "zone_id": zone_id, "app_host": host,
            "bundle_id": env.get("TREELINE_BUNDLE_ID", DEFAULT_BUNDLE_ID), "key_pair": env.get("TREELINE_SSH_KEY_PAIR") or None,
            "zone": az(env)}


def az(env):
    return env.get("TREELINE_AZ", REGION + "a")
