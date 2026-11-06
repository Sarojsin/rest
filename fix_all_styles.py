import os, re

pages_dir = 'E:/rest/apps/web/src/pages/admin'
files = os.listdir(pages_dir)

for f in files:
    if not f.endswith('.tsx'):
        continue
    path = os.path.join(pages_dir, f)
    content = open(path).read()
    original = content
    
    # Fix unquoted margin/padding shorthand values in style objects
    # Pattern: margin: N N N N (all numbers, no quotes)
    def fix_margin4(m):
        vals = [m.group(1), m.group(2), m.group(3), m.group(4)]
        fixed = []
        for v in vals:
            if v == '0':
                fixed.append('0')
            else:
                fixed.append(v + 'px')
        return f'margin: "{fixed[0]} {fixed[1]} {fixed[2]} {fixed[3]}"'
    
    content = re.sub(r'margin:\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)', fix_margin4, content)
    
    # Pattern: margin: N N (two values)
    def fix_margin2(m):
        vals = [m.group(1), m.group(2)]
        fixed = []
        for v in vals:
            if v == '0':
                fixed.append('0')
            else:
                fixed.append(v + 'px')
        return f'margin: "{fixed[0]} {fixed[1]}"'
    
    content = re.sub(r'margin:\s*(\d+)\s+(\d+)', fix_margin2, content)
    
    # Pattern: margin: N (single value)
    def fix_margin1(m):
        v = m.group(1)
        if v == '0':
            return 'margin: "0"'
        return f'margin: "{v}px"'
    
    content = re.sub(r'margin:\s*(\d+)\s', fix_margin1, content)
    
    # Same for padding
    def fix_padding4(m):
        vals = [m.group(1), m.group(2), m.group(3), m.group(4)]
        fixed = []
        for v in vals:
            if v == '0':
                fixed.append('0')
            else:
                fixed.append(v + 'px')
        return f'padding: "{fixed[0]} {fixed[1]} {fixed[2]} {fixed[3]}"'
    
    content = re.sub(r'padding:\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)', fix_padding4, content)
    
    def fix_padding2(m):
        vals = [m.group(1), m.group(2)]
        fixed = []
        for v in vals:
            if v == '0':
                fixed.append('0')
            else:
                fixed.append(v + 'px')
        return f'padding: "{fixed[0]} {fixed[1]}"'
    
    content = re.sub(r'padding:\s*(\d+)\s+(\d+)', fix_padding2, content)
    
    def fix_padding1(m):
        v = m.group(1)
        if v == '0':
            return 'padding: "0"'
        return f'padding: "{v}px"'
    
    content = re.sub(r'padding:\s*(\d+)\s', fix_padding1, content)
    
    if content != original:
        open(path, 'w').write(content)
        print(f'Fixed {f}')
    else:
        print(f'No changes: {f}')

print('Done')