import os, re

pages_dir = 'E:/rest/apps/web/src/pages/admin'
files = [f for f in os.listdir(pages_dir) if f.endswith('.tsx')]

for f in files:
    path = os.path.join(pages_dir, f)
    content = open(path).read()
    original = content
    
    # Remove unused React import (we use new JSX transform)
    content = content.replace('import React, { useEffect, useState } from "react";', 'import { useEffect, useState } from "react";')
    content = content.replace('import React from "react";\n', '')
    
    if content != original:
        open(path, 'w').write(content)
        print(f'Fixed {f}')

print('Done')