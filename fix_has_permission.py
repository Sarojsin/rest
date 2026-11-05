import os, re

pages_dir = 'apps/web/src/pages/admin'
fixes = {
    'hasPermission': 'has',
    # Remove unused navigate (keep import since it's used in some places for navigation)
}

for f in sorted(os.listdir(pages_dir)):
    if not f.endswith('.tsx'): continue
    path = os.path.join(pages_dir, f)
    content = open(path).read()
    original = content
    
    # Replace hasPermission with has
    content = content.replace('hasPermission', 'has')
    
    if content != original:
        open(path, 'w').write(content)
        print(f'Fixed {f}')
    else:
        print(f'No changes needed: {f}')
print('Done')