"""Make a fresh VAPID key pair (and a tick secret) for Chisme's alerts. Never commit the output.

    python tools/make_vapid_keys.py                   print env-var lines to paste into Render → Environment
    python tools/make_vapid_keys.py --out DIR [--subject mailto:you@example.com]
        write the keys into DIR (made 0700, every file 0600; refuses to write inside this repo):
          vapid_public.txt      VAPID_PUBLIC_KEY: the browser's applicationServerKey (base64url, 65-byte uncompressed P-256 point)
          vapid_private.txt     VAPID_PRIVATE_KEY: base64url raw 32-byte private key (what pywebpush/py_vapid accept as a string)
          vapid_private.pem     the same key as PKCS#8 PEM (pywebpush also accepts a path to this file)
          push_tick_secret.txt  PUSH_TICK_SECRET for the external cron / GitHub Actions knock on /api/push/tick
          chisme-vapid.env      all of the above as NAME=value lines (for ./run.sh: CHISME_ENV=DIR/chisme-vapid.env)
(needs: pip install py-vapid, or the app's requirements)"""
import argparse, base64, os, secrets, sys
from pathlib import Path
from py_vapid import Vapid
from cryptography.hazmat.primitives import serialization

ap = argparse.ArgumentParser()
ap.add_argument("--out"); ap.add_argument("--subject", default="mailto:you@example.com")
a = ap.parse_args()
v = Vapid(); v.generate_keys()
b64 = lambda b: base64.urlsafe_b64encode(b).rstrip(b"=").decode()
pub = b64(v.public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint))
priv = b64(v.private_key.private_numbers().private_value.to_bytes(32, "big"))
pem = v.private_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
tick = secrets.token_urlsafe(32)
if not a.out:
    print("VAPID_PUBLIC_KEY=" + pub); print("VAPID_PRIVATE_KEY=" + priv)
    print("VAPID_SUBJECT=" + a.subject + "   # change to your email"); print("PUSH_TICK_SECRET=" + tick)
    sys.exit(0)
out = Path(a.out).resolve(); repo = Path(__file__).resolve().parent.parent
if out == repo or repo in out.parents:
    sys.exit("refusing to write keys inside the repo")
out.mkdir(parents=True, exist_ok=True); os.chmod(out, 0o700)
files = {"vapid_public.txt": pub + "\n", "vapid_private.txt": priv + "\n", "vapid_private.pem": pem, "push_tick_secret.txt": tick + "\n",
         "chisme-vapid.env": f"# Chisme Web Push (VAPID) keys. Never commit. Paste into Render → chisme → Environment.\n"
                             f"VAPID_PUBLIC_KEY={pub}\nVAPID_PRIVATE_KEY={priv}\nVAPID_SUBJECT={a.subject}\nPUSH_TICK_SECRET={tick}\n"}
for name, body in files.items():
    p = out / name
    if p.exists():
        sys.exit(f"{p} already exists; not overwriting (move it away first)")
for name, body in files.items():
    p = out / name
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(body)
    os.chmod(p, 0o600)
print("wrote", ", ".join(files), "to", out, "(0600; values not printed)")
