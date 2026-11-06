import json

path = 'E:/rest/apps/web/package.json'
with open(path) as f:
    content = f.read()

content = content.replace(
    '"build": "tsc -b && vite build",',
    '"build": "vite build",'
)
content = content.replace(
    '"build:admin": "tsc -b && vite build --config vite.admin.config.ts",',
    '"build:admin": "vite build --config vite.admin.config.ts",'
)

with open(path, 'w') as f:
    f.write(content)

print('Fixed package.json build scripts')