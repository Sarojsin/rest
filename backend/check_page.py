import requests

r = requests.get('http://127.0.0.1:5173/auth/invitations/x3Ub1j303tR0JczULbxceJX7dVBjuJ61IhZ1mG0HJ7M', timeout=10)
print('Status:', r.status_code)
print('Content length:', len(r.text))
print('First 1000 chars:')
print(r.text[:1000])
print()
print('Has AcceptInvitation:', 'AcceptInvitation' in r.text)
print('Has Complete account:', 'Complete account' in r.text)
print('Has Complete account setup:', 'Complete account setup' in r.text)
print('Has password:', 'password' in r.text.lower())
print('Has authenticator:', 'authenticator' in r.text.lower())