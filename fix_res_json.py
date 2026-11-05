import os, re

pages_dir = 'apps/web/src/pages/admin'

# Files that use navigate (so keep import)
uses_navigate = {
    'AdminTenantsPage.tsx': True,
    'AdminSubscriptionsPage.tsx': True,  # navigate(`/admin/subscriptions/${sub.id}`)
}

for f in sorted(os.listdir(pages_dir)):
    if not f.endswith('.tsx'): continue
    path = os.path.join(pages_dir, f)
    content = open(path).read()
    original = content
    
    # Fix await res.json -> await res.json()
    content = content.replace('const data = await res.json;', 'const data = await res.json();')
    
    # Remove unused navigate import where not used
    if f not in uses_navigate:
        content = content.replace('import { useNavigate } from "react-router-dom";\n', '')
    
    # Remove unused React import in AdminSettingsPage
    if f == 'AdminSettingsPage.tsx':
        content = content.replace('import React, { useEffect, useState } from "react";', 'import { useEffect, useState } from "react";')
    
    if content != original:
        open(path, 'w').write(content)
        print(f'Fixed {f}')
    else:
        print(f'No changes: {f}')
print('Done')