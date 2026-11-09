import requests

session = requests.Session()
session.headers.update({'Origin': 'http://127.0.0.1:5173'})

# Use the existing invitation token from the seeded data
invite_token = '1AFrc8KiwtU8U2oz7qYlcHNFKpp6qpiOyjSCJKbqmAk'

# Test invitation acceptance
print(f"Testing invitation acceptance with token: {invite_token}")
r = session.post(f'http://127.0.0.1:8000/api/platform/auth/invitations/{invite_token}/accept',
                 json={'password': 'TestPass123!', 'mfa_code': '123456'},
                 timeout=10)

print(f'Status: {r.status_code}')
print(f'Response: {r.text[:500]}')

if r.status_code == 200:
    data = r.json()
    print(f'\nInvitation accepted successfully!')
    print(f'User: {data.get("user", {}).get("email")}')
    print(f'Token: {data.get("access_token", "N/A")[:60]}...')
    print(f'Role: {data.get("user", {}).get("role")}')
else:
    print(f'\nInvitation acceptance failed')