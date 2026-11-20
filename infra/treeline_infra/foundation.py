from aws_cdk import Aws, Duration, RemovalPolicy, Stack, aws_budgets as budgets, aws_lightsail as lightsail, aws_route53 as route53, aws_s3 as s3, aws_ses as ses
from constructs import Construct

from . import config


class Foundation(Stack):
    """Retained: nothing here is replaced when the host is. Termination protection is on and everything is RETAIN."""

    def __init__(self, scope: Construct, cid: str, *, cfg: dict, **kwargs):
        super().__init__(scope, cid, termination_protection=True, **kwargs)

        # The name must be exactly what infra/bootstrap/bootstrap.sh computed for the VM's IAM policy and SSM.
        self.bucket = s3.Bucket(
            self, "Backups",
            bucket_name=f"{config.BUCKET_PREFIX}-{Aws.ACCOUNT_ID}-{Aws.REGION}",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,                                   # a bucket policy statement that denies every non-TLS request
            versioned=False,                                    # versioning would keep deleted households' data past 7 days
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[
                s3.LifecycleRule(id="central-expires", prefix="central/", expiration=Duration.days(config.BACKUP_RETENTION_DAYS)),
                s3.LifecycleRule(id="households-expire", prefix="households/", expiration=Duration.days(config.BACKUP_RETENTION_DAYS)),
                s3.LifecycleRule(id="abort-partial-uploads", abort_incomplete_multipart_upload_after=Duration.days(1)),
            ],
        )

        # The hosted zone already exists (the domain is registered in Route 53): import it, never create one.
        self.zone = route53.HostedZone.from_hosted_zone_attributes(self, "Zone", hosted_zone_id=cfg["zone_id"], zone_name=config.ZONE_NAME)

        # SES with Easy DKIM: the three CNAME records are written into the zone. Production access is a request to AWS.
        self.mail = ses.EmailIdentity(self, "Mail", identity=ses.Identity.public_hosted_zone(self.zone))
        route53.TxtRecord(self, "Dmarc", zone=self.zone, record_name=f"_dmarc.{config.ZONE_NAME}", values=["v=DMARC1; p=none"])

        # All state lives on this disk (Lightsail encrypts attached disks at rest). Retained when the host stack is replaced.
        self.disk = lightsail.CfnDisk(self, "State", disk_name=config.STATE_DISK_NAME, size_in_gb=config.STATE_DISK_GB,
                                      availability_zone=cfg["zone"])
        self.disk.apply_removal_policy(RemovalPolicy.RETAIN)

        budgets.CfnBudget(
            self, "Budget",
            budget=budgets.CfnBudget.BudgetDataProperty(
                budget_name="treeline-monthly", budget_type="COST", time_unit="MONTHLY",
                budget_limit=budgets.CfnBudget.SpendProperty(amount=config.MONTHLY_BUDGET_USD, unit="USD")),
            notifications_with_subscribers=[budgets.CfnBudget.NotificationWithSubscribersProperty(
                notification=budgets.CfnBudget.NotificationProperty(
                    comparison_operator="GREATER_THAN", notification_type=nt, threshold=thr, threshold_type="PERCENTAGE"),
                subscribers=[budgets.CfnBudget.SubscriberProperty(subscription_type="EMAIL", address=cfg["alert_email"])])
                for nt, thr in (("ACTUAL", 80), ("FORECASTED", 100))],
        )
