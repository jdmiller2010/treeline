from aws_cdk import Duration, Stack, aws_lightsail as lightsail, aws_route53 as route53
from constructs import Construct

from . import config

P = lightsail.CfnInstance.PortProperty


def ports(cfg):
    """The IPv4 firewall, nothing else. Lightsail has a separate IPv6 firewall; its rules are replaced with this list too,
    and none of these has an IPv6 CIDR, so it is closed. 5061/tcp stays closed until an adapter is tried."""
    everyone = ["0.0.0.0/0"]
    narrowed = cfg["beta_cidrs"] or everyone              # the optional beta allowlist (SSM /treeline/beta_cidrs); empty = open
    return [
        P(protocol="tcp", from_port=22, to_port=22, cidrs=[cfg["admin_cidr"]]),
        P(protocol="tcp", from_port=80, to_port=80, cidrs=everyone),              # ACME and the redirect: always open
        P(protocol="tcp", from_port=443, to_port=443, cidrs=narrowed),
        P(protocol="udp", from_port=10000, to_port=10100, cidrs=narrowed),        # call audio
    ]


class Host(Stack):
    """Replaceable: delete and recreate it freely; the state disk, the bucket and the mail identity are in Foundation."""

    def __init__(self, scope: Construct, cid: str, *, cfg: dict, **kwargs):
        super().__init__(scope, cid, **kwargs)
        self.instance = lightsail.CfnInstance(
            self, "Instance",
            instance_name=config.INSTANCE_NAME, blueprint_id=config.BLUEPRINT_ID, bundle_id=cfg["bundle_id"],
            availability_zone=cfg["zone"], key_pair_name=cfg["key_pair"],
            hardware=lightsail.CfnInstance.HardwareProperty(
                disks=[lightsail.CfnInstance.DiskProperty(disk_name=config.STATE_DISK_NAME, path=config.STATE_DISK_PATH)]),
            networking=lightsail.CfnInstance.NetworkingProperty(ports=ports(cfg)),
        )
        self.ip = lightsail.CfnStaticIp(self, "Ip", static_ip_name=config.STATIC_IP_NAME, attached_to=self.instance.instance_name)
        self.ip.add_resource_dependency(self.instance)

        zone = route53.HostedZone.from_hosted_zone_attributes(self, "Zone", hosted_zone_id=cfg["zone_id"], zone_name=config.ZONE_NAME)
        for rid, name in (("App", cfg["app_host"]), ("Apex", config.ZONE_NAME)):     # the bare domain redirects to the app host
            # a short TTL: a replaced host gets a new address, and clients should follow within minutes, not half an hour
            route53.ARecord(self, rid, zone=zone, record_name=name + ".", ttl=Duration.seconds(config.DNS_TTL_SECONDS),
                            target=route53.RecordTarget.from_ip_addresses(self.ip.attr_ip_address))
