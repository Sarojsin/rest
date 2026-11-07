import hmac
import hashlib
import base64
import struct
import time

# MFA material derived from config:
# platform_mfa_material = f"platform-dev-mfa::{self.secret_key}"
# secret_key = "dev-only-change-me-not-for-production"
secret_string = "platform-dev-mfa::dev-only-change-me-not-for-production"

# TOTP uses base32-decoded secret. But our string isn't valid base32.
# Some implementations use raw string bytes instead.
# Let's try both approaches.

# Approach 1: Use raw string bytes as secret
secret_bytes = secret_string.encode('utf-8')

# Get current time step (30 seconds)
now = int(time.time())
time_step = now // 30

# Convert time step to 8-byte big-endian
counter = struct.pack(">Q", time_step)

# Compute HMAC-SHA1
hmac_hash = hmac.new(secret_bytes, counter, hashlib.sha1).digest()

# Dynamic truncation (RFC 4226)
offset = hmac_hash[-1] & 0x0f
binary = (
    ((hmac_hash[offset] & 0x7f) << 24) |
    ((hmac_hash[offset + 1] & 0xff) << 16) |
    ((hmac_hash[offset + 2] & 0xff) << 8) |
    (hmac_hash[offset + 3] & 0xff)
)

otp = binary % 1000000
print(f"TOTP Code (raw bytes secret): {otp:06d}")
print(f"Secret: {secret_string}")
print(f"Time step: {time_step}")
print(f"Current time: {now}")

# Also try: maybe the secret is base32 encoded somehow
# Try common base32 decoding of the string
try:
    # Add padding if needed
    secret_b32 = secret_string.upper()
    # Remove non-base32 chars
    import re
    secret_b32_clean = re.sub(r'[^A-Z2-7]', '', secret_b32)
    if secret_b32_clean:
        padding = len(secret_b32_clean) % 8
        if padding:
            secret_b32_clean += '=' * (8 - padding)
        secret_b32_bytes = base64.b32decode(secret_b32_clean)
        hmac_hash2 = hmac.new(secret_b32_bytes, counter, hashlib.sha1).digest()
        offset2 = hmac_hash2[-1] & 0x0f
        binary2 = (
            ((hmac_hash2[offset2] & 0x7f) << 24) |
            ((hmac_hash2[offset2 + 1] & 0xff) << 16) |
            ((hmac_hash2[offset2 + 2] & 0xff) << 8) |
            (hmac_hash2[offset2 + 3] & 0xff)
        )
        otp2 = binary2 % 1000000
        print(f"TOTP Code (base32 cleaned secret): {otp2:06d}")
except Exception as e:
    print(f"Base32 approach failed: {e}")

# Also try with just the secret_key part
secret_key = "dev-only-change-me-not-for-production"
secret_key_bytes = secret_key.encode('utf-8')
hmac_hash3 = hmac.new(secret_key_bytes, counter, hashlib.sha1).digest()
offset3 = hmac_hash3[-1] & 0x0f
binary3 = (
    ((hmac_hash3[offset3] & 0x7f) << 24) |
    ((hmac_hash3[offset3 + 1] & 0xff) << 16) |
    ((hmac_hash3[offset3 + 2] & 0xff) << 8) |
    (hmac_hash3[offset3 + 3] & 0xff)
)
otp3 = binary3 % 1000000
print(f"TOTP Code (secret_key only): {otp3:06d}")

# Try with platform_dev_signing key
signing_key = "dev-platform-signing"
signing_bytes = signing_key.encode('utf-8')
hmac_hash4 = hmac.new(signing_bytes, counter, hashlib.sha1).digest()
offset4 = hmac_hash4[-1] & 0x0f
binary4 = (
    ((hmac_hash4[offset4] & 0x7f) << 24) |
    ((hmac_hash4[offset4 + 1] & 0xff) << 16) |
    ((hmac_hash4[offset4 + 2] & 0xff) << 8) |
    (hmac_hash4[offset4 + 3] & 0xff)
)
otp4 = binary4 % 1000000
print(f"TOTP Code (platform_secret_key): {otp4:06d}")