import base64
import hashlib
import hmac
import struct
import time

secret = "JBSWY3DPEHPK3PXP"
key = base64.b32decode(secret + "=" * ((8 - len(secret) % 8) % 8))
counter = int(time.time()) // 30
msg = struct.pack(">Q", counter)
digest = hmac.new(key, msg, hashlib.sha1).digest()
offset = digest[-1] & 0x0F
code = (struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF) % 1_000_000
print(f"{code:06d}")
