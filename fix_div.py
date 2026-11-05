# Remove extra closing div at line 157 (14 spaces) that doesn't match any open div
path = 'apps/web/src/pages/admin/AdminSettingsPage.tsx'
lines = open(path).readlines()
# Line 157 is index 156 (0-indexed)
# Check what's at line 157
print(f"Line 157: {repr(lines[156])}")
print(f"Line 158: {repr(lines[157])}")
print(f"Line 159: {repr(lines[158])}")
# Remove line 157 (index 156) - the extra </div> at 14 spaces
del lines[156]
open(path, 'w').writelines(lines)
print("Removed line 157")