import json, urllib.request, urllib.error, secrets, hashlib, psycopg2, uuid
from datetime import UTC, datetime, timedelta

BASE = "http://127.0.0.1:8000"
ORIGIN = "http://192.168.1.5:5173"
STAFF_PASS = "Staff@#12345"

# Insert a fresh token for main.waiter
raw_token = secrets.token_urlsafe(32)
token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
expires_at = datetime.now(UTC) + timedelta(hours=72)

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
    (token_id, token_hash, "bahadhami14+main.waiter@gmail.com", rest_id, expires_at))
new_id = cur.fetchone()[0]
c.commit()
c.close()
print("Inserted PlatformOneTimeToken id=%s for main.waiter" % new_id)

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
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

# Accept it
try:
    post_json("/api/platform/auth/invitations/%s/accept" % raw_token, {
        "password": STAFF_PASS,
        "display_name": "main.waiter",
    }, origin=ORIGIN)
    print("OK accepted main.waiter")
except Exception as e:
    print("FAIL main.waiter: %s" % e)

# Verify login
try:
    lr = post_json("/api/v1/auth/login", {
        "email": "bahadhami14+main.waiter@gmail.com",
        "password": STAFF_PASS,
    })
    st = lr["access_token"]
    req = urllib.request.Request(f"{BASE}/api/v1/me",
                                 headers={"Authorization": "Bearer " + st},
                                 method="GET")
    with urllib.request.urlopen(req) as resp:
        me = json.loads(resp.read())
    print("OK main.waiter login -> role=%s branch_ids=%s" % (
        me['membership']['role'], me['membership'].get('branch_ids')))
except Exception as e:
    print("FAIL main.waiter login: %s" % e)

print("Done.")
