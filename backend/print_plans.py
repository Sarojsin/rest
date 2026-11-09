import requests
import json

session = requests.Session()
session.headers.update({'Origin': 'http://127.0.0.1:5173'})
r = session.get('http://127.0.0.1:8000/api/platform/public/plans', timeout=10)
data = r.json()
for p in data['items'][:4]:
    code = p['code']
    name = p['name']
    monthly = p['price_monthly_minor'] / 100
    trial = p['trial_days']
    public = p['is_public']
    print(f'Code: {code}, Name: {name}, Monthly: {monthly}, Trial: {trial}, Public: {public}')