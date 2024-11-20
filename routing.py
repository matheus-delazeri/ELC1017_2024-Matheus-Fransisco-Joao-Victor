import json
import argparse
import ipaddress
from scapy.all import *
import threading
import time

# Define custom routing protocol (Layer 4 above IP) TRP (Table Routing Protocol)
class TRP(Packet):
    name = "TableRoutingProtocol"
    fields_desc = [
        IPField("network", "0.0.0.0"),     # Destination IP address
        IntField("mask", 0),               # IP mask
        IPField("next_hop", "0.0.0.0"),    # Next hop IP address
        IntField("cost", 0),               # Distance metric
        ShortField("protocol_id", 42)      # Protocol identifier for routing
    ]

    def show(self, *args, **kwargs):
        "Pretty print the TableProtocol packet information."
        print("TRP Packet Information:")
        print("  - Network IP: {}/{}".format(self.network, self.mask))
        print("  - Cost: {}".format(self.cost))
        print("  - Next hop: {}".format(self.next_hop))
        print("  - Protocol ID: {}".format(self.protocol_id))
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
                    print("Error sending packet on {}: {}".format(iface_name, e))

        time.sleep(2)

def handle_route_share(pkt):
    is_new_entry = True
    updated = False

    network = _get_network(pkt[TRP].network, pkt[TRP].mask)
    for route in routing_table:
        if route['network'] == network.network_address:
            is_new_entry = False
            # Handle update for best route
            if pkt[TRP].cost + 1 < route['cost']:
                old_route = route.copy()
                route['iface'] = pkt.sniffed_on
                route['next_hop'] = pkt[IP].src
                route['cost'] = pkt[TRP].cost + 1
                updated = True
                show_new_best_route(old_route, route)

    if is_new_entry:
        routing_table.append({
            'network': network.network_address,
            'mask': pkt[TRP].mask,
            'cost': pkt[TRP].cost + 1,  # Add one to cost for each iteration
            'next_hop': pkt[IP].src,
            'iface': pkt.sniffed_on
        })
        updated = True

    if updated:
        show_routing_table()

def show_interfaces():
    print('\n[Interfaces] Entries: {}\n-------------------------'.format(len(local_interfaces)))
    print("{:<12} {:<12}".format('Name', 'IP'))
    for iface_name, iface_ip in local_interfaces.items():
        print("{:<12} {:<12}".format(iface_name, iface_ip))
    print('-------------------------\n')

def show_routing_table():
    print('\n[Routing Table] Entries: {}\n-------------------------'.format(len(routing_table)))
    print("{:<12} {:<12} {:<10} {:<5}".format('Network', 'Next hop', 'Interface', 'Cost'))
    for route in routing_table:
        print("{:<12} {:<12} {:<10} {:<5}".format(
            '{}/{}'.format(route['network'], route['mask']),
            str(route['next_hop']), route['iface'], route['cost']))
    print('-------------------------\n')

def show_new_best_route(old_route, new_route):
    print('\n[New route] {}/{}\n-------------------------'.format(old_route['network'], old_route['mask']))
    print("      {:<12} {:<10} {:<5}".format('Next hop', 'Interface', 'Cost'))
    print("[OLD] {:<12} {:<10} {:<5}".format(str(old_route['next_hop']), old_route['iface'], old_route['cost']))
    print("[NEW] {:<12} {:<10} {:<5}".format(str(new_route['next_hop']), new_route['iface'], new_route['cost']))
    print('-------------------------\n')

def _get_network(ip, mask):
    return ipaddress.ip_network("{}/{}".format(ip, mask), False)

def init(node):
    global routing_table, local_interfaces
    "Load configuration from the node config file."
    try:
        with open('tmp/{}.json'.format(node), 'r') as f:
            routing_table = json.load(f)

        for route in routing_table:
            # Make sure that the network IP is being used
            network = _get_network(route['network'], route['mask'])
            route['network'] = network.network_address

        ifaces = [route['iface'] for route in routing_table]
        for iface_name, iface in conf.ifaces.items():
            if iface_name in ifaces:
                local_interfaces[iface_name] = iface.ip

        return routing_table
    except FileNotFoundError:
        print("ERROR: Configuration file for host {} not found in tmp/.".format(node))
        return None

def forward_packet(pkt):
    "Forward packets based on forwarding table using vector-distance algorithm."
    if IP in pkt and TRP not in pkt:  # Ensure the packet is an IP packet and not a routing packet
        dst = ipaddress.ip_address(pkt[IP].dst)
        for route in routing_table:
            route_network = _get_network(route['network'], route['mask'])
            if dst in route_network and route['iface'] != pkt.sniffed_on:
                # Modify MAC address instead of setting to None
                pkt[Ether].dst = None
                sendp(pkt, iface=route['iface'], verbose=0)
                break  # Stop after first match to prevent multiple forwarding
    else:
        print("Non-IP packet or routing packet received, ignoring.")

def main():
    parser = argparse.ArgumentParser(description="Router Configuration")
    parser.add_argument("--node", type=str, required=True, help="Name of the node to be used as router. e.g: r1")
    args = parser.parse_args()

    if not init(args.node):
        return

    show_interfaces()
    show_routing_table()

    # Start the routing share thread
    threading.Thread(target=share_routes, daemon=True).start()

    # Sniff for routing share and data packets
    sniff(iface=list(local_interfaces.keys()), filter="ip", prn=lambda pkt: handle_route_share(pkt) if TRP in pkt else forward_packet(pkt))


if __name__ == '__main__':
    main()

