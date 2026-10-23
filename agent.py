import socket
import time
import sys
import psutil
from packet import encode_packet
from config import SERVER_IP, PORT, SEND_INTERVAL, CPU_LIMIT

SERVER = (SERVER_IP, PORT)

node_id = sys.argv[1] if len(sys.argv) > 1 else "node-1"

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

seq = 0

psutil.cpu_percent(interval=None)
last_net = psutil.net_io_counters()
last_t = time.time()

while True:
    time.sleep(SEND_INTERVAL)
    cpu = psutil.cpu_percent(interval=None)    
    mem = psutil.virtual_memory().percent
    procs = len(psutil.pids())

    now = time.time()
    net_now = psutil.net_io_counters()
    moved = (net_now.bytes_sent + net_now.bytes_recv) - (last_net.bytes_sent + last_net.bytes_recv)
    net = round(moved / (now - last_t) / 1e6, 2)  # MB/s
    last_net, last_t = net_now, now

    critical = cpu > CPU_LIMIT
    seq += 1

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