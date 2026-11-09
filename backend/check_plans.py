import requests
import json

session = requests.Session()
session.headers.update({'Origin': 'http://127.0.0.1:5173'})

# Check public plans
r = session.get('http://127.0.0.1:8000/api/platform/public/plans', timeout=10)
print(f'Public plans status: {r.status_code}')
if r.status_code == 200:
    data = r.json()
    print(f'Plans: {json.dumps(data, indent=2)[:1000]}')
else:
    print(f'Response: {r.text[:500]}')