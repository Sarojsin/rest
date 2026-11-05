import os

pages_dir = 'apps/web/src/pages/admin'

# Fix 1: Cast res as Response for platformFetch calls
# Fix 2: Restore useNavigate + navigate in AdminLayout, AdminLoginPage, AdminMfaPage

for f in sorted(os.listdir(pages_dir)):
    if not f.endswith('.tsx'): continue
    path = os.path.join(pages_dir, f)
    content = open(path).read()
    original = content
    
    # Fix: const res = await platformFetch(url) -> const res: Response = await platformFetch(url)
    content = content.replace('const res = await platformFetch(', 'const res: Response = await platformFetch(')
    
    if content != original:
        open(path, 'w').write(content)
        print(f'Fixed res typing in {f}')
    else:
        print(f'No res fix needed in {f}')
print('Done')