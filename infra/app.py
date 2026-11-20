#!/usr/bin/env python3
"""CDK entry point. Settings come from the environment (infra/deploy.sh sets them from SSM and Route 53); see config.py."""

import sys

from aws_cdk import App, CliCredentialsStackSynthesizer, Environment

from treeline_infra import config
from treeline_infra.foundation import Foundation
from treeline_infra.host import Host


def build(env=None):
    cfg = config.from_environment(env)
    app = App()
    kw = {"env": Environment(region=config.REGION), "synthesizer": CliCredentialsStackSynthesizer()}
    foundation = Foundation(app, "TreelineFoundation", cfg=cfg, **kw)
    host = Host(app, "TreelineHost", cfg=cfg, **kw)
    host.add_stack_dependency(foundation)
    return app


if __name__ == "__main__":
    try:
        build().synth()
    except config.ConfigError as err:
        sys.exit(f"infra: {err}")
