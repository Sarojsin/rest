import requests

# Try to list registrations via the API (may need auth)
session = requests.Session()
r = session.get('http://127.0.0.1:8000/api/platform/self-service/registrations', 
                headers={'Origin': 'http://127.0.0.1:5173'},
                timeout=10)
print('List registrations status:', r.status_code)
print('Response:', r.text[:300] if r.status_code < 500 else 'Error')