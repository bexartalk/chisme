"""Print a fresh VAPID key pair (and a tick secret) for Chisme's alerts, as env-var lines to paste into Render's
Environment settings. Nothing is written to disk; don't commit the output.
    python tools/make_vapid_keys.py            (needs: pip install py-vapid, or the app's requirements)"""
import base64, secrets
from py_vapid import Vapid
from cryptography.hazmat.primitives import serialization
v = Vapid(); v.generate_keys()
b64 = lambda b: base64.urlsafe_b64encode(b).rstrip(b"=").decode()
print("VAPID_PUBLIC_KEY=" + b64(v.public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)))
print("VAPID_PRIVATE_KEY=" + b64(v.private_key.private_numbers().private_value.to_bytes(32, "big")))
print("VAPID_SUBJECT=mailto:you@example.com   # change to your email")
print("PUSH_TICK_SECRET=" + secrets.token_urlsafe(32) + "   # the same value goes in the GitHub secret PUSH_TICK_SECRET")
