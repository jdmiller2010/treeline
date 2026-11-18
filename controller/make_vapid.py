"""Make a Web Push (VAPID) key pair for parent notifications.

  python make_vapid.py

Prints the two lines to paste into deploy/.env.
"""

import base64

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid


def b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def make():
    v = Vapid()
    v.generate_keys()
    private = b64(v.private_key.private_numbers().private_value.to_bytes(32, "big"))
    public = b64(v.public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint))
    return public, private


if __name__ == "__main__":
    pub, priv = make()
    print(f"TREELINE_VAPID_PUBLIC={pub}")
    print(f"TREELINE_VAPID_PRIVATE={priv}")
