"""
PocketPlot Universe — Encryption helper (v11).

The brief is explicit: no new external dependencies. The container
has no `cryptography` or `pycryptodome` installed, so we can't use
Fernet or PyCA's AES.

This module implements an AUTHENTICATED ENCRYPTION scheme using only
the Python standard library:

  - KDF:    PBKDF2-HMAC-SHA256 (NIST SP 800-132 recommended, 100k iters)
  - Cipher: stream cipher built from HMAC-SHA256(key, salt || counter).
            This is functionally equivalent to AES-CTR with a HMAC-based
            keystream — the actual encryption step is XOR with the
            keystream blocks. (For at-rest API-key storage of ~50-char
            strings, this is appropriate; do NOT use it for general
            bulk data.)
  - MAC:    Encrypt-then-MAC: separate HMAC-SHA256 over the ciphertext.

Output wire format (base64-encoded):
    [version:1B][salt:16B][IV:16B][ciphertext:N B][tag:32B]

version=1 indicates v11 format. Future versions can extend without
breaking compatibility (decryption refuses unknown versions).
"""
import base64
import hashlib
import hmac
import os
import struct

VERSION = 1
SALT_LEN = 16
IV_LEN = 16
TAG_LEN = 32
PBKDF2_ITERS = 100_000
BLOCK_LEN = 64  # bytes per keystream block; HMAC-SHA256 output size


def _derive_key_material(passphrase: str, salt: bytes) -> tuple:
    """Derive 64 bytes: 32 for keystream, 32 for MAC."""
    mat = hashlib.pbkdf2_hmac(
        "sha256", passphrase.encode("utf-8"), salt, PBKDF2_ITERS, dklen=64
    )
    return mat[:32], mat[32:]


def _keystream_block(stream_key: bytes, salt: bytes, iv: bytes, counter: int) -> bytes:
    """One 64-byte keystream block."""
    msg = salt + iv + struct.pack(">Q", counter)
    return hmac.new(stream_key, msg, hashlib.sha256).digest()


def _keystream(stream_key: bytes, salt: bytes, iv: bytes, n: int) -> bytes:
    """n bytes of keystream."""
    out = b""
    counter = 0
    while len(out) < n:
        out += _keystream_block(stream_key, salt, iv, counter)
        counter += 1
    return out[:n]


def encrypt(plaintext: str, passphrase: str) -> str:
    """Encrypt a string. Returns base64-encoded wire format."""
    salt = os.urandom(SALT_LEN)
    iv = os.urandom(IV_LEN)
    stream_key, mac_key = _derive_key_material(passphrase, salt)
    pt = plaintext.encode("utf-8")
    ct = bytes(a ^ b for a, b in zip(pt, _keystream(stream_key, salt, iv, len(pt))))
    # Encrypt-then-MAC over version, salt, iv, ciphertext.
    mac_data = bytes([VERSION]) + salt + iv + ct
    tag = hmac.new(mac_key, mac_data, hashlib.sha256).digest()
    blob = bytes([VERSION]) + salt + iv + ct + tag
    return base64.urlsafe_b64encode(blob).decode("ascii")


def decrypt(ciphertext_b64: str, passphrase: str) -> str:
    """Decrypt a string. Raises ValueError on tamper / bad version."""
    blob = base64.urlsafe_b64decode(ciphertext_b64.encode("ascii"))
    if len(blob) < 1 + SALT_LEN + IV_LEN + TAG_LEN:
        raise ValueError("ciphertext too short")
    version = blob[0]
    if version != VERSION:
        raise ValueError(f"unknown version: {version}")
    salt = blob[1:1 + SALT_LEN]
    iv = blob[1 + SALT_LEN:1 + SALT_LEN + IV_LEN]
    ct = blob[1 + SALT_LEN + IV_LEN:-TAG_LEN]
    tag = blob[-TAG_LEN:]
    stream_key, mac_key = _derive_key_material(passphrase, salt)
    expected_tag = hmac.new(
        mac_key, bytes([version]) + salt + iv + ct, hashlib.sha256
    ).digest()
    if not hmac.compare_digest(expected_tag, tag):
        raise ValueError("authentication tag mismatch (tamper or wrong key)")
    pt = bytes(a ^ b for a, b in zip(ct, _keystream(stream_key, salt, iv, len(ct))))
    return pt.decode("utf-8")
