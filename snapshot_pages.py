import requests
import re

def snapshot_page(url, timeout=15):
    """Get detailed page snapshot content"""
    try:
        r = requests.get(url, timeout=timeout)
        content = r.text[:3000] if r.text else ""
        
        # Remove script tags for readability
        clean = re.sub(r'<script[^>]*>.*?</script>', '[JS]', content, flags=re.DOTALL)
        clean = re.sub(r'<style[^>]*>.*?</style>', '[CSS]', clean, flags=re.DOTALL)
        
        # Find all UI elements
        elements = {
            "headings": re.findall(r'<h[1-6][^>]*>([^<]+)</h[1-6]>', clean),
            "inputs": re.findall(r'<input[^>]+>', clean),
            "buttons": re.findall(r'<button[^>]+>([^<]+)</button>', clean) or [],
            "links": re.findall(r'<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>', clean) or [],
        }
        
        # Count occurrences of key terms
        key_terms = ["pending", "approve", "register", "tenant", "onboard", "status", "create", "restaurant"]
        term_counts = {}
        for term in key_terms:
            count = clean.lower().count(term.lower())
            if count > 0:
                term_counts[term] = count
        
        return {
            "status": r.status_code,
            "headings": [h.strip() for h in elements["headings"][:10]],
            "input_count": len(elements["inputs"]),
            "button_texts": [b.strip() for b in elements["buttons"][:10]],
            "link_count": len(elements["links"]),
            "key_terms": term_counts,
        }
    except Exception as e:
        return {"url": url, "error": str(e)}

# Check all admin pages
pages = [
    "http://192.168.1.5:5173/admin/onboarding",
    "http://192.168.1.5:5173/admin/tenants",
    "http://192.168.1.5:5173/admin/login",
    "http://192.168.1.5:5173/",
    "http://192.168.1.5:5173/admin/plans",
    "http://192.168.1.5:5173/admin/settings",
]

print("ADMIN PAGES DETAILED SNAPSHOT")
print("=" * 50)

for page in pages:
    result = snapshot_page(page)
    print(f"\nURL: {page}")
    print(f"  Status: {result['status']}")
    if 'error' in str(result.get('status', '')):
        print(f"  ERROR: {result['error']}")
    else:
        print(f"  Headings: {result['headings']}")
        print(f"  Inputs: {result['input_count']}")
        print(f"  Buttons: {result['button_texts']}")
        print(f"  Links: {result['link_count']}")
        print(f"  Key terms: {result['key_terms']}")
    print()

print("=" * 50)
print("DONE")
print("=" * 50)