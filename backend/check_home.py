import requests

r = requests.get('http://192.168.1.5:5173/', timeout=10)
print(f'Status: {r.status_code}')
print(f'Content length: {len(r.text)}')
print(f'First 1500 chars:')
print(r.text[:1500])