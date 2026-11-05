import os, re

path = 'apps/web/src/pages/admin/AdminSettingsPage.tsx'
content = open(path).read()
matches = re.findall(r'margin:\s*\d+\s+\d+\s+\d+\s+\d+', content)
print('Unquoted margins found:', matches)
content = re.sub(r'margin:\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)', r'margin: "\1 \2 \3 \4px"', content)
open(path, 'w').write(content)
print('Fixed')