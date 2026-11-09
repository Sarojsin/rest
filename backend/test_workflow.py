import json, urllib.request, uuid

BASE = "http://127.0.0.1:8000"

def post_json(path, body, token=None, idempotency_key=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:500]

def get_json(path, token=None):
    headers = {}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(BASE + path, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:500]

QR_TOKEN = "ewFx7F47Eg_i5298VJkWKeyj4YwhnZwU"

# Get order_id and status_token from previous run - we need to re-submit
print("=== Step 1: Customer scans QR ===")
print("QR URL: http://ass.platform.com:5173/t/%s" % QR_TOKEN)

# Customer opens menu page
print("\n=== Customer opens menu ===")
status, menu = get_json("/api/v1/public/qr/%s/menu" % QR_TOKEN)
if status != 200:
    print("Menu failed: %s" % menu)
    exit(1)
print("Menu loaded! Restaurant: %s | Table: %s" % (menu["restaurant_name"], menu["table_display_name"]))

# Customer places order
print("\n=== Customer submits order ===")
menu_items = []
for cat in menu["categories"]:
    for item in cat["items"]:
        menu_items.append(item)

order_items = []
for item in menu_items:
    if item["name"] == "Margherita Pizza":
        order_items.append({"menu_item_id": item["id"], "quantity": 1, "special_instructions": "Extra cheese"})
    if item["name"] == "Fresh Lime Soda":
        order_items.append({"menu_item_id": item["id"], "quantity": 2, "special_instructions": "No ice"})

status, order_result = post_json(
    "/api/v1/public/qr/%s/orders" % QR_TOKEN,
    {"customer_note": "Please bring water first", "items": order_items},
    idempotency_key=str(uuid.uuid4())
)

if status not in (200, 201):
    print("Order failed: %s" % order_result)
    exit(1)

print("Order submitted!")
order_id = order_result["order"]["id"]
status_token = order_result["status_token"]
print("Order ID: %s" % order_id)
print("Status token: %s" % status_token)

# Waiter accepts order
print("\n=== Waiter accepts order ===")
lr = post_json("/api/v1/auth/login", {"email": "bahadhami14+main.waiter@gmail.com", "password": "Staff@#12345"})
waiter_token = lr[1]["access_token"]

status, pending = get_json("/api/v1/orders?status=PENDING_CONFIRMATION", waiter_token)
print("Pending orders: %d" % len(pending))

status, accepted = post_json("/api/v1/orders/%s/accept" % order_id, {}, waiter_token)
if status == 200:
    print("Order accepted!")
    print("Dining session: %s" % accepted.get("dining_session_id", "N/A"))
    print("Kitchen ticket: %s" % accepted.get("kitchen_ticket_id", "N/A"))
else:
    print("Accept failed: %s" % accepted)

# Kitchen sees ticket
print("\n=== Kitchen sees ticket ===")
lr = post_json("/api/v1/auth/login", {"email": "bahadhami14+main.kitchen@gmail.com", "password": "Staff@#12345"})
kitchen_token = lr[1]["access_token"]

status, tickets = get_json("/api/v1/kitchen/tickets", kitchen_token)
print("Kitchen tickets: %d" % len(tickets))
for t in tickets:
    print("  Ticket %s | status=%s" % (t["id"][:8], t.get("status", "?")))

# Cashier issues bill
print("\n=== Cashier issues bill ===")
lr = post_json("/api/v1/auth/login", {"email": "bahadhami14+main.cashier@gmail.com", "password": "Staff@#12345"})
cashier_token = lr[1]["access_token"]

status, sessions = get_json("/api/v1/sessions", cashier_token)
print("Cashier sessions: %d" % len(sessions))
if sessions:
    first = sessions[0]
    print("First session keys: %s" % list(first.keys()) if isinstance(first, dict) else type(first))
    for s in sessions[:5]:
        if isinstance(s, dict):
            print("  Session %s | status=%s | total=%s" % (str(s.get("id", ""))[:8], s.get("status", "?"), s.get("total_minor", "N/A")))
        else:
            print("  Item: %s" % str(s)[:100])

# Customer status page
print("\n=== Customer status page ===")
status, cust_status = get_json("/api/v1/public/orders/%s" % status_token)
if status == 200:
    print("Customer status loaded!")
    print("Order status: %s" % cust_status.get("status", "?"))
    print("Table: %s" % cust_status.get("table_display_name", "?"))
else:
    print("Status failed: %s" % cust_status)

print("\n=== WORKFLOW COMPLETE ===")
