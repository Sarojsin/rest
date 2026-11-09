import requests
import json

# Step 1: First, we need to get the registration approved
# The approve endpoint is: POST /api/platform/self-service/registrations/{id}/approve
# It requires: confirm: true, reason: string

# But this endpoint requires authentication (tenant.create permission)
# Let me try without auth first to see the error, then we'll figure out the flow

reg_id = 'a2cb51e7-0629-420b-8770-ef6a70fc19c2'

session = requests.Session()
session.headers.update({'Origin': 'http://127.0.0.1:5173'})

# Try approval without auth
approve_payload = {'confirm': True, 'reason': 'Admin approval for onboarding'}
r = session.post(f'http://127.0.0.1:8000/api/platform/self-service/registrations/{reg_id}/approve',
                 json=approve_payload, timeout=10)
print(f'Approve status: {r.status_code}')
print(f'Response: {r.text[:300]}')