import socket

print("Checking SMTP server availability:")
print()

# Check local SMTP servers
for port in [1025, 25, 587, 465]:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex(('localhost', port))
        if result == 0:
            print(f"  localhost:{port} - OPEN")
        else:
            print(f"  localhost:{port} - CLOSED")
        sock.close()
    except Exception as e:
        print(f"  localhost:{port} - ERROR: {e}")

print()

# Check remote SMTP servers
for host, port in [('smtp.gmail.com', 587), ('smtp.gmail.com', 465)]:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        if result == 0:
            print(f"  {host}:{port} - OPEN")
        else:
            print(f"  {host}:{port} - CLOSED")
        sock.close()
    except Exception as e:
        print(f"  {host}:{port} - ERROR: {e}")