import requests
import json

session = requests.Session()
session.headers.update({'Origin': 'http://127.0.0.1:5173'})

# Get OpenAPI spec
r = session.get('http://127.0.0.1:8000/openapi.json', timeout=10)
print(f'Status: {r.status_code}')
print(f'Content type: {r.headers.get("content-type", "unknown")}')
if r.status_code == 200:
    data = r.json()
    paths = list(data['paths'].keys())
    for p in sorted(paths):
        if 'registrations' in p.lower() or 'accept' in p.lower() or 'self-service' in p.lower():
            print(p)