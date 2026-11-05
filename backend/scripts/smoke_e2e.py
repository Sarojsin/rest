"""Live end-to-end smoke test against a running backend (local dev).

Exercises both realms the way a real client does:

* platform (Super Admin): Origin-checked login, MFA enrollment/verification,
  HttpOnly cookie session, CSRF-protected step-up and logout;
* restaurant staff: owner/manager/waiter/kitchen/cashier sign-in and the
  endpoints each role is expected to reach, plus the public QR ordering flow.

Usage (backend venv, from ``backend``):

    .\\venv\\Scripts\\python.exe scripts\\smoke_e2e.py
    .\\venv\\Scripts\\python.exe scripts\\smoke_e2e.py --base http://127.0.0.1:8000

Exit code is non-zero when any hard check fails.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import httpx
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.modules.platform.models import PlatformAdmin  # noqa: E402
from app.modules.platform.services.crypto import decrypt_secret  # noqa: E402
from app.modules.platform.services.mfa import totp_at  # noqa: E402

DEMO_QR = "table-harbor-1-alpha"
STAFF = [
    ("owner@harbor.example", "HarborOwner!1", "owner"),
    ("manager@harbor.example", "HarborManager!1", "manager"),
    ("waiter@harbor.example", "HarborWaiter!1", "waiter"),
    ("kitchen@harbor.example", "HarborKitchen!1", "kitchen"),
    ("cashier@harbor.example", "HarborCashier!1", "cashier"),
]
PLATFORM_ADMIN = ("platform@harbor.example", "PlatformOwner!1")

PASS = "PASS"
FAIL = "FAIL"
INFO = "INFO"

failures: list[str] = []
SECRET: list[str] = [""]


def check(condition: bool, label: str, detail: str = "") -> bool:
    status = PASS if condition else FAIL
    line = f"[{status}] {label}"
    if detail:
        line += f" :: {detail}"
    print(line)
    if not condition:
        failures.append(label)
    return condition


def note(message: str) -> None:
    print(f"[{INFO}] {message}")


def code() -> str:
    return totp_at(SECRET[0], datetime.now(UTC))


def platform_secret_for(email: str) -> str:
    db = SessionLocal()
    try:
        admin = db.scalar(select(PlatformAdmin).where(PlatformAdmin.email == email))
        if admin is None or not admin.mfa_secret_encrypted:
            raise SystemExit(f"no enrolled MFA secret for {email}")
        return decrypt_secret(admin.mfa_secret_encrypted)
    finally:
        db.close()


def platform_flow(base: str, origin: str) -> None:
    print("\n=== Platform realm (Super Admin) ===")
    client = httpx.Client(timeout=10)
    headers = {"Origin": origin}
    email, password = PLATFORM_ADMIN

    login = client.post(
        f"{base}/api/platform/auth/login",
        json={"email": email, "password": password},
        headers=headers,
    )
    check(login.status_code == 200, "platform login", f"{login.status_code} {login.text[:120]}")
    if login.status_code != 200:
        return
    challenge = login.json()

    if challenge.get("enrollment_required"):
        started = client.post(
            f"{base}/api/platform/auth/mfa/enroll/start",
            json={"ticket": challenge["ticket"]},
            headers=headers,
        )
        check(started.status_code == 200, "MFA enrollment start", f"{started.status_code} {started.text[:120]}")
        if started.status_code != 200:
            return
        SECRET[0] = started.json()["secret"]
        verified = client.post(
            f"{base}/api/platform/auth/mfa/enroll/verify",
            json={"ticket": challenge["ticket"], "code": totp_at(SECRET[0], datetime.now(UTC))},
            headers=headers,
        )
        check(
            verified.status_code == 200,
            "MFA enrollment verify",
            f"{verified.status_code} {verified.text[:120]}",
        )
        if verified.status_code == 200:
            codes = verified.json().get("recovery_codes") or []
            check(len(codes) == settings.platform_recovery_code_count, "recovery codes issued")
    else:
        SECRET[0] = platform_secret_for(email)
        verified = client.post(
            f"{base}/api/platform/auth/mfa/verify",
            json={"ticket": challenge["ticket"], "code": code()},
            headers=headers,
        )
        check(verified.status_code == 200, "MFA verify", f"{verified.status_code} {verified.text[:120]}")

    cookie_names = {c.name for c in client.cookies.jar}
    check("platform_access" in cookie_names, "access cookie stored")
    check("platform_refresh" in cookie_names, "refresh cookie stored")
    check("platform_csrf" in cookie_names, "csrf cookie readable")
    if "platform_access" in cookie_names:
        jar = next(c for c in client.cookies.jar if c.name == "platform_access")
        check(not jar.secure, "dev cookie is not Secure (plain HTTP)")

    me = client.get(f"{base}/api/platform/auth/me")
    check(me.status_code == 200, "platform /me", f"{me.status_code} {me.text[:120]}")
    if me.status_code == 200:
        body = me.json()
        check(body["role"] == "superadmin", "signed in as superadmin", body["role"])
        check(bool(body.get("permissions")), "permissions returned", str(len(body["permissions"])))

    csrf = client.cookies.get("platform_csrf") or ""
    step_up = client.post(
        f"{base}/api/platform/auth/step-up",
        json={"password": password, "code": code()},
        headers={"Origin": origin, "X-CSRF-Token": csrf},
    )
    check(step_up.status_code == 200, "step-up with CSRF", f"{step_up.status_code} {step_up.text[:120]}")

    no_csrf = client.post(
        f"{base}/api/platform/auth/step-up",
        json={"password": password, "code": code()},
        headers={"Origin": origin},
    )
    check(
        no_csrf.status_code == 403 and no_csrf.json().get("code") == "CSRF_INVALID",
        "step-up without CSRF is rejected",
        f"{no_csrf.status_code} {no_csrf.text[:120]}",
    )

    sessions = client.get(f"{base}/api/platform/auth/sessions")
    check(sessions.status_code == 200, "session list", f"{sessions.status_code}")
    if sessions.status_code == 200:
        rows = sessions.json()["sessions"]
        check(len(rows) >= 1 and rows[0]["current"] is True, "current session marked")

    logout = client.post(
        f"{base}/api/platform/auth/logout",
        headers={"Origin": origin, "X-CSRF-Token": csrf},
    )
    check(logout.status_code == 204, "logout", f"{logout.status_code}")
    after = client.get(f"{base}/api/platform/auth/me")
    check(after.status_code == 401, "session cleared after logout", str(after.status_code))


def staff_token(base: str, email: str, password: str) -> str | None:
    response = httpx.post(
        f"{base}/api/v1/auth/login",
        json={"email": email, "password": password},
        timeout=10,
    )
    if response.status_code != 200:
        check(False, f"staff login {email}", f"{response.status_code} {response.text[:120]}")
        return None
    token = response.json()["access_token"]
    check(True, f"staff login {email}", response.json()["user"]["membership"]["role"])
    return token


def staff_flow(base: str) -> None:
    print("\n=== Restaurant realm (staff roles) ===")
    tokens: dict[str, str] = {}
    for email, password, role in STAFF:
        token = staff_token(base, email, password)
        if token:
            tokens[role] = token

    def auth(role: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {tokens[role]}"}

    if "owner" in tokens:
        me = httpx.get(f"{base}/api/v1/me", headers=auth("owner"), timeout=10)
        check(me.status_code == 200, "owner /me", f"{me.status_code}")
        if me.status_code == 200:
            check(me.json()["membership"]["role"] == "owner", "owner role")

    expected = {
        "owner": ["/api/v1/menu", "/api/v1/tables", "/api/v1/orders", "/api/v1/reports/sales"],
        "manager": ["/api/v1/menu", "/api/v1/tables", "/api/v1/orders", "/api/v1/reports/sales"],
        "waiter": ["/api/v1/menu", "/api/v1/tables", "/api/v1/orders"],
        "kitchen": ["/api/v1/kitchen/tickets"],
        "cashier": ["/api/v1/tables", "/api/v1/orders"],
    }
    for role, paths in expected.items():
        if role not in tokens:
            continue
        for path in paths:
            response = httpx.get(f"{base}{path}", headers=auth(role), timeout=10)
            check(response.status_code == 200, f"{role} GET {path}", str(response.status_code))

    if "kitchen" in tokens:
        denied = httpx.post(
            f"{base}/api/v1/sessions/{uuid.uuid4()}/bill/issue",
            headers=auth("kitchen"),
            timeout=10,
        )
        check(denied.status_code == 403, "kitchen cannot issue a bill", str(denied.status_code))

    # Public QR ordering: submit, waiter accepts, kitchen sees the ticket.
    if "waiter" in tokens and "kitchen" in tokens:
        menu = httpx.get(f"{base}/api/v1/public/qr/{DEMO_QR}/menu", timeout=10)
        check(menu.status_code == 200, "public QR menu", str(menu.status_code))
        if menu.status_code == 200:
            item_id = menu.json()["categories"][0]["items"][0]["id"]
            submit = httpx.post(
                f"{base}/api/v1/public/qr/{DEMO_QR}/orders",
                json={"items": [{"menu_item_id": item_id, "quantity": 1}], "customer_note": "smoke"},
                headers={"Idempotency-Key": f"smoke-{uuid.uuid4()}"},
                timeout=10,
            )
            check(submit.status_code == 200, "QR order submit", f"{submit.status_code} {submit.text[:120]}")
            if submit.status_code == 200:
                order_id = submit.json()["order"]["id"]
                check(
                    submit.json()["order"]["status"] == "PENDING_CONFIRMATION",
                    "QR order starts PENDING_CONFIRMATION",
                )
                accept = httpx.post(
                    f"{base}/api/v1/orders/{order_id}/accept",
                    headers=auth("waiter"),
                    timeout=10,
                )
                check(accept.status_code == 200, "waiter accepts QR order", f"{accept.status_code} {accept.text[:120]}")
                tickets = httpx.get(f"{base}/api/v1/kitchen/tickets", headers=auth("kitchen"), timeout=10)
                check(tickets.status_code == 200, "kitchen sees ticket", str(tickets.status_code))

    if "waiter" in tokens:
        call = httpx.post(f"{base}/api/v1/public/qr/{DEMO_QR}/service-calls", timeout=10)
        check(call.status_code == 200, "public service call", str(call.status_code))
        listing = httpx.get(
            f"{base}/api/v1/service-calls?status=REQUESTED",
            headers=auth("waiter"),
            timeout=10,
        )
        check(listing.status_code == 200, "waiter sees service calls", str(listing.status_code))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--origin",
        default=(settings.platform_admin_origin_list or ["http://localhost:5173"])[0],
    )
    args = parser.parse_args()

    health = httpx.get(f"{args.base}/health", timeout=5)
    check(health.status_code == 200, "health", str(health.status_code))

    platform_flow(args.base, args.origin)
    staff_flow(args.base)

    print("\n=== Summary ===")
    if failures:
        print(f"{len(failures)} failure(s):")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
