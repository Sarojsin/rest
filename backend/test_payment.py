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

# Login as cashier
lr = post_json("/api/v1/auth/login", {"email": "bahadhami14+main.cashier@gmail.com", "password": "Staff@#12345"})
cashier_token = lr[1]["access_token"]
print("Cashier login: OK")

# Create a cash payment method
status, method = post_json("/api/v1/payment-methods", {
    "label": "Cash",
    "kind": "CASH",
    "account_hint": "",
    "instructions": "",
    "is_active": True
}, cashier_token)
if status in (200, 201):
    method_id = method["id"]
    print("Payment method created: %s (%s)" % (method["label"], str(method_id)[:8]))
else:
    print("Payment method creation failed: %s" % method)
    # Try getting existing methods
    status, methods = get_json("/api/v1/payment-methods", cashier_token)
    print("Existing methods: %d" % len(methods))
    if methods:
        method_id = methods[0]["id"]
    else:
        print("Cannot proceed - no payment method")
        exit(1)

# Record payment for bill
bill_id = "18f530bc-8d70-4f1c-af63-16eb173ff82f"
amount_minor = 3222

status, payment = post_json(
    "/api/v1/bills/%s/payments" % bill_id,
    {"method_id": method_id, "amount_minor": amount_minor, "note": "Cash payment"},
    cashier_token,
    idempotency_key="pay-" + str(uuid.uuid4())
)
if status in (200, 201):
    print("\nPayment recorded: OK")
    print("Payment ID: %s" % payment.get("id"))
    print("Status: %s" % payment.get("status"))
    print("Amount: %s %s" % (payment.get("amount_minor"), payment.get("currency_code")))
else:
    print("Payment failed: %s" % payment)

# Check final order status
status_token = "3UWBTYFligX7EnGx_hUUmK-Tdv3SyxLiS29stxpgkOA"
status, cust_status = get_json("/api/v1/public/orders/%s" % status_token)
if status == 200:
    print("\nFinal customer status:")
    print("  Order status: %s" % cust_status.get("status", "?"))
    print("  Table: %s" % cust_status.get("table_display_name", "?"))
    if "payment_status" in cust_status:
        print("  Payment status: %s" % cust_status["payment_status"])

print("\n=== PAYMENT STEP COMPLETE ===")
