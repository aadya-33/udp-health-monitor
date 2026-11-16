import socket
import time
import sys
import psutil
import random
from packet import encode_packet
from config import SERVER_IP, PORT, SEND_INTERVAL, CPU_LIMIT, MEM_LIMIT

# Server IP: from command line, otherwise ask the user
if len(sys.argv) > 1:
    server_ip = sys.argv[1]
else:
    server_ip = input(f"Enter server IP address [{SERVER_IP}]: ").strip() or SERVER_IP

if len(sys.argv) > 2:
    node_id = sys.argv[2]
else:
    node_id = input("Enter node ID: ").strip() or socket.gethostname()

stress_mode = (len(sys.argv) > 3 and sys.argv[3].lower() == "stress")

try:
    socket.inet_aton(server_ip)   # checks it looks like a valid IPv4 address
except OSError:
    print(f"'{server_ip}' is not a valid IP address.")
    sys.exit(1)
 
SERVER = (server_ip, PORT)
print(f"[{node_id}] sending to {server_ip}:{PORT}")

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

seq = 0

psutil.cpu_percent(interval=None)
last_net = psutil.net_io_counters()
last_t = time.time()

while True:
    time.sleep(SEND_INTERVAL)

    if stress_mode:
        # ~85% chance of breaching thresholds (90% CPU / 85% MEM), ~15% brief dip
        cpu = round(random.uniform(88.0, 99.5), 1)
        mem = round(random.uniform(83.0, 96.0), 1)
    else:
        cpu = psutil.cpu_percent(interval=None)    
        mem = psutil.virtual_memory().percent
    procs = len(psutil.pids())

    now = time.time()
    net_now = psutil.net_io_counters()
    moved = (net_now.bytes_sent + net_now.bytes_recv) - (last_net.bytes_sent + last_net.bytes_recv)
    net = round(moved / (now - last_t) / 1e6, 2)  # MB/s
    last_net, last_t = net_now, now

    critical = cpu > CPU_LIMIT or mem > MEM_LIMIT
    seq += 1
    # 0xB8 = DSCP 46 (Expedited Forwarding) for CRITICAL alerts; 0x00 = CS0 for normal
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, 0xB8 if critical else 0x00)

    data = encode_packet(
        node_id=node_id,
        seq=seq,
        timestamp=time.time(),
        cpu=cpu,
        mem=mem,
        procs=procs,
        net=net,
        critical=critical,
    )

    # send the packet (no connection needed with UDP)
    sock.sendto(data, SERVER)

    flag = " (CRITICAL)" if critical else ""
    print(f"[{node_id}] seq={seq} cpu={cpu}% mem={mem}% procs={procs} net={net}MB/s sent{flag}")