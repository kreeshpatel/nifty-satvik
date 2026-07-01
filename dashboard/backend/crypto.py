"""
Symmetric encryption helpers — single source of truth for at-rest
encryption of Kite access tokens (routers/kite.py) and TOTP secrets
(auth.py).

Uses Fernet (AES-128-CBC + HMAC-SHA256) wrapped in MultiFernet so we
can rotate keys without a downtime migration:

  ENCRYPTION_KEY        — primary key (used for new encryptions)
  ENCRYPTION_KEYS_OLD   — comma-separated retired keys (still used for
                          decryption only — never for new encryptions)

To rotate keys safely:
  1. Generate a new Fernet key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
  2. Move the current ENCRYPTION_KEY into ENCRYPTION_KEYS_OLD on Render
  3. Set ENCRYPTION_KEY to the new key
  4. Restart the service (existing ciphertexts decrypt fine via the old
     key in the chain; new encryptions use the new key)
  5. Optionally run `rewrap()` on every encrypted column to actively
     migrate ciphertexts from old → new (one-shot maintenance script)
  6. Once all rows are rewrapped, drop the old key from ENCRYPTION_KEYS_OLD
"""
from __future__ import annotations

import os

from fastapi import HTTPException
from cryptography.fernet import Fernet, MultiFernet, InvalidToken


def _build_fernets() -> list[Fernet]:
    primary = os.getenv("ENCRYPTION_KEY", "")
    if not primary:
        raise HTTPException(
            status_code=500,
            detail="Server-side encryption not configured.",
        )
    keys = [Fernet(primary.encode())]
    old_raw = os.getenv("ENCRYPTION_KEYS_OLD", "").strip()
    if old_raw:
        for k in old_raw.split(","):
            k = k.strip()
            if k:
                keys.append(Fernet(k.encode()))
    return keys


def _multi() -> MultiFernet:
    return MultiFernet(_build_fernets())


def encrypt(plaintext: str) -> str:
    """Encrypt with the primary key only."""
    return _multi().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt — primary or any retired key in the chain may have signed it."""
    try:
        return _multi().decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        raise HTTPException(
            status_code=500,
            detail="Failed to decrypt — wrong key, retired key dropped, or tampered data.",
        )


def rewrap(ciphertext: str) -> str:
    """
    Decrypt with whichever key signed it, then re-encrypt under the primary.
    Idempotent if the ciphertext was already wrapped under the primary.
    Used by one-shot key-rotation maintenance scripts.
    """
    return _multi().rotate(ciphertext.encode()).decode()
