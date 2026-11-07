import sys

# Fix AdminLayout.tsx - remove the hardcoded plan versions nav item
file_path = r'e:\rest\apps\web\src\pages\admin\AdminLayout.tsx'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Remove the hardcoded plan versions line
old_line = '{ to: "/plans/fe736ba2-bccd-44d5-ac0d-8fe98a787f94/versions", label: "Plan Versions", permission: "plan.view" },'
new_content = content.replace(old_line, '')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print('AdminLayout.tsx fixed')