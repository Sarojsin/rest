import requests

r = requests.get('http://192.168.1.5:5173/auth/invitations/Z91LJid5QTGQ86bxrgEUwPYpmHCKYLmhsgiJ5bJ-Y3M', timeout=10)
print(f'Status: {r.status_code}')
print(f'Content length: {len(r.text)}')
print(f'First 2000 chars:')
print(r.text[:2000])