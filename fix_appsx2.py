import sys

# Fix App.tsx - fix indentation of admin routes
file_path = r'e:\rest\apps\web\src\App.tsx'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the indentation - replace the malformed lines
old = '''        <Route path="/admin/tenants/create" element={<AdminTenantCreatePage />} />
  <Route path="/admin/diagnostics" element={<AdminDiagnosticsPage />} />
'''
new = '''  <Route path="/admin/tenants/create" element={<AdminTenantCreatePage />} />
  <Route path="/admin/diagnostics" element={<AdminDiagnosticsPage />} />
'''

content = content.replace(old, new)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('App.tsx indentation fixed')