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

# Use the order from the previous test
QR_TOKEN = "ewFx7F47Eg_i5298VJkWKeyj4YwhnZwU"
ORDER_ID = "5fe2abcd-fe03-4556-9299-24738b1cc81d"
STATUS_TOKEN = "HlJyrJQm9wpkpy0wH_jWLsoJEaVLpNKg83LE1M3ZxxU"

print("=== Step 5: Cashier issues bill ===")
lr = post_json("/api/v1/auth/login", {"email": "bahadhami14+main.cashier@gmail.com", "password": "Staff@#12345"})
cashier_token = lr[1]["access_token"]

# Get the dining session from order acceptance - we know it's 41692f3f-cecb-4573-b7d4-286ca83d55d8
session_id = "41692f3f-cecb-4573-b7d4-286ca83d55d8"

# Get bill for session
status, bill = get_json("/api/v1/sessions/%s/bill" % session_id, cashier_token)
if status == 200:
    print("Existing bill: %s" % bill)
else:
    print("No existing bill (status=%d), issuing new one..." % status)
    
    # Issue bill
    status, bill_result = post_json(
        "/api/v1/sessions/%s/bill/issue" % session_id,
        {},
        cashier_token
    )
    if status in (200, 201):
        print("Bill issued!")
        print("Bill ID: %s" % bill_result.get("id", "N/A"))
        print("Total: %s %s" % (bill_result.get("total_minor", "N/A"), bill_result.get("currency_code", "NPR")))
        print("Status: %s" % bill_result.get("status", "N/A"))
        bill_id = bill_result.get("id")
        
        # Record payment
        print("\n=== Customer pays ===")
        status, payment = post_json(
            "/api/v1/bills/%s/payments" % bill_id,
            {"amount_paid_minor": bill_result.get("total_minor", 0), "payment_method": "cash"},
            cashier_token
        )
        if status in (200, 201):
            print("Payment recorded!")
            print("Payment status: %s" % payment.get("status", "N/A"))
        else:
            print("Payment failed: %s" % payment)
    else:
        print("Bill issue failed: %s" % bill_result)

# Customer status page - final check
print("\n=== Customer status page (final) ===")
status, cust_status = get_json("/api/v1/public/orders/%s" % STATUS_TOKEN)
if status == 200:
    print("Customer status loaded!")
    print("Order status: %s" % cust_status.get("status", "?"))
    print("Table: %s" % cust_status.get("table_display_name", "?"))
    # Check if there's payment info
    if "payment_status" in cust_status:
        print("Payment status: %s" % cust_status["payment_status"])
else:
    print("Status failed: %s" % cust_status)

print("\n=== COMPLETE WORKFLOW FINISHED ===")
