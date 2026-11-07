import sys

# Fix App.tsx - add missing admin routes
file_path = r'e:\rest\apps\web\src\App.tsx'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add admin routes before the catch-all route
old_text = '<Route path=\"*\" element={<Navigate to=\"/\" replace />} />'
new_text = '''<Route path="/admin/tenants/create" element={<AdminTenantCreatePage />} />
  <Route path="/admin/diagnostics" element={<AdminDiagnosticsPage />} />
  <Route path="/admin/plans/:planId/versions" element={<AdminPlanVersionsPage />} />

  <Route path="*" element={<Navigate to="/" replace />} />'''

new_content = content.replace(old_text, new_text)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print('App.tsx fixed')