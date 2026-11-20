"""Treeline's AWS infrastructure (CDK, Python). Two stacks, see docs/DEPLOY_AWS.md work package 6:

  Foundation  retained: the backup bucket, the mail identity (DKIM), the state disk, a budget alert
  Host        replaceable: the Lightsail instance, its static IP, the firewall, the disk attachment, the DNS records
"""
