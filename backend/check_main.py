import requests

# Check if main.tsx loads correctly
r = requests.get('http://192.168.1.5:5173/src/main.tsx', timeout=10)
print(f'Status: {r.status_code}')
print(f'Content length: {len(r.text)}')
print(f'First 1000 chars:')
print(r.text[:1000])