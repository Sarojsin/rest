import socket
for host in ["ass.platform.com", "localhost", "127.0.0.1", "192.168.1.5"]:
    try:
        ip = socket.gethostbyname(host)
        print(f"{host} resolves to: {ip}")
    except socket.gaierror as e:
        print(f"{host} does NOT resolve: {e}")
