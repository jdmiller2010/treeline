"""Assertions on the synthesized CloudFormation templates. They run offline (no AWS account): what they can show is that the
template says what the spec says; whether AWS accepts it is the first real deploy."""

import json
import os
import pathlib
import re
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aws_cdk.assertions import Match, Template  # noqa: E402

import app as app_module  # noqa: E402
from treeline_infra import config  # noqa: E402

ENV = {"TREELINE_ADMIN_CIDR": "203.0.113.9/32", "TREELINE_ALERT_EMAIL": "owner@example.invalid", "TREELINE_HOSTED_ZONE_ID": "Z0123456789ABCDEFGHIJ"}


def templates(**over):
    app = app_module.build(dict(ENV, **over))
    return Template.from_stack(app.node.find_child("TreelineFoundation")), Template.from_stack(app.node.find_child("TreelineHost")), app


class Foundation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t, _, cls.app = templates()

    def bucket(self):
        (res,) = self.t.find_resources("AWS::S3::Bucket").values()
        return res

    def test_the_bucket_name_is_the_one_bootstrap_sh_gave_the_vms_policy(self):
        name = self.bucket()["Properties"]["BucketName"]
        self.assertEqual(name, {"Fn::Join": ["", [config.BUCKET_PREFIX + "-", {"Ref": "AWS::AccountId"}, "-", {"Ref": "AWS::Region"}]]})
        boot = (ROOT / "bootstrap" / "bootstrap.sh").read_text()
        self.assertIn(f'BUCKET_BASE="{config.BUCKET_PREFIX}"', boot)
        self.assertIn('BUCKET="${BUCKET_BASE}-${ACCOUNT}-${REGION}"', boot)
        self.assertIn(f'REGION="${{TREELINE_AWS_REGION:-{config.REGION}}}"', boot)

    def test_versioning_is_off(self):
        self.assertNotIn("VersioningConfiguration", self.bucket()["Properties"])

    def test_it_is_private_encrypted_and_kept(self):
        res = self.bucket()
        self.assertEqual(res["DeletionPolicy"], "Retain")
        props = res["Properties"]
        self.assertEqual(props["PublicAccessBlockConfiguration"], {"BlockPublicAcls": True, "BlockPublicPolicy": True, "IgnorePublicAcls": True, "RestrictPublicBuckets": True})
        self.assertEqual(props["BucketEncryption"]["ServerSideEncryptionConfiguration"][0]["ServerSideEncryptionByDefault"]["SSEAlgorithm"], "AES256")
        self.assertEqual(props["OwnershipControls"]["Rules"][0]["ObjectOwnership"], "BucketOwnerEnforced")

    def test_backups_expire_after_seven_days_under_both_prefixes(self):
        rules = {r["Id"]: r for r in self.bucket()["Properties"]["LifecycleConfiguration"]["Rules"]}
        for rid, prefix in (("central-expires", "central/"), ("households-expire", "households/")):
            self.assertEqual(rules[rid]["Prefix"], prefix)
            self.assertEqual(rules[rid]["ExpirationInDays"], 7)
            self.assertEqual(rules[rid]["Status"], "Enabled")

    def test_non_tls_requests_are_denied_by_the_bucket_policy(self):
        self.t.has_resource_properties("AWS::S3::BucketPolicy", {"PolicyDocument": {"Statement": Match.array_with([Match.object_like({
            "Effect": "Deny", "Action": "s3:*", "Condition": {"Bool": {"aws:SecureTransport": "false"}}})])}})

    def test_tls_older_than_1_2_is_denied_as_well_as_plain_http(self):
        (policy,) = self.t.find_resources("AWS::S3::BucketPolicy").values()
        conditions = [st.get("Condition", {}) for st in policy["Properties"]["PolicyDocument"]["Statement"] if st["Effect"] == "Deny"]
        self.assertIn({"Bool": {"aws:SecureTransport": "false"}}, conditions)
        self.assertIn({"NumericLessThan": {"s3:TlsVersion": 1.2}}, conditions)

    def test_only_lets_encrypt_may_issue_certificates_for_the_domain(self):
        (caa,) = [r for r in self.t.find_resources("AWS::Route53::RecordSet").values() if r["Properties"]["Type"] == "CAA"]
        self.assertEqual(caa["Properties"]["Name"], "treelinephone.com.")
        self.assertEqual(caa["Properties"]["ResourceRecords"], ['0 issue "letsencrypt.org"'])

    def test_the_existing_hosted_zone_is_imported_never_created(self):
        self.t.resource_count_is("AWS::Route53::HostedZone", 0)
        self.assertIn("Z0123456789ABCDEFGHIJ", json.dumps(self.t.to_json()))

    def test_mail_has_dkim_records_in_the_zone(self):
        self.t.resource_count_is("AWS::SES::EmailIdentity", 1)
        cnames = [r for r in self.t.find_resources("AWS::Route53::RecordSet").values() if r["Properties"]["Type"] == "CNAME"]
        self.assertGreaterEqual(len(cnames), 3)
        self.assertTrue(all("DkimDNSTokenName" in json.dumps(r["Properties"]["Name"]) for r in cnames), "the record names must come from SES's DKIM tokens")

    def test_the_state_disk_is_retained_and_named_as_the_host_expects(self):
        (disk,) = self.t.find_resources("AWS::Lightsail::Disk").values()
        self.assertEqual(disk["DeletionPolicy"], "Retain")
        self.assertEqual(disk["UpdateReplacePolicy"], "Retain")
        self.assertEqual(disk["Properties"]["DiskName"], config.STATE_DISK_NAME)
        self.assertEqual(disk["Properties"]["AvailabilityZone"], "us-west-2a")

    def test_there_is_a_budget_alert_to_the_owner(self):
        self.t.has_resource_properties("AWS::Budgets::Budget", {"NotificationsWithSubscribers": Match.array_with([Match.object_like(
            {"Subscribers": [{"SubscriptionType": "EMAIL", "Address": "owner@example.invalid"}]})])})

    def test_termination_protection_is_on(self):
        self.assertTrue(self.app.node.find_child("TreelineFoundation").termination_protection)


