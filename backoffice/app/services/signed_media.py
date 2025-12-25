import base64
import hmac
import hashlib
import os
import time
from typing import Optional


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _get_signing_key(secret_fallback: str) -> bytes:
    key = os.getenv("MEDIA_SIGNING_KEY") or secret_fallback or ""
    return key.encode("utf-8")


def sign_media(kind: str, identifier: str, exp: int, nonce: str, *, secret_fallback: str) -> str:
    """Return HMAC signature for a media reference.

    kind: e.g. "faq", "idle", "greeting"
    identifier: faq_id/chatbot_id as string
    exp: unix seconds
    nonce: any short string to avoid cache issues; MUST be included in verification
    """
    msg = f"{kind}:{identifier}:{exp}:{nonce}".encode("utf-8")
    key = _get_signing_key(secret_fallback)
    mac = hmac.new(key, msg, hashlib.sha256).digest()
    return _b64url(mac)


def verify_media_sig(
    kind: str,
    identifier: str,
    exp: int,
    nonce: str,
    sig: str,
    *,
    secret_fallback: str,
    now: Optional[int] = None,
) -> bool:
    """Verify signature + expiry. Returns False on any invalid input."""
    try:
        now_ts = int(time.time() if now is None else now)
        exp_int = int(exp)
        if exp_int < now_ts:
            return False
        expected = sign_media(kind, identifier, exp_int, nonce, secret_fallback=secret_fallback)
        return hmac.compare_digest(expected, (sig or "").strip())
    except Exception:
        return False


