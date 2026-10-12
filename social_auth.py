"""Chisme social: Supabase Auth (GoTrue) from the server. Supabase stores and checks every password; Chisme never sees
a password hash and never stores a password. Chisme only keeps its own random session ids (hashed) after Supabase says
the password or the 6-digit email code was right.

Used endpoints: /signup, /verify (type email | recovery | email_change), /resend, /token?grant_type=password|pkce,
/recover, PUT /user (with the user's fresh access token), /admin/users/{id} (delete; the secret key), /authorize (OAuth).

FakeGoTrue: an in-memory stand-in with the same HTTP shapes, for tests and local dev only (SOCIAL_FAKE_AUTH=1). It
refuses to run on Render. Its 6-digit codes go to an outbox the tests (and the dev-only outbox endpoint) can read."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import secrets
import time
import uuid

import httpx

import social_store as S


class AuthError(Exception):
    def __init__(self, code: str, status: int = 400):
        super().__init__(code)
        self.code, self.status = code, status


def fake_enabled() -> bool:
    return os.environ.get("SOCIAL_FAKE_AUTH") == "1" and not os.environ.get("RENDER")


class GoTrue:
    def __init__(self, url: str, key: str, anon: str = "", client: httpx.AsyncClient | None = None):
        self.url, self.key, self.anon = url.rstrip("/"), key, anon or key
        self.http = client or httpx.AsyncClient(timeout=15)

    def _h(self, admin: bool = False, bearer: str | None = None) -> dict:
        k = self.key if admin else self.anon
        h = {"apikey": k, "Content-Type": "application/json"}
        if bearer:
            h["Authorization"] = "Bearer " + bearer
        elif admin or k.startswith("eyJ"):
            if k.startswith("eyJ"):
                h["Authorization"] = "Bearer " + k
        return h

    async def _call(self, method: str, path: str, body: dict | None = None, admin: bool = False, bearer: str | None = None,
                    params: dict | None = None) -> dict:
        try:
            r = await self.http.request(method, f"{self.url}/auth/v1{path}", json=body, params=params, headers=self._h(admin, bearer))
        except httpx.HTTPError:
            raise AuthError("unreachable", 503)
        try:
            d = r.json() if r.content else {}
        except Exception:
            d = {}
        if r.status_code >= 400:
            code = str(d.get("error_code") or d.get("code") or d.get("error") or "").lower() if isinstance(d, dict) else ""
            msg = str(d.get("msg") or d.get("message") or d.get("error_description") or "").lower() if isinstance(d, dict) else ""
            if r.status_code == 429 or "rate" in code:
                raise AuthError("rate_limited", 429)
            if "weak" in code or "weak" in msg or "password should" in msg:
                raise AuthError("weak_password", 422)
            if "not_confirmed" in code or "not confirmed" in msg:
                raise AuthError("email_not_confirmed", 403)
            if "otp" in code or "expired" in msg or "token" in msg and r.status_code in (401, 403):
                raise AuthError("bad_code", 400)
            if "invalid" in code or "invalid" in msg:
                raise AuthError("invalid", 400)
            raise AuthError("auth_error", 502 if r.status_code >= 500 else 400)
        return d if isinstance(d, dict) else {}

    async def signup(self, email: str, password: str) -> dict:
        """→ {"id": ..., "existing": bool}. Supabase answers a fake user (no identities) for an address it already has."""
        d = await self._call("POST", "/signup", {"email": email, "password": password})
        u = d.get("user") if isinstance(d.get("user"), dict) else d
        existing = isinstance(u.get("identities"), list) and not u["identities"]
        return {"id": u.get("id"), "existing": existing, "confirmed": bool(u.get("email_confirmed_at") or u.get("confirmed_at"))}

    async def verify(self, email: str, token: str, kind: str = "email") -> dict:
        d = await self._call("POST", "/verify", {"type": kind, "email": email, "token": token})
        u = d.get("user") or {}
        return {"id": u.get("id"), "access_token": d.get("access_token"), "email": u.get("email")}

    async def resend(self, email: str, kind: str = "signup") -> None:
        await self._call("POST", "/resend", {"type": kind, "email": email})

    async def password_login(self, email: str, password: str) -> dict:
        d = await self._call("POST", "/token", {"email": email, "password": password}, params={"grant_type": "password"})
        u = d.get("user") or {}
        return {"id": u.get("id"), "access_token": d.get("access_token"), "email": u.get("email")}

    async def recover(self, email: str) -> None:
        await self._call("POST", "/recover", {"email": email})

    async def update_user(self, access_token: str, fields: dict) -> dict:
        return await self._call("PUT", "/user", fields, bearer=access_token)

    async def admin_delete(self, uid: str) -> None:
        if not re.fullmatch(r"[0-9a-f-]{36}", uid or ""):
            raise AuthError("invalid")
        await self._call("DELETE", f"/admin/users/{uid}", admin=True)

    async def admin_get(self, uid: str) -> dict:
        return await self._call("GET", f"/admin/users/{uid}", admin=True)

    def authorize_url(self, provider: str, redirect_to: str, challenge: str) -> str:
        from urllib.parse import urlencode
        return f"{self.url}/auth/v1/authorize?" + urlencode({"provider": provider, "redirect_to": redirect_to,
                                                             "code_challenge": challenge, "code_challenge_method": "s256"})

    async def pkce_exchange(self, code: str, verifier: str) -> dict:
        d = await self._call("POST", "/token", {"auth_code": code, "code_verifier": verifier}, params={"grant_type": "pkce"})
        u = d.get("user") or {}
        return {"id": u.get("id"), "email": u.get("email"), "access_token": d.get("access_token"), "provider": (u.get("app_metadata") or {}).get("provider")}


# ---------------------------------------------------------------- the fake (tests + local dev only)
class FakeGoTrue:
    """GoTrue's HTTP shapes, in memory. Never for production (no persistence; refuses to run on Render)."""

    def __init__(self):
        self.users: dict[str, dict] = {}     # email → user
        self.codes: dict[tuple, tuple] = {}   # (email, kind) → (code, expires)
        self.outbox: list[dict] = []
        self.tokens: dict[str, str] = {}      # access token → email
        self.calls: list[tuple] = []

    @staticmethod
    def _hash(pw: str, salt: bytes) -> bytes:   # scrypt: the fake still never keeps a plain password
        return hashlib.scrypt(pw.encode(), salt=salt, n=2 ** 12, r=8, p=1)

    def _code(self, email: str, kind: str) -> str:
        c = f"{secrets.randbelow(10 ** 6):06d}"
        self.codes[(email, kind)] = (c, time.time() + 3600)
        self.outbox.append({"to": email, "kind": kind, "code": c, "at": time.time()})
        if fake_enabled():
            print(f"[fake auth] {kind} code for {email}: {c}")
        return c

    def _session(self, u: dict) -> dict:
        t = "fake-" + secrets.token_urlsafe(16)
        self.tokens[t] = u["email"]
        return {"access_token": t, "refresh_token": "r", "token_type": "bearer", "user": self._pub(u)}

    @staticmethod
    def _pub(u: dict) -> dict:
        return {"id": u["id"], "email": u["email"], "email_confirmed_at": u.get("confirmed"), "identities": [{"provider": "email"}],
                "app_metadata": {"provider": u.get("provider", "email")}}

    def last_code(self, email: str, kind: str | None = None) -> str | None:
        for m in reversed(self.outbox):
            if m["to"] == email and (kind is None or m["kind"] == kind):
                return m["code"]
        return None

    def handler(self, req: httpx.Request) -> httpx.Response:
        path = req.url.path.split("/auth/v1", 1)[-1]
        body = json.loads(req.content or b"{}") if req.content else {}
        self.calls.append((req.method, path))

        def err(status, code, msg=""):
            return httpx.Response(status, json={"error_code": code, "msg": msg})

        def ok(d):
            return httpx.Response(200, json=d)

        if req.method == "POST" and path == "/signup":
            email, pw = str(body.get("email", "")).lower(), str(body.get("password", ""))
            if len(pw) < 8:
                return err(422, "weak_password", "Password should be at least 8 characters.")
            if email in self.users:
                return ok({"id": str(uuid.uuid4()), "email": email, "identities": []})   # GoTrue's anti-enumeration answer
            salt = os.urandom(16)
            u = {"id": str(uuid.uuid4()), "email": email, "salt": salt, "pw": self._hash(pw, salt), "confirmed": None}
            self.users[email] = u
            self._code(email, "signup")
            return ok(self._pub(u))
        if req.method == "POST" and path == "/resend":
            email = str(body.get("email", "")).lower()
            if email in self.users:
                self._code(email, body.get("type", "signup"))
            return ok({})
        if req.method == "POST" and path == "/verify":
            email, tok, kind = str(body.get("email", "")).lower(), str(body.get("token", "")), body.get("type")
            key = {"email": "signup", "signup": "signup", "recovery": "recovery", "email_change": "email_change"}.get(kind)
            hit = self.codes.get((email, key))
            if not hit or hit[0] != tok or hit[1] < time.time():
                return err(403, "otp_expired", "Token has expired or is invalid")
            del self.codes[(email, key)]
            if key == "email_change":
                old = next((e for e, u in self.users.items() if u.get("new_email") == email), None)
                if not old:
                    return err(403, "otp_expired", "Token has expired or is invalid")
                u = self.users.pop(old)
                u["email"], u["new_email"] = email, None
                self.users[email] = u
            u = self.users[email]
            u["confirmed"] = u.get("confirmed") or "2026-10-04T00:00:00Z"
            return ok(self._session(u))
        if req.method == "POST" and path == "/token":
            gt = req.url.params.get("grant_type")
            if gt == "password":
                u = self.users.get(str(body.get("email", "")).lower())
                if not u or self._hash(str(body.get("password", "")), u["salt"]) != u["pw"]:
                    return err(400, "invalid_credentials", "Invalid login credentials")
                if not u.get("confirmed"):
                    return err(400, "email_not_confirmed", "Email not confirmed")
                return ok(self._session(u))
            if gt == "pkce":
                code = str(body.get("auth_code", ""))
                if not code.startswith("fakecode-"):
                    return err(400, "invalid_grant")
                email = code[9:] + "@oauth.example"
                u = self.users.setdefault(email, {"id": str(uuid.uuid4()), "email": email, "salt": b"", "pw": b"", "confirmed": "x", "provider": "google"})
                return ok(self._session(u))
            return err(400, "unsupported_grant_type")
        if req.method == "POST" and path == "/recover":
            email = str(body.get("email", "")).lower()
            if email in self.users:
                self._code(email, "recovery")
            return ok({})
        if req.method == "PUT" and path == "/user":
            tok = (req.headers.get("authorization") or "")[7:]
            email = self.tokens.get(tok)
            if not email or email not in self.users:
                return err(401, "bad_jwt")
            u = self.users[email]
            if "password" in body:
                if len(str(body["password"])) < 8:
                    return err(422, "weak_password")
                u["salt"] = os.urandom(16)
                u["pw"] = self._hash(str(body["password"]), u["salt"])
            if "email" in body:
                ne = str(body["email"]).lower()
                if ne in self.users:
                    return err(422, "email_exists")
                u["new_email"] = ne
                self._code(ne, "email_change")
            return ok(self._pub(u))
        m = re.fullmatch(r"/admin/users/([0-9a-f-]{36})", path)
        if m:
            if req.headers.get("apikey") != "fake-service-key":
                return err(401, "not_admin")
            email = next((e for e, u in self.users.items() if u["id"] == m.group(1)), None)
            if not email:
                return err(404, "user_not_found")
            if req.method == "DELETE":
                del self.users[email]
                return ok({})
            return ok(self._pub(self.users[email]))
        return err(404, "not_found")


_auth: dict = {}
FAKE = FakeGoTrue()


def auth() -> GoTrue | None:
    """The GoTrue client, or None when accounts aren't set up on this server (no Supabase and no dev fake)."""
    url, key = S.supabase_conf()
    anon = S._env("SUPABASE_PUBLISHABLE_KEY", "SUPABASE_ANON_KEY")
    if url and key:
        want = ("real", url, key, anon)
    elif fake_enabled():
        want = ("fake",)
    else:
        return None
    if _auth.get("want") != want:
        if want[0] == "real":
            _auth["c"] = GoTrue(url, key, anon)
        else:
            _auth["c"] = GoTrue("http://fake-gotrue.local", "fake-service-key", "fake-anon-key",
                                client=httpx.AsyncClient(transport=httpx.MockTransport(FAKE.handler)))
        _auth["want"] = want
    return _auth["c"]


def pkce_pair() -> tuple[str, str]:
    v = secrets.token_urlsafe(48)
    c = base64.urlsafe_b64encode(hashlib.sha256(v.encode()).digest()).decode().rstrip("=")
    return v, c
