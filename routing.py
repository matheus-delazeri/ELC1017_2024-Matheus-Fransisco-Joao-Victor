import json
from os import walk
import time
import threading
import argparse
from pprint import pprint
from scapy.all import *

# Global variables for the routing and forwarding tables
routing_table = {}  # {destination: {next_hop IP: distance}}
forwarding_table = {}  # {destination IP: next hop IP}
local_interfaces = {}  # {local_interface: IP address}

def initialize_routing():
    "Initialize routing and forwarding tables from configuration."
    global routing_table, forwarding_table, local_interfaces

    # Add the local interfaces to the routing table
    ifaces: NetworkInterfaceDict = conf.ifaces
    iface: NetworkInterface
    for iface_name, iface in ifaces.items():
        local_interfaces[iface_name] = iface.ip
        routing_table[iface.ip] = {iface_name: 0}  # Local interface has distance 0
        forwarding_table[iface.ip] = iface_name

    print("Routing table initialized:")
    pprint(routing_table)
    print("Forwarding table initialized:")
    pprint(forwarding_table)

def advertise_routes():
    "Periodically send routing table updates to neighbors using split horizon with poison reverse."
    while True:
        for iface, iface_ip in local_interfaces.items():
            for dest, paths in routing_table.items():
                min_distance = min(paths.values())

                # Apply split horizon with poison reverse
                for path_iface, distance in paths.items():
                    if path_iface == iface:
                        dest_info = f"{dest},{16}"  # Poison reverse with infinite distance
                    else:
                        dest_info = f"{dest},{min_distance}"
                    pkt = Ether(dst="ff:ff:ff:ff:ff:ff") / IP(src=iface_ip, dst="255.255.255.255") / Raw(load=dest_info)

                    try:
                        sendp(pkt, iface=iface, verbose=0)
                    except Exception as e:
                        print(f"Error sending packet on {iface}: {e}")

        time.sleep(5)

def update_routing_table(dest_ip, distance, recv_iface):
    "Update routing and forwarding tables if a shorter path is found."
    updated = False
    new_distance = distance + 1  # Increase distance by 1 for hop count
    current_paths = routing_table.get(dest_ip, {})

    # Apply split horizon: avoid creating loops by ignoring routes from the same interface
    if recv_iface in current_paths and current_paths[recv_iface] <= new_distance:
        return False

    # Update routing table if a shorter path is found or a new destination
    if dest_ip not in routing_table or new_distance < min(current_paths.values()):
        routing_table[dest_ip] = {recv_iface: new_distance}
        forwarding_table[dest_ip] = recv_iface

        updated = True
        print(f"Routing table updated for {dest_ip}:")
        pprint(routing_table)
        print(f"Forwarding table updated:")
        pprint(forwarding_table)
        print("\n")

    return updated

def handle_route_advertisement(pkt):
    "Handle incoming route advertisements and update routing table."
    if IP in pkt and Raw in pkt:
        data = pkt[Raw].load.decode()
        dest_ip, distance = data.split(",")
        distance = int(distance)

        update_routing_table(dest_ip, distance, pkt.sniffed_on)

def forward_packet(pkt):
    "Forward packet based on forwarding table and vector-distance algorithm."
    if IP in pkt:
        dest_ip = pkt[IP].dst
        if dest_ip in local_interfaces.values(): 
            return

        route = routing_table.get(dest_ip)

        if route:
            # Find the interface to send the packet via
            out_iface = forwarding_table.get(dest_ip)
            if out_iface:
                #pkt[Ether].dst = None  # Clear destination MAC address for re-resolution

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

# Main function
def main():
    initialize_routing()

    # Start the routing advertisement thread
    threading.Thread(target=advertise_routes, daemon=True).start()

    # Sniff for route advertisements and data packets
    sniff(iface=list(local_interfaces.keys()), filter='ip', prn=lambda pkt: handle_route_advertisement(pkt) if pkt[IP].dst == '255.255.255.255' else forward_packet(pkt))

if __name__ == '__main__':
    main()

