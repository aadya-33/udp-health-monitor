from ryu.app import simple_switch_stp_13
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, set_ev_cls
from ryu.lib.packet import packet, ethernet, ipv4, udp


class HealthMonitorController(simple_switch_stp_13.SimpleSwitch13):
    def __init__(self, *args, **kwargs):
        super(HealthMonitorController, self).__init__(*args, **kwargs)
        self.prioritized_hosts = set()

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # 1. Let SimpleSwitch13 + STP learn MACs and install base L2 forwarding first
        super(HealthMonitorController, self)._packet_in_handler(ev)

        msg = ev.msg
        datapath = msg.datapath
        parser = datapath.ofproto_parser

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if not eth:
            return

        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        udp_pkt = pkt.get_protocol(udp.udp)

        dpid = datapath.id
        out_port = self.mac_to_port.get(dpid, {}).get(eth.dst)

        # 2. Override base L2 flow with high-priority QoS flow once out_port is known
        if ip_pkt and udp_pkt and udp_pkt.dst_port == 9000 and out_port is not None:
            dscp = ip_pkt.tos >> 2
            if dscp == 46:  # DSCP EF (0xB8) -> Critical Health Alert -> Queue 1 (8-10 Mbps)
                if ip_pkt.src not in self.prioritized_hosts:
                    self.prioritized_hosts.add(ip_pkt.src)
                    self.logger.warning(
                        "[SDN-QoS] Prioritizing CRITICAL alert traffic from %s on s%s (Queue 1, Priority 100)",
                        ip_pkt.src, dpid
                    )
                match = parser.OFPMatch(
                    eth_type=0x0800,
                    ip_proto=17,
                    ipv4_src=ip_pkt.src,
                    udp_dst=9000,
                    ip_dscp=46
                )
                actions = [parser.OFPActionSetQueue(1), parser.OFPActionOutput(out_port)]
                self.add_flow(datapath, 100, match, actions, idle_timeout=15)
            else:  # Normal Health Telemetry -> Queue 0 (1-2 Mbps)
                match = parser.OFPMatch(
                    eth_type=0x0800,
                    ip_proto=17,
                    ipv4_src=ip_pkt.src,
                    udp_dst=9000
                )
                actions = [parser.OFPActionSetQueue(0), parser.OFPActionOutput(out_port)]
                self.add_flow(datapath, 50, match, actions, idle_timeout=15)