import json, urllib.request, urllib.error, sys, time

BASE = "http://127.0.0.1:8000"
OWNER_EMAIL = "bahadhami14@gmail.com"
OWNER_PASS = "Saroj@#12345"
STAFF_PASS = "Staff@#12345"

# mapping of branch codes to branch IDs (from list_branches.py)
BRANCHES = {
    "Main Branch": "bc62498a-279b-487b-9d20-076306a661c3",
    "Lakeside Branch": "4f8d99de-4dbe-484e-8b73-46b730048737",
}

# roles per branch (owner already exists)
ROLES = [
    ("manager", "Main Branch"),
    ("waiter", "Main Branch"),
    ("kitchen", "Main Branch"),
    ("cashier", "Main Branch"),
    ("manager", "Lakeside Branch"),
    ("waiter", "Lakeside Branch"),
    ("kitchen", "Lakeside Branch"),
    ("cashier", "Lakeside Branch"),
]

# helper to make POST with JSON body and auth token
def post_json(path, body, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{BASE}{path}", data=json.dumps(body).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

# helper to make GET with auth token
def get_json(path, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{BASE}{path}", headers=headers, method="GET")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

print("=== Owner login ===")
login_body = {"email": OWNER_EMAIL, "password": OWNER_PASS}
try:
    login_resp = post_json("/api/v1/auth/login", login_body)
except Exception as e:
    print("Owner login failed:", e)
    sys.exit(1)
owner_token = login_resp["access_token"]
print(f"Owner token: {owner_token[:20]}...")

# Verify owner membership
me = get_json("/api/v1/me", owner_token)
print(f"Owner user: {me['email']}, role: {me['membership']['role']}")

# Step 1: Create invitations for each role+branch
invitations = []
for role, branch_name in ROLES:
    email_alias = f"bahadhami14+{branch_name.lower().replace(' ', '.').replace('branch', '')}.{role}@gmail.com"
    # According to summary, use plus-aliases like main.manager, main.waiter etc.
    # but we need to match actual email format used. Earlier we saw main.manager, main.waiter etc.
    # Let's reconstruct based on summary: "bahadhami14+main.manager@gmail.com", "+main.waiter", "+main.kitchen", "+main.cashier", "+lake.manager", etc.
    # Let's generate email aliases per summary:
    if branch_name == "Main Branch":
        prefix = "main"
    else:
        prefix = "lake"
    email = f"bahadhami14+{prefix}.{role}@gmail.com"
    body = {
        "email": email,
        "role": role,
        "name": f"{role.capitalize()} {branch_name}",
        "phone": None,
        "branch_id": BRANCHES[branch_name],
    }
    try:
        inv = post_json("/api/v1/restaurant_memberships/invite", body, owner_token)
        link = f"{BASE}/auth/invitations/{inv['invitation_token']}"
        invitations.append({
            "role": role,
            "branch": branch_name,
            "email": email,
            "name": body["name"],
            "token": inv["invitation_token"],
            "link": link,
        })
        print(f"Created invitation: {email} ({role} in {branch_name})")
    except Exception as e:
        print(f"Failed to invite {email}: {e}")

# Step 2: Accept invitations and login
staff_accounts = []
for inv in invitations:
    token = inv["token"]
    try:
        accept_body = {"password": STAFF_PASS}
        accept_resp = post_json(f"/api/v1/auth/invitations/{token}/accept", accept_body)
        staff_token = accept_resp.get("access_token")
        # Use the token to fetch user/me to confirm role
        user = get_json("/api/v1/me", staff_token)
        staff_accounts.append({
            "role": inv["role"],
            "branch": inv["branch"],
            "email": inv["email"],
            "token": staff_token,
            "membership": user["membership"],
        })
        print(f"Accepted invitation for {inv['email']} (role {inv['role']})")
        time.sleep(0.2)  # avoid rate limiting
    except Exception as e:
        print(f"Failed to accept invitation for {inv['email']}: {e}")

# Step 3: Verify each staff account can log in and lands correctly
print("\n=== Staff verification ===")
for acc in staff_accounts:
    try:
        # direct login with the staff password using the token already obtained
        # but we also can call login endpoint to re-verify
        login_body = {"email": acc["email"], "password": STAFF_PASS}
        login_resp = post_json("/api/v1/auth/login", login_body)
        login_token = login_resp["access_token"]
        user = get_json("/api/v1/me", login_token)
        print(f"✓ {acc['email']} logged in as {user['membership']['role']} for branch {acc['branch']}")
    except Exception as e:
        print(f"✗ {acc['email']} login verification failed: {e}")

print("\n=== Summary ===")
print(f"Created {len(invitations)} invitations.")
print(f"Accepted {len(staff_accounts)} invitations.")
print("\nInvitation links (for manual testing):")
for inv in invitations:
    print(f"{inv['role']} {inv['branch']}: {inv['link']}")

# Optionally, also test restricted API actions for each role (skip for brevity)
print("\nDone.")