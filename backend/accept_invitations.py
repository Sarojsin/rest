import json, urllib.request, urllib.error, sys, time

BASE = "http://127.0.0.1:8000"
STAFF_PASS = "Staff@#12345"

# From DB: all 8 staff memberships now exist as INVITED. We need their tokens.
# Re-fetch tokens from DB
import psycopg2
c = psycopg2.connect("dbname=restaurant user=postgres password=tara host=localhost")
cur = c.cursor()
cur.execute("""
    SELECT u.email, t.token, t.purpose, t.expires_at, t.used_at
    FROM platform_one_time_tokens t
    JOIN users u ON u.id = t.user_id
    WHERE t.purpose = 'STAFF_INVITE' AND t.used_at IS NULL
    ORDER BY t.created_at DESC
""")
tokens = cur.fetchall()
c.close()
print("Pending STAFF_INVITE tokens:", len(tokens))
for row in tokens:
    print(" ", row[0], row[1][:20], "...", row[2], row[3], row[4])

def post_json(path, body):
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

accepted = []
for email, token, purpose, expires_at, used_at in tokens:
    try:
        body = {"password": STAFF_PASS, "display_name": email.split("@")[0]}
        resp = post_json(f"/api/platform/auth/invitations/{token}/accept", body)
        accepted.append((email, token))
        print(f"✓ Accepted {email}")
    except urllib.error.HTTPError as e:
        print(f"✗ {email}: HTTP {e.code} {e.read().decode()[:200]}")
    except Exception as e:
        print(f"✗ {email}: {e}")
    time.sleep(0.2)

print(f"\nAccepted {len(accepted)}/{len(tokens)} invitations.")
