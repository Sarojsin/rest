import hmac, hashlib, base64, struct, time, sys

def totp(secret, period=30, digits=6):
    key = base64.b32decode(secret, casefold=True)
    counter = int(time.time()) // period
    msg = struct.pack('>Q', counter)
    h = hmac.new(key, msg, hashlib.sha1).digest()
    o = h[19] & 0x0F
    code = (struct.unpack('>I', h[o:o+4])[0] & 0x7FFFFFFF) % (10 ** digits)
    return f"{code:0{digits}d}"

if __name__ == '__main__':
    sec = sys.argv[1] if len(sys.argv) > 1 else "JBSWY3DPEHPK3PXP"
    print(totp(sec))
