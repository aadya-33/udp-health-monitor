import json

FIELDS = ["node_id", "seq", "timestamp", "cpu", "mem", "procs", "net", "critical"]


def encode_packet(node_id, seq, timestamp, cpu, mem, procs, net, critical):
    """Build the bytes an agent sends over UDP."""
    packet = {
        "node_id": node_id,
        "seq": seq,
        "timestamp": timestamp,
        "cpu": cpu,
        "mem": mem,
        "procs": procs,
        "net": net,
        "critical": critical,
    }
    return json.dumps(packet).encode()


def decode_packet(data):
    try:
        packet = json.loads(data.decode())
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(packet, dict) or any(f not in packet for f in FIELDS):
        return None
    return packet