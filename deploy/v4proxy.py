"""Local IPv4-only HTTPS CONNECT proxy — a workaround for machines where IPv6 to
api.machines.dev connects but fails TLS, so flyctl's Go client gets EOF and never
falls back to IPv4.

Run in one terminal:
    python deploy/v4proxy.py

Then in another terminal (cmd.exe):
    set HTTPS_PROXY=http://127.0.0.1:18080
    fly deploy

Nothing is installed or changed on the system; Ctrl+C ends it.
"""
import socket
import sys
import threading

LISTEN = ("127.0.0.1", 18080)


def pipe(src, dst):
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
    except OSError:
        pass
    finally:
        for s in (src, dst):
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


def handle(client):
    try:
        req = b""
        while b"\r\n\r\n" not in req:
            chunk = client.recv(4096)
            if not chunk:
                return
            req += chunk
        method, target, _ = req.split(b"\r\n")[0].decode().split(" ", 2)
        if method != "CONNECT":
            client.sendall(b"HTTP/1.1 405 Method Not Allowed\r\n\r\n")
            return
        host, port = target.rsplit(":", 1)
        addr = socket.getaddrinfo(host, int(port), socket.AF_INET, socket.SOCK_STREAM)[0][4]
        upstream = socket.create_connection(addr, timeout=30)
        upstream.settimeout(None)
        client.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        print(f"CONNECT {host}:{port} -> {addr[0]}", flush=True)
        threading.Thread(target=pipe, args=(client, upstream), daemon=True).start()
        pipe(upstream, client)
    except Exception as exc:  # noqa: BLE001 — report and drop the one connection
        print("ERR", exc, file=sys.stderr, flush=True)
        try:
            client.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
        except OSError:
            pass
    finally:
        try:
            client.close()
        except OSError:
            pass


def main():
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(LISTEN)
    srv.listen(64)
    print(f"v4proxy listening on http://{LISTEN[0]}:{LISTEN[1]}  (Ctrl+C to stop)", flush=True)
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=handle, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    main()
