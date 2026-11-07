import requests
import re

def check_page(url, timeout=15):
    """Check a page and return its status and basic info"""
    try:
        r = requests.get(url, timeout=timeout)
        content = r.text[:2000] if r.text else ""
        
        result = {
            "url": url,
            "status": r.status_code,
            "has_react": False,
            "forms": 0,
            "buttons": 0,
            "key_text": [],
        }
        
        # Check for React app indicators
        result["has_react"] = (
            r.text.find('/@react-refresh') >= 0 or
            'window.$RefreshReg$' in r.text or
            'data-reactroot' in r.text
        )
        
        # Count form tags
        result["forms"] = r.text.count('<form') if r.text else 0
        
        # Count button occurrences
        result["buttons"] = len(re.findall(r'pf-button', r.text)) if r.text else 0
        
        # Extract key visible text
        clean = re.sub(r'<script[^>]*>.*?</script>', '', r.text, flags=re.DOTALL)
        clean = re.sub(r'<style[^>]*>.*?</style>', '', clean, flags=re.DOTALL)
        text_only = re.sub(r'<[^>]+>', ' ', clean)
        words = [w.strip() for w in text_only[:300].split() if w.strip() and len(w) > 2]
        result["key_text"] = words[:15]
        
        return result
    except Exception as e:
        return {"url": url, "error": str(e), "status": 0}

# Pages to check - all admin pages
pages = [
    "http://192.168.1.5:5173/admin/onboarding",
    "http://192.168.1.5:5173/admin/tenants",
    "http://192.168.1.5:5173/admin/login",
    "http://192.168.1.5:5173/",
    "http://192.168.1.5:5173/admin/plans",
    "http://192.168.1.5:5173/admin/subscriptions",
    "http://192.168.1.5:5173/admin/settings",
    "http://192.168.1.5:5173/admin/dashboard",
    "http://192.168.1.5:5173/admin/users",
    "http://192.168.1.5:5173/admin/analytics",
]

print("ADMIN PAGES ACCESSIBILITY CHECK")
print("=" * 60)

for page in pages:
    result = check_page(page)
    print(f"\nURL: {result['url']}")
    print(f"  Status: {result['status']}")
    if result['status'] == 0:
        print(f"  ERROR: {result['error']}")
    else:
        print(f"  React: {result['has_react']}")
        print(f"  Forms: {result['forms']}")
        print(f"  Buttons: {result['buttons']}")
        if result['key_text']:
            print(f"  Key text: {', '.join(result['key_text'][:8])}")
    print()

print("=" * 60)