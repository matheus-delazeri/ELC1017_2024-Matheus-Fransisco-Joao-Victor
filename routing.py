import json
import argparse
from scapy.all import *

# Define custom routing protocol (Layer 4 above IP) TRP (Table Routing Protocol)
class TRP(Packet):
    name = "TableRoutingProtocol"
    fields_desc = [
        IPField("network", "0.0.0.0"),     # Destination IP address
        IntField("mask", 0),               # IP mask
        IPField("next_hop", "0.0.0.0"),     # Next hop IP address
        IntField("cost", 0),               # Distance metric
        ShortField("protocol_id", 42)          # Protocol identifier for routing
    ]

    def show(self, *args, **kwargs):
        "Pretty print the TableProtocol packet information."
        print("TRP Packet Information:")
        print(f"  - Network IP: {self.network}/{self.mask}")
        print(f"  - Cost: {self.cost}")
        print(f"  - Next hop: {self.next_hop}")
        print(f"  - Protocol ID: {self.protocol_id}")
        print("\n")

bind_layers(IP, TRP, proto=143)

local_interfaces = {}
routing_table = []

def share_routes():
    "Periodically send routing table updates to neighbors"
    while True:
        for iface_name, iface_ip in local_interfaces.items():
            for route in routing_table:
                pkt = Ether(dst="ff:ff:ff:ff:ff:ff") / \
                IP(dst=iface_ip) / \
                TRP(network=route['network'], mask=int(route['mask']),
                    next_hop=route['next_hop'], 
                    cost=route['cost'])

                try:
                    sendp(pkt, iface=iface_name, verbose=0)
                except Exception as e:
                    print(f"Error sending packet on {iface_name}: {e}")

        time.sleep(5)

def handle_route_share(pkt):
    is_new_entry = True
    updated = False
    for route in routing_table:
        if route['network'] == pkt[TRP].network:
            # Handle update for best route
            is_new_entry = False

    if is_new_entry:
        routing_table.append({
            'network': pkt[TRP].network,
            'mask': pkt[TRP].mask,
            'cost': pkt[TRP].cost + 1, # Add one to cost for each iteration
            'next_hop': pkt[TRP].next_hop,
            'iface': pkt.sniffed_on
        })
        updated = True

    if updated:
        show_routing_table()

def show_routing_table():
    print(f'\n[Routing Table] Entries: {len(routing_table)}\n-------------------------')
    print("{:<12} {:<12} {:<10} {:<5}".format('Network','Next hop','Interface','Cost'))
    for route in routing_table:
        print("{:<12} {:<12} {:<10} {:<5}".format(f'{route['network']}/{route['mask']}', str(route['next_hop']), route['iface'], route['cost']))
    print('-------------------------\n')

def init(node):
    global routing_table, local_interfaces
    "Load configuration from the node config file."

    iface: NetworkInterface
    for iface_name, iface in conf.ifaces.items():
        if iface_name != 'lo':
            local_interfaces[iface_name] = iface.ip

    try:
        with open(f'tmp/{node}.json', 'r') as f:
            routing_table = json.load(f)

        return routing_table
    except FileNotFoundError:
        print(f"ERROR: Configuration file for host {node} not found int tmp/.")
        return None

def forward_packet(pkt):
    "Forward packets based on forwarding table using vector-distance algorithm."
    if IP in pkt:
        dst = pkt[IP].dst
        pkt.show()
        for route in routing_table:
            if route['network'] == dst and route['iface'] != pkt.sniffed_on:
                pkt[Ether].dst = None

                sendp(pkt, iface=route['iface'], verbose=0)
    else:
        print("Non-IP packet received, ignoring.")

def main():
    parser = argparse.ArgumentParser(description="Router Configuration")
    parser.add_argument("--node", type=str, required=True, help="Name of the node to be used as router. e.g: r1")
    args = parser.parse_args()

    if not init(args.node):
        return

    show_routing_table()

    # Start the routing share thread
    threading.Thread(target=share_routes, daemon=True).start()

    # Sniff for routing share and data packets
    sniff(iface=list(local_interfaces.keys()), filter="ip", prn=lambda pkt: handle_route_share(pkt) if TRP in pkt else forward_packet(pkt))


if __name__ == '__main__':
    main()

