import json, urllib.request, urllib.error, time, secrets, hashlib, psycopg2, uuid
from datetime import UTC, datetime, timedelta

BASE = "http://127.0.0.1:8000"
ORIGIN = "http://192.168.1.5:5173"
STAFF_PASS = "Staff@#12345"

# Tokens captured from earlier invites (browser + API)
tokens = {
    "main.manager": "eXsu9uNa3QxT1iSEkvtVimRyvMd48Ydpu0LEmhwJSOE",
    "main.waiter": "pjs2IL78LaUspF6EF7EJFAFJNgAHklAS0LMFQOHruak",
    "main.cashier": "SSdBV6G6SfrsOf3RT6MbsBhPWt4e84EsNBxysahLesE",
    "lake.manager": "3YRv-e4Ecbc-5UQ9HNmf4A1TNRYlv33EueenDnEcKGo",
    "lake.waiter": "ajPy-0z0DwWkhZi_9b4dereXCTIdDgU7SjYfF0C6FRY",
    "lake.kitchen": "agO3A_vRvmsk0dKGKXFwP-O6FkWMj6TxOKUMhQJb0AQ",
    "lake.cashier": "ieZgsBeer3MWt5XU1L2pEADmvoY_wf_88F7ks1HTYfk",
}

# Generate a fresh token for main.kitchen and insert directly into DB
raw_token = secrets.token_urlsafe(32)
token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
expires_at = datetime.now(UTC) + timedelta(hours=72)
tokens["main.kitchen"] = raw_token

c = psycopg2.connect("dbname=restaurant user=postgres password=tara host=localhost")
cur = c.cursor()
cur.execute("SELECT id FROM restaurants WHERE slug = 'ass'")
rest_id = cur.fetchone()[0]
token_id = str(uuid.uuid4())
cur.execute(
    """INSERT INTO platform_one_time_tokens
        (id, token_hash, purpose, email, restaurant_id, expires_at,
         created_by_admin_id, used_at, created_at)
       VALUES (%s, %s, 'STAFF_INVITE', %s, %s, %s, NULL, NULL, NOW())
       RETURNING id""",
    (token_id, token_hash, "bahadhami14+main.kitchen@gmail.com", rest_id, expires_at))
new_id = cur.fetchone()[0]
c.commit()
c.close()
print("Inserted PlatformOneTimeToken id=%s for main.kitchen" % new_id)

def post_json(path, body, origin=None):
    headers = {"Content-Type": "application/json"}
    if origin:
        headers["Origin"] = origin
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(body).encode(),
        headers=headers,
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        msg = e.read().decode()[:200]
        print("  HTTP %d: %s" % (e.code, msg))
        raise

def get_me(token):
    req = urllib.request.Request(f"{BASE}/api/v1/me",
                                 headers={"Authorization": "Bearer " + token},
                                 method="GET")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

label_map = {
    "main.manager": ("Manager", "Main Branch"),
    "main.waiter": ("Waiter", "Main Branch"),
    "main.kitchen": ("Kitchen", "Main Branch"),
    "main.cashier": ("Cashier", "Main Branch"),
    "lake.manager": ("Manager", "Lakeside Branch"),
    "lake.waiter": ("Waiter", "Lakeside Branch"),
    "lake.kitchen": ("Kitchen", "Lakeside Branch"),
    "lake.cashier": ("Cashier", "Lakeside Branch"),
}

email_map = {
    "main.manager": "bahadhami14+main.manager@gmail.com",
    "main.waiter": "bahadhami14+main.waiter@gmail.com",
    "main.kitchen": "bahadhami14+main.kitchen@gmail.com",
    "main.cashier": "bahadhami14+main.cashier@gmail.com",
    "lake.manager": "bahadhami14+lake.manager@gmail.com",
    "lake.waiter": "bahadhami14+lake.waiter@gmail.com",
    "lake.kitchen": "bahadhami14+lake.kitchen@gmail.com",
    "lake.cashier": "bahadhami14+lake.cashier@gmail.com",
}

print("\n=== Accept all 8 invitations via platform API ===")
accepted = []
for key, token in tokens.items():
    try:
        post_json("/api/platform/auth/invitations/%s/accept" % token, {
            "password": STAFF_PASS,
            "display_name": key,
        }, origin=ORIGIN)
        accepted.append(key)
        print("OK accepted %s (%s, %s)" % (key, label_map[key][0], label_map[key][1]))
    except Exception as e:
        print("FAIL %s: %s" % (key, e))
    time.sleep(0.2)

print("\nAccepted %d/8" % len(accepted))

print("\n=== Verify staff logins ===")
for key in tokens:
    email = email_map[key]
    try:
        lr = post_json("/api/v1/auth/login", {"email": email, "password": STAFF_PASS})
        st = lr["access_token"]
        me = get_me(st)
        print("OK %s -> role=%s branch_ids=%s" % (email, me['membership']['role'], me['membership'].get('branch_ids')))
    except Exception as e:
        print("FAIL %s: %s" % (email, e))

print("\nDone.")
