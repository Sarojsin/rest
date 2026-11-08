import requests

# Check if the AcceptInvitationPage.tsx file is being served with our changes
r = requests.get('http://192.168.1.5:5173/src/pages/staff/AcceptInvitationPage.tsx', timeout=10)
print(f'Status: {r.status_code}')
print(f'Content length: {len(r.text)}')
print(f'First 500 chars:')
print(r.text[:500])
print()
# Check if useParams is being used
if 'useParams' in r.text:
    print('✓ useParams is imported in AcceptInvitationPage.tsx')
else:
    print('✗ useParams NOT imported in AcceptInvitationPage.tsx')
if 'useSearchParams' in r.text:
    print('✗ useSearchParams is still being used (should be useParams)')
else:
    print('✓ useSearchParams is NOT used (correctly replaced with useParams)')