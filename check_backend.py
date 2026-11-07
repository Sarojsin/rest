import subprocess

# Check if uvicorn process is running
result = subprocess.run(['tasklist', '/FI', 'IMAGE eq uvicorn.exe'], capture_output=True, text=True)
print("Tasklist result:")
if result.stdout:
    print(result.stdout[-300:])
else:
    print("  no output")

# Also check for any python processes
result2 = subprocess.run(['tasklist'], capture_output=True, text=True)
python_lines = [line for line in result2.stdout.split('\n') if 'python' in line.lower()]
if python_lines:
    print("\nPython processes:")
    for line in python_lines[-5:]:
        print("  ", line)
else:
    print("\n  no python processes found")