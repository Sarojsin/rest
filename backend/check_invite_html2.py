import requests

r = requests.get('http://192.168.1.5:5173/auth/invitations/Z91LJid5QTGQ86bxrgEUwPYpmHCKYLmhsgiJ5bJ-Y3M', timeout=10)
print(f'Status: {r.status_code}')
print(f'Content length: {len(r.text)}')
if '<div id="root">' in r.text:
    root = r.text.split('<div id="root">')[1].split("</div>")[0]
    print(f'Root div content: "{root.strip()}"')
else:
    print('No root div')
print(f'First 500 chars: {r.text[:500]}')