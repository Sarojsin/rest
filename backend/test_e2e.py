import requests
import json

session = requests.Session()
session.headers.update({'Origin': 'http://127.0.0.1:5173'})

# Step 1: Register a new restaurant
print("=" * 70)
print("STEP 1: Self-service Registration")
print("=" * 70)

payload = {
    'restaurant_name': 'Test Restaurant XYZ',
    'restaurant_slug': 'test-restaurantxyz-new84',
    'owner_email': 'test-owner-xyz84@example.com',
    'owner_name': 'Test Owner XYZ',
    'owner_phone': '1234567891',
    'plan_code': 'professional',
    'contact_email': 'test-owner-xyz84@example.com',
    'contact_phone': '123-456-7890',
    'legal_name': 'Test Legal Name XYZ',
    'source': 'self_service',
    'reason': 'End-to-end test'
}

r = session.post('http://127.0.0.1:8000/api/platform/public/register', json=payload, timeout=10)
print(f'Register status: {r.status_code}')

if r.status_code == 201:
    data = r.json()
    reg_id = data.get('id')
    print(f'Registration successful!')
    print(f'Registration ID: {reg_id}')
    print(f'Status: {data.get("status")}')
else:
    print(f'Registration failed: {r.text[:200]}')
    exit(1)

# Step 2: Approve the registration (admin action)
print("\n" + "=" * 70)
print("STEP 2: Admin Approves Registration")
print("=" * 70)

approve_payload = {
    'confirm': True,
    'reason': 'Admin approval for end-to-end test'
}

r = session.post(f'http://127.0.0.1:8000/api/platform/self-service/registrations/{reg_id}/approve',
                 json=approve_payload, timeout=10)
print(f'Accept status: {r.status_code}')
if r.status_code == 201:
    data = r.json()
    print('Approval successful!')
    print(f'New status: {data.get("status")}')
    print(f'Invitation token: {data.get("invitation_token")}')
    invite_token = data.get('invitation_token')
    print(f'Restaurant ID: {data.get("restaurant_id")}')
else:
    print(f'Acceptance failed: {r.text[:300]}')
    exit(1)

# Step 3: Test invitation acceptance via the accept invitation endpoint
print("\n" + "=" * 70)
print("STEP 3: Owner Accepts Invitation")
print("=" * 70)

# The owner clicks the invitation link and sets password + MFA
invite_accept_payload = {
    'password': 'TestPass123!',
    'mfa_code': '123456'
}

r = session.post(f'http://127.0.0.1:8000/api/platform/auth/invitations/{invite_token}/accept',
                 json=invite_accept_payload, timeout=10)
print(f'Invitation accept status: {r.status_code}')
if r.status_code == 200:
    data = r.json()
    print('Invitation accepted successfully!')
    print(f'User: {data.get("user", {}).get("email")}')
    print(f'Token: {data.get("access_token", "N/A")[:50]}...')
    print(f'Role: {data.get("user", {}).get("role")}')
    print(f'\n✅ Complete onboarding flow successful!')
    print(f'Owner can now access staff dashboard')
else:
    print(f'Invitation accept failed: {r.text[:300]}')

print("\n" + "=" * 70)
print("END-TO-END TEST COMPLETE")
print("=" * 70)