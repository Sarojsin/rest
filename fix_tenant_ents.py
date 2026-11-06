import os

path = 'E:/rest/apps/web/src/pages/admin/AdminTenantEntitlementsPage.tsx'
content = open(path).read()

# Fix line 201: change '              );' to '              }'
content = content.replace('              );\n            )}', '              }\n            )}')

open(path, 'w').write(content)
print('Fixed AdminTenantEntitlementsPage.tsx')