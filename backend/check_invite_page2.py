import requests

r = requests.get('http://192.168.1.5:5173/auth/invitations/Z91LJid5QTGQ86bxrgEUwPYpmHCKYLmhsgiJ5bJ-Y3M', timeout=10)
print(f'Status: {r.status_code}')
print(f'Content length: {len(r.text)}')
print()
# Check if root div has content
if "<div id=\"root\">" in r.text:
    root_content = r.text.split("<div id=\"root\">")[1].split("</div>")[0]
    print(f'Root div content: "{root_content.strip()}"')
else:
    print('No root div found')
print()
print(f'First 1500 chars:')
print(r.text[:1500])