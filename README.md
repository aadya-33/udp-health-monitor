# UDP Health Monitor with SDN

A distributed system health monitor written in Python. Agents on each node send CPU, memory, process and network stats over **UDP** to a central server, which raises alerts and detects node failures. The system runs on a **Mininet** network controlled by an **SDN controller (Ryu)**.

This is the SDN-Socket Programming (Jackfruit) mini project.

## How it works

- **Agent (`agent.py`)** samples CPU, memory, process count and network throughput every 2 seconds and sends them to the server as a JSON datagram. Each packet has a sequence number and timestamp.
- **Server (`server.py`)** listens on UDP port 9000 and keeps the state of every node:
  - **Alerts** when CPU is above 90% or memory is above 85%.
  - **Packet loss detection** from gaps in sequence numbers.
  - **Node failure detection**: a node is marked DOWN if no packet arrives for 6 seconds, and UP again when packets resume.
- **Packet format (`packet.py`)** encodes and validates the JSON packets. Malformed packets are ignored.
- **Settings (`config.py`)** holds the port, timing and alert thresholds.

## SDN architecture

```
 Application layer   UDP health monitor (agents + server)
                     controller apps (flow rules, prioritising, blocking, rerouting)
                              |  northbound API (REST)
 Control layer       Ryu SDN controller (global view, installs flow rules)
                              |  southbound API (OpenFlow 1.3)
 Data layer          Open vSwitch switches s1, s2, s3 + hosts h1-h4 (Mininet)
```

### Topology

```
        h1 (server)
          |
         s1
        /  \
      s2 -- s3
      |    /  \
     h2   h3  h4      (h2, h3, h4 run agents)
```

The three switches form a triangle, which gives a redundant path for rerouting and failure tests. Because of the loop, the controller uses an STP-enabled learning switch.

## Project structure

```
agent.py  server.py  packet.py  config.py   UDP socket application
requirements.txt                            Python dependencies for the app
sdn/
  topology.py                               Mininet topology (3 switches, 4 hosts)
  controller.py                             Ryu controller (OpenFlow 1.3, STP)
  tests/                                    test scripts for scenarios
results/                                    measurements and graphs
docs/                                       architecture diagram and report
```

## Requirements

- Ubuntu with **Mininet** and **Open vSwitch**
- Python 3.9 virtual environment for Ryu (Ryu does not build on very new Python versions)
- `psutil` for the agents

Installing Ryu in the venv:

```
pip install pbr wheel "setuptools==65.5.0"
pip install --no-build-isolation eventlet==0.30.2 ryu psutil
ryu-manager --version
```

## Running with Mininet and SDN

Use two terminals, both from the repo folder.

**Terminal 1: start the controller** (venv active):

```
ryu-manager sdn/controller.py
```

**Terminal 2: start the topology:**

```
sudo -E python3 sdn/topology.py
```

Wait 30-60 seconds for STP to converge, then check connectivity with `pingall`.

**Start the monitor.** Open a window for each host from the `mininet>` prompt:

```
mininet> xterm h1 h2 h3 h4
```

Then, inside the windows:

| Window | Command |
|--------|---------|
| h1 | `python3 server.py` |
| h2 | `python3 agent.py 10.0.0.1 h2` |
| h3 | `python3 agent.py 10.0.0.1 h3` |
| h4 | `python3 agent.py 10.0.0.1 h4` |

Each agent needs its own node ID. Use the Python that has `psutil` installed.

## Test scenarios

- **Normal operation:** all agents reporting, the server shows OK for each node.
- **Node failure:** stop an agent and confirm the server marks it DOWN after 6 seconds, then UP when restarted.
- **Link failure:** `link s1 s2 down` and check that traffic still reaches the server through the other path.
- **Packet loss / congestion:** add loss on a link or flood it with `iperf`, and compare the loss reported by the server (sequence gaps).
- **Traffic Prioritization (`sdn/controller.py` & `sdn/topology.py`):** Links are capped at `10 Mbps` with OVS HTB QoS queues:
  - **Queue 1 (8 Mbps guaranteed, `priority=100`):** Express queue for critical alerts matching `udp_dst=9000` and `ip_dscp=46`.
  - **Queue 0 (2 Mbps max, `priority=50` / default):** Standard queue for routine health telemetry and background traffic.
