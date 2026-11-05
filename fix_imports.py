import os

pages_dir = 'apps/web/src/pages/admin'
files = [f for f in os.listdir(pages_dir) if f.endswith('.tsx')]
for f in files:
    path = os.path.join(pages_dir, f)
    content = open(path).read()
    old_import = 'import { usePlatformAuth, useNavigate } from "react-router-dom";'
    new_import = 'import { useNavigate } from "react-router-dom";\nimport { usePlatformAuth } from "../../lib/platformAuth";'
    if old_import in content:
        content = content.replace(old_import, new_import)
        open(path, 'w').write(content)
        print(f'Fixed import in {f}')
    else:
        print(f'No import to fix in {f}')
print('Done')