import subprocess, time

# Start uvicorn in background
proc = subprocess.Popen(
    ['python', '-m', 'uvicorn', 'app.main:app', '--reload', '--host', '0.0.0.0', '--port', '8000'],
    cwd='E:\\rest\\backend',
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

time.sleep(3)

# Check if process is still running
if proc.poll() is None:
    print("Backend started successfully PID:", proc.pid)
else:
    print("Backend failed to start")
    stdout = proc.stdout.read().decode(errors='replace')
    stderr = proc.stderr.read().decode(errors='replace')
    print("STDOUT:", stdout[-500:])
    print("STDERR:", stderr[-500:])