import requests

combos = [
    ("superadmin", "platform@harbor.example", "PlatformOwner!1"),
    ("ops", "ops@harbor.example", "PlatformOps!1"),
    ("billing", "billing@harbor.example", "PlatformBilling!1"),
    ("support", "support@harbor.example", "PlatformSupport!1"),
]

endpoints = [
    ("GET", "/api/platform/tenants", "Tenant access"),
    ("GET", "/api/platform/plans", "Plans access"),
    ("GET", "/api/platform/subscriptions", "Subscriptions access"),
    ("GET", "/api/platform/invoices", "Invoices access"),
    ("GET", "/api/platform/payments", "Payments access"),
    ("GET", "/api/platform/refunds", "Refunds access"),
    ("GET", "/api/platform/platform-users", "Platform users access"),
    ("GET", "/api/platform/audit-logs", "Audit logs access"),
    ("GET", "/api/platform/settings", "Settings access"),
    ("GET", "/api/platform/diagnostics/health", "Diagnostics access"),
]

for role, email, password in combos:
    session = requests.Session()
    r = session.post('http://127.0.0.1:8000/api/platform/auth/login',
                     json={'email': email, 'password': password},
                     headers={'Origin': 'http://127.0.0.1:5173'},
                     timeout=10)
    print(f"\n{'='*60}")
    print(f"Role: {role} ({email})")
    print(f"Login status: {r.status_code}")
    if r.status_code == 200:
        print("  Login SUCCESS")
        for method, path, name in endpoints:
            r2 = session.get(f'http://127.0.0.1:8000{path}',
                            headers={'Origin': 'http://127.0.0.1:5173'},
                            timeout=10)
            icon = "[OK]" if r2.status_code == 200 else "[DENY]"
            print(f"    {icon} {name}: {r2.status_code}")
    else:
        print(f"  Login FAILED: {r.text[:100]}")
    session.close()