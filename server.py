import socket
import time
from packet import decode_packet
from config import BIND_IP, PORT, HEARTBEAT_TIMEOUT, CPU_LIMIT, MEM_LIMIT

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()

HOST = BIND_IP

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((HOST, PORT))
sock.settimeout(1)             

nodes = {}                     
print(f"Monitoring server listening on port {PORT}")
print(f"Agents on other laptops should use server IP: {get_local_ip()}")

print(f"Monitoring server listening on port {PORT}...")

try:
    while True:
        try:
            data, addr = sock.recvfrom(4096)
            now = time.time()

            p = decode_packet(data)
            if p is None:
                print("Ignored malformed packet")
                continue
            node = p["node_id"]

            # new node, or update an existing one
            info = nodes.setdefault(node, {"last_seq": 0, "status": "NEW"})

            if info["status"] == "DOWN":
                print(f"[{time.strftime('%H:%M:%S')}] {node} is UP again")

            # detect lost packets using sequence numbers
            expected = info["last_seq"] + 1
            if info["last_seq"] and p["seq"] > expected:
                print(f"[{time.strftime('%H:%M:%S')}] {node} WARNING "
                      f"missing packet(s): expected seq {expected}, got {p['seq']}")

            info["last_seq"] = p["seq"]
            info["last_seen"] = now
            info["status"] = "UP"

            # check thresholds
            latency_ms = (now - p["timestamp"]) * 1000
            if p["cpu"] > CPU_LIMIT or p["mem"] > MEM_LIMIT:
                print(f"[{time.strftime('%H:%M:%S')}] {node} ALERT "
                      f"cpu={p['cpu']}% mem={p['mem']}% latency={latency_ms:.1f} ms")
            else:
                print(f"[{time.strftime('%H:%M:%S')}] {node} OK "
                      f"cpu={p['cpu']}% mem={p['mem']}%")

        except socket.timeout:
            pass

        now = time.time()
        for node, info in nodes.items():
            if info["status"] == "UP" and now - info["last_seen"] > HEARTBEAT_TIMEOUT:
                info["status"] = "DOWN"
                print(f"[{time.strftime('%H:%M:%S')}] {node} DOWN "
                      f"(no packet for {HEARTBEAT_TIMEOUT}s)")

except KeyboardInterrupt:
    print("\nServer stopped.")