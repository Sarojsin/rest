import requests

# Test the invitation acceptance API with the actual token
session = requests.Session()

token = 'x3Ub1j303tR0JczULbxceJX7dVBjuJ61IhZ1mG0HJ7M'

print("=== Testing invitation acceptance API ===")
r = session.post(f'http://127.0.0.1:8000/api/platform/auth/invitations/{token}/accept',
                 json={'password': 'TestPass123!', 'mfa_code': '000000'},
                 headers={'Origin': 'http://127.0.0.1:5173'},
                 timeout=10)
print(f'Status: {r.status_code}')
print(f'Response: {r.text[:500]}')

if r.status_code == 200:
    print('\n✅ Invitation acceptance API works!')
    print(f'Token: {token}')
    print(f'Invitation URL: http://192.168.1.5:5173/auth/invitations/{token}')
else:
    print(f'\n❌ Invitation acceptance API failed')