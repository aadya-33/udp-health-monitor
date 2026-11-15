from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel


def build():
    net = Mininet(controller=None, switch=OVSSwitch, link=TCLink,
                  autoSetMacs=True)

    net.addController('c0', controller=RemoteController,
                      ip='127.0.0.1', port=6653)

    s1 = net.addSwitch('s1', protocols='OpenFlow13')
    s2 = net.addSwitch('s2', protocols='OpenFlow13')
    s3 = net.addSwitch('s3', protocols='OpenFlow13')

    h1 = net.addHost('h1', ip='10.0.0.1/24')   # monitoring server
    h2 = net.addHost('h2', ip='10.0.0.2/24')   # agents
    h3 = net.addHost('h3', ip='10.0.0.3/24')
    h4 = net.addHost('h4', ip='10.0.0.4/24')

    # hosts
    net.addLink(h1, s1)
    net.addLink(h2, s2)
    net.addLink(h3, s3)
    net.addLink(h4, s3)

    # triangle between switches (redundant path)
    net.addLink(s1, s2)
    net.addLink(s2, s3)
    net.addLink(s1, s3)

    return net


if __name__ == '__main__':
    setLogLevel('info')
    net = build()
    net.start()
    CLI(net)
    net.stop()