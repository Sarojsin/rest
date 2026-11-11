"""Phase B test: payments breakdown, waste report, expiring batches, kitchen speed.

Creates real data (a WASTE movement and a near-expiry batch with unique suffixes),
then verifies all four new report endpoints return them.
"""
import json
import time
import urllib.request
from datetime import UTC, datetime, timedelta

BASE = "http://127.0.0.1:8000"
SUFFIX = f"T{int(time.time())}"


def request(path, token=None, payload=None, method=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        BASE + path, data=data, headers=headers, method=method or ("POST" if data else "GET")
    )
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.URLError as e:  # noqa: F841
        return 0, {"raw": str(e)}
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {"raw": raw}


def main():
    # login owner
    st, body = request(
        "/api/v1/auth/login",
        payload={"email": "bahadhami14@gmail.com", "password": "Saroj@#12345"},
    )
    assert st == 200, f"login failed: {body}"
    token = body["access_token"]
    print(f"login: OK")

    # create a WASTE movement on the first ingredient
    st, ingredients = request("/api/v1/inventory/ingredients", token)
    assert st == 200 and len(ingredients) > 0, f"ingredients: {st}"
    ing = ingredients[0]
    st, move = request(
        "/api/v1/inventory/stock-movements",
        token,
        payload={
            "ingredient_id": ing["id"],
            "movement_type": "WASTE",
            "quantity": 120,
            "reason": f"Phase B test spoilage {SUFFIX}",
            "reference_type": "MANUAL",
        },
    )
    assert st == 201, f"waste movement create failed: {st} {move}"
    print(f"waste movement created: id={move['id']}")

    # create a near-expiry batch (expires in 2 days)
    st, batch = request(
        "/api/v1/inventory/batches",
        token,
        payload={
            "ingredient_id": ing["id"],
            "batch_no": f"PB-{SUFFIX}",
            "expiry_date": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
            "quantity": 7,
            "cost_per_unit_minor": 500,
        },
    )
    assert st == 201, f"batch create failed: {st} {batch}"
    print(f"batch created: batch_no={batch['batch_no']}")

    # ── 1. payments breakdown ──
    st, pay = request("/api/v1/reports/payments?days=30", token)
    assert st == 200, f"payments report failed: {st} {pay}"
    print(f"payments: currency={pay['currency_code']} collected={pay['total_collected_minor']} "
          f"succeeded={pay['succeeded_count']} failed={pay['failed_count']}")
    for m in pay["methods"]:
        print(f"  method={m['method']} count={m['payment_count']} amount={m['amount_minor']}")
    assert isinstance(pay["methods"], list)

    # ── 2. kitchen speed ──
    st, speed = request("/api/v1/reports/kitchen-speed?days=30", token)
    assert st == 200, f"kitchen-speed failed: {st} {speed}"
    print(f"kitchen-speed: completed={speed['completed_ticket_count']} "
          f"avg={speed['avg_prep_seconds']}s fastest={speed['fastest_prep_seconds']}s "
          f"slowest={speed['slowest_prep_seconds']}s")
    if speed["slowest_tickets"]:
        print(f"  slowest ticket #{speed['slowest_tickets'][0]['ticket_number']} "
              f"prep={speed['slowest_tickets'][0]['prep_seconds']}s")

    # ── 3. waste report contains the new movement ──
    st, waste = request("/api/v1/inventory/reports/waste?days=30", token)
    assert st == 200, f"waste report failed: {st} {waste}"
    assert waste["window_days"] == 30
    found = any(str(ing["id"]) == str(e["ingredient_id"]) for e in waste["waste"])
    assert found, "waste report missing the ingredient we just wasted"
    total = sum(e["total_wasted"] for e in waste["waste"])
    assert total >= 120, f"expected at least 120 wasted, got {total}"
    print(f"waste: events={waste['event_count']} rows={len(waste['waste'])} total={total} -> contains test data")

    # ── 4. expiring batches contains the new batch ──
    st, exp = request("/api/v1/inventory/reports/expiring-batches?days=7", token)
    assert st == 200, f"expiring-batches failed: {st} {exp}"
    found = any(b["batch_no"] == f"PB-{SUFFIX}" for b in exp["batches"])
    assert found, "expiring-batches report missing the batch we just created"
    test_batch = next(b for b in exp["batches"] if b["batch_no"] == f"PB-{SUFFIX}")
    assert test_batch["expired"] is False and test_batch["quantity"] == 7
    assert test_batch["cost_value_minor"] == 7 * 500
    print(f"expiring-batches: rows={len(exp['batches'])} -> PB-{SUFFIX} found (qty=7, value=3500, not expired)")

    # ── failure path: bad params ──
    st, _ = request("/api/v1/inventory/reports/waste?days=99999", token)
    assert st == 200, "days clamp should not 4xx"  # clamped to 365

    print("\nALL PHASE B TESTS PASSED")


if __name__ == "__main__":
    main()
