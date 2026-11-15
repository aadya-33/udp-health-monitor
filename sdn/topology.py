from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel


def configure_qos(net):
    """Create HTB QoS queues on all switch interfaces: Queue 0 (2 Mbps), Queue 1 (8 Mbps)."""
    for sw in net.switches:
        for intf in sw.intfList():
            if intf.name == 'lo':
                continue
            sw.cmd(
                f'ovs-vsctl -- set Port {intf.name} qos=@newqos '
                f'-- --id=@newqos create QoS type=linux-htb other-config:max-rate=10000000 queues=0=@q0,1=@q1 '
                f'-- --id=@q0 create Queue other-config:min-rate=1000000 other-config:max-rate=2000000 '
                f'-- --id=@q1 create Queue other-config:min-rate=8000000 other-config:max-rate=10000000'
            )


def build():
    net = Mininet(controller=None, switch=OVSSwitch, link=TCLink, autoSetMacs=True)

    net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6653)

    s1 = net.addSwitch('s1', protocols='OpenFlow13')
    s2 = net.addSwitch('s2', protocols='OpenFlow13')
    s3 = net.addSwitch('s3', protocols='OpenFlow13')

    h1 = net.addHost('h1', ip='10.0.0.1/24')   # monitoring server
    h2 = net.addHost('h2', ip='10.0.0.2/24')   # agents
    h3 = net.addHost('h3', ip='10.0.0.3/24')
    h4 = net.addHost('h4', ip='10.0.0.4/24')

    net.addLink(h1, s1, bw=10)
    net.addLink(h2, s2, bw=10)
    net.addLink(h3, s3, bw=10)
    net.addLink(h4, s3, bw=10)

    # Triangle between switches (redundant path)
    net.addLink(s1, s2, bw=10)
    net.addLink(s2, s3, bw=10)
    net.addLink(s1, s3, bw=10)

    return net


if __name__ == '__main__':
    setLogLevel('info')
    net = build()
    net.start()
    configure_qos(net)
    CLI(net)
    net.stop()