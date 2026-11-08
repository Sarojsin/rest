import requests

# Test if React renders any content
r = requests.get('http://192.168.1.5:5173/auth/invitations/Z91LJid5QTGQ86bxrgEUwPYpmHCKYLmhsgiJ5bJ-Y3M', timeout=10)
print(f'Status: {r.status_code}')
print(f'Content length: {len(r.text)}')
print()
print('Checking for React-rendered content:')
print(f'  Has "Complete account": {"Complete account" in r.text}')
print(f'  Has "password": {"password" in r.text.lower()}')
print(f'  Has "Authenticator": {"authenticator" in r.text.lower()}')
print(f'  Has "#root" content: {">" in r.text.split("<div id=\"root\">")[1].split("</div>")[0] if "<div id=\"root\">" in r.text else "N/A"}')

# Check what's inside the root div
if "<div id=\"root\">" in r.text:
    root_content = r.text.split("<div id=\"root\">")[1].split("</div>")[0]
    print(f'\nRoot div content: "{root_content.strip()}"')