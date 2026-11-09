import requests

session = requests.Session()
session.headers.update({'Origin': 'http://127.0.0.1:5173'})

# Step 1: Register with specified data
print("=" * 70)
print("STEP 1: Self-service Registration")
print("=" * 70)

payload = {
    'restaurant_name': 'random',
    'restaurant_slug': 'my-random',
    'owner_email': 'sarojsinghdhami91@gmail.com',
    'owner_name': 'jhone',
    'owner_phone': '1234567891',
    'plan_code': 'professional',
    'trial_days': 15,
    'contact_email': 'sarojsinghdhami91@gmail.com',
    'contact_phone': '1234567891',
    'legal_name': 'Legal Business Name',
    'timezone': 'Asia/Kathmandu',
    'currency_code': 'NPR',
    'source': 'self_service',
    'reason': 'Self-service registration for new restaurant'
}

r = session.post('http://127.0.0.1:8000/api/platform/public/register', json=payload, timeout=10)
print(f'Register status: {r.status_code}')
print(f'Register response: {r.text[:500]}')

if r.status_code == 201:
    data = r.json()
    reg_id = data.get('id')
    print(f'\nRegistration ID: {reg_id}')
    print(f'Status: {data.get("status")}')
    
    # Step 2: Approve the registration
    print('\n--- STEP 2: Admin Approves Registration ---')
    approve_payload = {'confirm': True, 'reason': 'Admin approval for test'}
    r2 = session.post(f'http://127.0.0.1:8000/api/platform/self-service/registrations/{reg_id}/approve',
                      json=approve_payload, timeout=10)
    print(f'Accept status: {r2.status_code}')
    print(f'Accept response: {r2.text[:500]}')
    
    if r2.status_code == 201:
        data2 = r2.json()
        invite_token = data2.get('invitation_token')
        print(f'\nInvitation token: {invite_token}')
        
        # Step 3: Test invitation acceptance
        print('\n--- STEP 3: Owner Accepts Invitation ---')
        r3 = session.post(f'http://127.0.0.1:8000/api/platform/auth/invitations/{invite_token}/accept',
                          json={'password': 'TestPass123!', 'mfa_code': '123456'},
                          timeout=10)
        print(f'Invite accept status: {r3.status_code}')
        print(f'Invite accept response: {r3.text[:500]}')
        
        if r3.status_code == 200:
            data3 = r3.json()
            print(f'\n✅ SUCCESS! User: {data3.get("user", {}).get("email")}')
            print(f'Role: {data3.get("user", {}).get("role")}')
            print(f'Access token: {data3.get("access_token", "N/A")[:60]}...')
        else:
            print(f'\n❌ Invitation acceptance failed')
    else:
        print(f'\n❌ Registration approval failed')
else:
    print(f'\n❌ Registration failed - this is expected if email already exists')
    print('   (Database may need reset if sarojsinghdhami91@gmail.com already has a registration)')