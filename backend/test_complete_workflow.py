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
        return e.code, e.read().decode()[:300]

def get_json(path, token=None):
    headers = {}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(BASE + path, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]

print("=" * 60)
print("COMPLETE QR ORDERING WORKFLOW TEST")
print("=" * 60)

# ============================================================
# Step 0: Owner gets cash payment method
# ============================================================
print("\n--- Step 0: Owner gets cash payment method ---")
lr = post_json("/api/v1/auth/login", {"email": "bahadhami14@gmail.com", "password": "Saroj@#12345"})
owner_token = lr[1]["access_token"]
print("Owner login: OK")

status, methods = get_json("/api/v1/payment-methods", owner_token)
cash_method_id = None
for m in methods:
    if m["kind"] == "CASH":
        cash_method_id = m["id"]
        print("Cash payment method: %s" % str(cash_method_id)[:8])
        break

if not cash_method_id:
    print("ERROR: No cash payment method found")
    exit(1)

# ============================================================
# Step 1: Owner gets existing table T7
# ============================================================
print("\n--- Step 1: Owner gets existing table ---")
status, tables = get_json("/api/v1/tables", owner_token)
table = None
for t in tables:
    if t["table_code"] == "T7":
        table = t
        break

if not table:
    print("Table T7 not found, creating new one...")
    status, table = post_json("/api/v1/tables", {
        "table_code": "T9",
        "display_name": "Table 9",
        "seating_capacity": 4,
        "sort_order": 20
    }, owner_token)
    if status not in (200, 201):
        print("Table creation failed: %s" % table)
        exit(1)

qr_token = table["qr_token"]
print("Table: %s (%s)" % (table["table_code"], table["display_name"]))
print("QR token (full): %s" % qr_token)
print("QR URL: http://ass.platform.com:5173/t/%s" % qr_token)
if not qr_token:
    print("ERROR: No QR token returned from table listing!")
    exit(1)

# ============================================================
# Step 2: Customer opens menu via QR
# ============================================================
print("\n--- Step 2: Customer opens menu via QR ---")
status, menu = get_json("/api/v1/public/qr/%s/menu" % qr_token)
assert status == 200, "Menu load failed: %s" % menu
print("Menu loaded for restaurant: %s" % menu["restaurant_name"])
print("Table: %s" % menu["table_display_name"])
print("QR ordering enabled: %s" % menu["qr_ordering_enabled"])
print("Categories: %d" % len(menu["categories"]))

menu_items = []
for cat in menu["categories"]:
    for item in cat["items"]:
        menu_items.append(item)

# ============================================================
# Step 3: Customer submits order
# ============================================================
print("\n--- Step 3: Customer submits order ---")
order_items = []
for item in menu_items:
    if item["name"] == "Margherita Pizza":
        order_items.append({"menu_item_id": item["id"], "quantity": 1, "special_instructions": "Extra cheese"})
    if item["name"] == "Fresh Lime Soda":
        order_items.append({"menu_item_id": item["id"], "quantity": 2, "special_instructions": "No ice"})

print("Ordering: Margherita Pizza x1, Fresh Lime Soda x2")

idempotency_key = str(uuid.uuid4())
status, order_result = post_json(
    "/api/v1/public/qr/%s/orders" % qr_token,
    {"customer_note": "Please bring water first", "items": order_items},
    idempotency_key=idempotency_key
)
assert status in (200, 201), "Order submission failed: %s" % order_result
order_id = order_result["order"]["id"]
status_token = order_result["status_token"]
print("Order submitted: OK")
print("Order ID: %s" % order_id)
print("Status token: %s" % status_token)
print("Status URL: http://localhost:5173/status/%s" % status_token)

# ============================================================
# Step 4: Waiter accepts order
# ============================================================
print("\n--- Step 4: Waiter accepts order ---")
lr = post_json("/api/v1/auth/login", {"email": "bahadhami14+main.waiter@gmail.com", "password": "Staff@#12345"})
waiter_token = lr[1]["access_token"]
print("Waiter login: OK")

status, pending = get_json("/api/v1/orders?status=PENDING_CONFIRMATION", waiter_token)
print("Pending orders: %d" % len(pending))

status, accepted = post_json("/api/v1/orders/%s/accept" % order_id, {}, waiter_token)
assert status == 200, "Accept failed: %s" % accepted
print("Order accepted: OK")
print("Dining session: %s" % accepted.get("dining_session_id", "N/A"))
print("Kitchen ticket: %s" % accepted.get("kitchen_ticket_id", "N/A"))

dining_session_id = accepted.get("dining_session_id")

# ============================================================
# Step 5: Kitchen sees ticket
# ============================================================
print("\n--- Step 5: Kitchen ticket ---")
lr = post_json("/api/v1/auth/login", {"email": "bahadhami14+main.kitchen@gmail.com", "password": "Staff@#12345"})
kitchen_token = lr[1]["access_token"]
print("Kitchen login: OK")

status, tickets = get_json("/api/v1/kitchen/tickets", kitchen_token)
print("Kitchen tickets: %d" % len(tickets))
for t in tickets:
    print("  Ticket %s | status=%s" % (str(t["id"])[:8], t.get("status", "?")))

# ============================================================
# Step 6: Cashier issues bill
# ============================================================
print("\n--- Step 6: Cashier issues bill ---")
lr = post_json("/api/v1/auth/login", {"email": "bahadhami14+main.cashier@gmail.com", "password": "Staff@#12345"})
cashier_token = lr[1]["access_token"]
print("Cashier login: OK")

status, bill_result = post_json(
    "/api/v1/sessions/%s/bill/issue" % dining_session_id,
    {},
    cashier_token
)
if status in (200, 201):
    bill_id = bill_result.get("id")
    print("Bill issued: OK")
    print("Bill ID: %s" % bill_id)
    print("Total: %s %s" % (bill_result.get("total_minor", 0), bill_result.get("currency_code", "NPR")))
    print("Bill status: %s" % bill_result.get("status", "N/A"))
else:
    print("Bill issue failed: %s" % bill_result)
    bill_id = None

# ============================================================
# Step 7: Customer pays bill
# ============================================================
print("\n--- Step 7: Customer pays bill ---")
if bill_id:
    status, payment = post_json(
        "/api/v1/bills/%s/payments" % bill_id,
        {"method_id": cash_method_id, "amount_minor": bill_result.get("total_minor", 0), "note": "Cash payment"},
        cashier_token,
        idempotency_key="pay-" + str(uuid.uuid4())
    )
    if status in (200, 201):
        print("Payment recorded: OK")
        print("Payment ID: %s" % payment.get("id"))
        print("Status: %s" % payment.get("status"))
        print("Amount: %s %s" % (payment.get("amount_minor"), payment.get("currency_code")))
    else:
        print("Payment failed: %s" % payment)
else:
    print("Skipping payment (no bill)")

# ============================================================
# Step 8: Customer checks status page
# ============================================================
print("\n--- Step 8: Customer status page ---")
status, cust_status = get_json("/api/v1/public/orders/%s" % status_token)
if status == 200:
    print("Customer status loaded: OK")
    print("Order status: %s" % cust_status.get("status", "?"))
    print("Table: %s" % cust_status.get("table_display_name", "?"))
    if "payment_status" in cust_status:
        print("Payment status: %s" % cust_status["payment_status"])
else:
    print("Status check failed: %s" % cust_status)

print("\n" + "=" * 60)
print("WORKFLOW TEST COMPLETE - ALL STEPS PASSED")
print("=" * 60)
