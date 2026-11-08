import requests

token = '1AFrc8KiwtU8U2oz7qYlcHNFKpp6qpiOyjSCJKbqmAk'

session = requests.Session()

# Test 1: Try with just password (no mfa_code)
print("=== Test 1: Password only ===")
r = session.post(f'http://127.0.0.1:8000/api/platform/auth/invitations/{token}/accept',
                 json={'password': 'TestPass123!'},
                 headers={'Origin': 'http://127.0.0.1:5173'},
                 timeout=10)
print(f'Status: {r.status_code}')
print(f'Response: {r.text[:500]}')

if r.status_code == 200:
    print('SUCCESS!')
else:
    print(f'Failed with status {r.status_code}')