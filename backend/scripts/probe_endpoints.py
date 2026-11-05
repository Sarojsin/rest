"""Crawl every parameterless GET endpoint for each staff role and the platform
realm, flagging only server errors (5xx). Expected 401/403/404/422 are normal.

Run against a live dev server:
    .\\venv\\Scripts\\python.exe scripts\\probe_endpoints.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402

STAFF = {
    "owner": ("owner@harbor.example", "HarborOwner!1"),
    "manager": ("manager@harbor.example", "HarborManager!1"),
    "waiter": ("waiter@harbor.example", "HarborWaiter!1"),
    "kitchen": ("kitchen@harbor.example", "HarborKitchen!1"),
    "cashier": ("cashier@harbor.example", "HarborCashier!1"),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    schema = httpx.get(f"{args.base}/openapi.json", timeout=10).json()
    paths = [
        path
        for path, ops in schema["paths"].items()
        if "get" in ops and "{" not in path and not path.startswith("/api/platform/auth")
    ]
    print(f"{len(paths)} parameterless GET paths under test")

    server_errors: list[tuple[str, str, int]] = []
    results: dict[str, list[int]] = {}

    for role, (email, password) in STAFF.items():
        login = httpx.post(
            f"{args.base}/api/v1/auth/login",
            json={"email": email, "password": password},
            timeout=10,
        )
        if login.status_code != 200:
            print(f"login failed for {role}: {login.status_code}")
            return 1
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        codes = []
        for path in paths:
            if not path.startswith("/api/v1"):
                continue
            response = httpx.get(f"{args.base}{path}", headers=headers, timeout=15)
            codes.append(response.status_code)
            if response.status_code >= 500:
                server_errors.append((role, path, response.status_code))
                print(f"  5xx {role} {path} -> {response.status_code}")
        results[role] = codes
        ok = sum(1 for c in codes if c == 200)
        denied = sum(1 for c in codes if c in (401, 403))
        print(f"{role:8s} {len(codes):3d} calls: {ok} ok, {denied} denied")

    platform_origin = (settings.platform_admin_origin_list or ["http://localhost:5173"])[0]
    print(f"platform origin allowlist: {settings.platform_admin_origin_list}")

    print("\nServer errors:", len(server_errors))
    for role, path, code in server_errors:
        print(f"  - {role} {path} -> {code}")
    return 1 if server_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
