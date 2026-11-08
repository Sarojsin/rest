import requests

# Check if App.tsx loads correctly
r = requests.get('http://192.168.1.5:5173/src/App.tsx', timeout=10)
print(f'Status: {r.status_code}')
print(f'Content length: {len(r.text)}')
print(f'First 1500 chars:')
print(r.text[:1500])