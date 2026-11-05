import os, re

pages_dir = 'apps/web/src/pages/admin'

# Files that actually USE navigate in JSX (onClick handlers)
uses_navigate_in_jsx = {
    'AdminTenantsPage.tsx': True,
    'AdminSubscriptionsPage.tsx': True,
}

for f in sorted(os.listdir(pages_dir)):
    if not f.endswith('.tsx'): continue
    path = os.path.join(pages_dir, f)
    content = open(path).read()
    original = content
    
    # 1. If navigate is NOT used in JSX, remove the navigate declaration
    if f not in uses_navigate_in_jsx:
        content = content.replace('  const navigate = useNavigate();\n', '')
    
    # 2. Remove unused setPage/setPageSize declarations (they're declared but setters never called)
    # Keep page and pageSize state since they're used in URL construction
    content = content.replace('  const [page, setPage] = React.useState(1);\n', '  const [page] = React.useState(1);\n')
    content = content.replace('  const [pageSize, setPageSize] = React.useState(25);\n', '  const [pageSize] = React.useState(25);\n')
    
    # 3. Remove unused React import in AdminSettingsPage
    if f == 'AdminSettingsPage.tsx':
        content = content.replace('import React, { useEffect, useState } from "react";', 'import { useEffect, useState } from "react";')
    
    if content != original:
        open(path, 'w').write(content)
        print(f'Fixed {f}')
    else:
        print(f'No changes: {f}')
print('Done')