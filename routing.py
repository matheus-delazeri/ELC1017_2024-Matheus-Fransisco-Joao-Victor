import json
import time
import threading
from pprint import pprint
from scapy.all import *

# Define custom routing protocol (Layer 4 above IP)
class TableProtocol(Packet):
    name = "TableProtocol"
    fields_desc = [
        IPField("origin", "0.0.0.0"),          # Origin IP address
        IPField("destination", "0.0.0.0"),     # Destination IP address
        IntField("distance", 0),               # Distance metric
        ShortField("protocol_id", 42)          # Protocol identifier for routing
    ]

    def show(self, *args, **kwargs):
        "Pretty print the TableProtocol packet information."
        print("TableProtocol Packet Information:")
        print(f"  - Destination IP: {self.destination}")
        print(f"  - Distance: {self.distance}")
        print(f"  - Protocol ID: {self.protocol_id}")

bind_layers(IP, TableProtocol, proto=143)

# Global tables for routing and forwarding
routing_table = {}  # {destination: {next_hop IP: distance}}
forwarding_table = {}  # {destination IP: next hop IP}
local_interfaces = {}  # {local_interface: IP address}

def initialize_routing():
    "Initialize routing and forwarding tables from configuration."
    global routing_table, forwarding_table, local_interfaces

    # Populate local interfaces into the routing table
    for iface_name, iface in conf.ifaces.items():
        if iface.ip:
            local_interfaces[iface_name] = iface.ip
            routing_table[iface.ip] = {iface_name: 0}  # Local interface has distance 0
            forwarding_table[iface.ip] = iface_name

    print("Routing table initialized:")
    pprint(routing_table)
    print("Forwarding table initialized:")
    pprint(forwarding_table)

def advertise_routes():
    "Periodically send routing table updates to neighbors with split horizon and poison reverse."
    while True:
        for iface, iface_ip in local_interfaces.items():
            for dest, paths in routing_table.items():
                min_distance = min(paths.values())

                # Apply split horizon with poison reverse
                for path_iface, distance in paths.items():
                    advertised_distance = 16 if path_iface == iface else min_distance  # Poison reverse for local path
                    pkt = Ether(dst="ff:ff:ff:ff:ff:ff") / IP(src=iface_ip, dst="255.255.255.255") / TableProtocol(destination=dest, distance=advertised_distance)

                    try:
                        sendp(pkt, iface=iface, verbose=0)
                    except Exception as e:
                        print(f"Error sending packet on {iface}: {e}")

        time.sleep(5)

def update_routing_table(dest_ip, distance, recv_iface):
    "Update routing and forwarding tables if a shorter path is discovered."
    updated = False
    new_distance = distance + 1  # Increment distance for each hop
    current_paths = routing_table.get(dest_ip, {})

    # Avoid loops by ignoring routes from the same interface with a shorter/equal distance
    if recv_iface in current_paths and current_paths[recv_iface] <= new_distance:
        return False

    # Update if it's a new destination or a shorter path
    if dest_ip not in routing_table or new_distance < min(current_paths.values()):
        routing_table[dest_ip] = {recv_iface: new_distance}
        forwarding_table[dest_ip] = recv_iface

        updated = True
        print(f"Routing table updated for {dest_ip}:")
        pprint(routing_table)
        print("Forwarding table updated:")
        pprint(forwarding_table)
        print("\n")

    return updated

def handle_route_advertisement(pkt):
    "Process incoming route advertisements and update the routing table."
    if TableProtocol in pkt:
        dest_ip = pkt[TableProtocol].destination
        distance = pkt[TableProtocol].distance
        recv_iface = pkt.sniffed_on

        update_routing_table(dest_ip, distance, recv_iface)

def forward_packet(pkt):
    "Forward packets based on forwarding table using vector-distance algorithm."
    if IP in pkt:
        dest_ip = pkt[IP].dst
        if dest_ip in local_interfaces.values():
            return  # Destination is a local interface

        route = routing_table.get(dest_ip)
        if route:
            out_iface = forwarding_table.get(dest_ip)
            if out_iface:
                pkt[IP].dst = None # Avoid infinite loop
                try:
                    sendp(pkt, iface=out_iface, verbose=0)
                    print(f"Packet forwarded via {out_iface} to destination {dest_ip}")
                except Exception as e:
                    print(f"Error forwarding packet: {e}")
            else:
                print(f"No valid interface found for destination {dest_ip}")
        else:
            print(f"No valid forwarding rule for destination {dest_ip}")
    else:
        print("Non-IP packet received, ignoring.")

def main():
    initialize_routing()

    # Start the routing advertisement thread
    threading.Thread(target=advertise_routes, daemon=True).start()

    # Sniff for routing advertisements and data packets
    sniff(iface=list(local_interfaces.keys()), filter="ip", prn=lambda pkt: handle_route_advertisement(pkt) if TableProtocol in pkt else forward_packet(pkt))

if __name__ == '__main__':
    main()