class Host(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, cls.t, _ = templates()

    def instance(self, t=None):
        (res,) = (t or self.t).find_resources("AWS::Lightsail::Instance").values()
        return res["Properties"]

    def rules(self, t=None):
        return {(p["Protocol"], p["FromPort"], p["ToPort"]): p for p in self.instance(t)["Networking"]["Ports"]}

    def test_the_instance_is_ubuntu_24_04_with_the_state_disk_attached(self):
        props = self.instance()
        self.assertEqual(props["BlueprintId"], "ubuntu_24_04")
        self.assertEqual(props["Hardware"]["Disks"], [{"DiskName": config.STATE_DISK_NAME, "Path": config.STATE_DISK_PATH}])
        self.assertEqual(props["AvailabilityZone"], "us-west-2a")

    def test_only_the_intended_ports_are_open(self):
        self.assertEqual(set(self.rules()), {("tcp", 22, 22), ("tcp", 80, 80), ("tcp", 443, 443), ("udp", 10000, 10100)})

    def test_ssh_is_the_owners_address_only_and_never_the_world(self):
        rules = self.rules()
        self.assertEqual(rules[("tcp", 22, 22)]["Cidrs"], ["203.0.113.9/32"])
        self.assertEqual(rules[("tcp", 80, 80)]["Cidrs"], ["0.0.0.0/0"])

    def test_no_ipv6_rule_exists_so_the_ipv6_firewall_is_closed(self):
        for rule in self.rules().values():
            self.assertNotIn("Ipv6Cidrs", rule)

    def test_sip_tls_stays_closed_until_an_adapter_is_tried(self):
        self.assertFalse([k for k in self.rules() if k[1] <= 5061 <= k[2] or k[1] <= 5060 <= k[2]])

    def test_the_optional_allowlist_narrows_443_and_the_media_range_but_never_80(self):
        _, t, _ = templates(TREELINE_BETA_CIDRS="198.51.100.0/24, 203.0.113.0/24")
        rules = self.rules(t)
        self.assertEqual(rules[("tcp", 443, 443)]["Cidrs"], ["198.51.100.0/24", "203.0.113.0/24"])
        self.assertEqual(rules[("udp", 10000, 10100)]["Cidrs"], ["198.51.100.0/24", "203.0.113.0/24"])
        self.assertEqual(rules[("tcp", 80, 80)]["Cidrs"], ["0.0.0.0/0"])

    def test_a_static_ip_is_attached_and_both_names_point_at_it(self):
        self.t.has_resource_properties("AWS::Lightsail::StaticIp", {"StaticIpName": config.STATIC_IP_NAME, "AttachedTo": config.INSTANCE_NAME})
        records = {json.dumps(r["Properties"]["Name"]): r for r in self.t.find_resources("AWS::Route53::RecordSet").values()}
        self.assertEqual({r["Properties"]["Name"] for r in records.values()}, {"app.treelinephone.com.", "treelinephone.com."})
        for r in records.values():
            self.assertEqual(r["Properties"]["Type"], "A")
            self.assertEqual(r["Properties"]["TTL"], "300", "a replaced host must be found again within minutes")
            self.assertIn("Fn::GetAtt", json.dumps(r["Properties"]["ResourceRecords"]))

    def test_the_host_does_not_own_anything_that_must_survive_it(self):
        for kind in ("AWS::S3::Bucket", "AWS::Lightsail::Disk", "AWS::SES::EmailIdentity", "AWS::Budgets::Budget"):
            self.t.resource_count_is(kind, 0)


class Settings(unittest.TestCase):
    def test_missing_or_dangerous_settings_stop_the_synth(self):
        for bad in ({"TREELINE_ADMIN_CIDR": ""}, {"TREELINE_ADMIN_CIDR": "0.0.0.0/0"}, {"TREELINE_ADMIN_CIDR": "10.0.0.0/8"},
                    {"TREELINE_ADMIN_CIDR": "2001:db8::/32"}, {"TREELINE_ALERT_EMAIL": "nope"}, {"TREELINE_HOSTED_ZONE_ID": "x"},
                    {"TREELINE_BETA_CIDRS": "not-a-cidr"}, {"TREELINE_APP_HOST": "app.evil.invalid"}):
            with self.assertRaises(config.ConfigError, msg=bad):
                config.from_environment(dict(ENV, **bad))

    def test_the_cdk_feature_flags_are_configured_not_left_to_legacy_defaults(self):
        """`cdk flags --safe --set` (flags that cannot change an existing resource). The synthesized resources were identical before and after."""
        flags = {k: v for k, v in json.loads((ROOT / "cdk.json").read_text())["context"].items() if k.startswith("@aws-cdk")}
        self.assertGreaterEqual(len(flags), 60)
        self.assertTrue(flags["@aws-cdk/aws-s3:createDefaultLoggingPolicy"])

    def test_nothing_environment_specific_is_in_the_repository(self):
        # (the repo-rules scan covers the whole tree; this is the CDK app's own check, and its templates carry no account either)
        for path in [ROOT / "app.py", *(ROOT / "treeline_infra").glob("*.py"), ROOT / "cdk.json"]:
            self.assertFalse(re.search(r"\b\d{12}\b", path.read_text()), f"{path} has a 12-digit number (an account id?)")
        _, _, app = templates()
        for template in (Template.from_stack(app.node.find_child(n)).to_json() for n in ("TreelineFoundation", "TreelineHost")):
            self.assertFalse(re.search(r"\b\d{12}\b", json.dumps(template)))

    def test_the_cdk_command_line_synthesizes_both_stacks_when_it_is_installed(self):
        cdk = ROOT / "node_modules" / ".bin" / "cdk"
        if not cdk.exists():
            self.skipTest("the pinned CDK CLI is not installed (npm ci in infra/)")
        out = pathlib.Path(os.environ.get("TMPDIR", "/tmp")) / "treeline-cdk-test-out"
        done = subprocess.run([str(cdk), "synth", "--quiet", "--output", str(out)], cwd=ROOT, env=dict(os.environ, **ENV), capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertTrue((out / "TreelineFoundation.template.json").exists())
        self.assertTrue((out / "TreelineHost.template.json").exists())


if __name__ == "__main__":
    unittest.main()
