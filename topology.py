import argparse
import json
import os
from mininet.topo import Topo
from mininet.net import Link, Mininet
from mininet.node import Node
from mininet.log import setLogLevel, info
from mininet.cli import CLI

class BasicTopo(Topo):
    "A router connecting two hosts"
    def build(self, **_opts):
        router = self.addHost('r', ip=None)
        host1 = self.addHost('h1', ip=None, defaultRoute='via 10.1.1.254')
        host2 = self.addHost('h2', ip=None, defaultRoute='via 10.2.2.254')

        # Links with correct IP assignments for each side
        self.addLink(host1, router, 
                     intfName1='h1-eth0', params1={'ip':'10.1.1.1/24'},
                     intfName2='r-eth1', params2={'ip':'10.1.1.254/24'})
        self.addLink(host2, router, 
                     intfName1='h2-eth0', params1={'ip':'10.2.2.1/24'},
                     intfName2='r-eth2', params2={'ip':'10.2.2.254/24'})

class ExampleTopo(Topo):
    "Two routers connecting two hosts"
    def build(self, **_opts):
        r1 = self.addHost('r1', ip='10.0.0.1')
        r2 = self.addHost('r2', ip='10.0.0.2')
        host1 = self.addHost('h1', ip='10.1.1.1/24', defaultRoute='via 10.1.1.254')
        host2 = self.addHost('h2', ip='10.2.2.1/24', defaultRoute='via 10.2.2.254')

        self.addLink(r1, r2, 
                     intfName1='r1-eth0', params1={'ip': '10.0.0.1/24'},
                     intfName2='r2-eth0', params2={'ip': '10.0.0.2/24'})
 
        # Links each host to it's router
        self.addLink(host1, r1, 
                     intfName1='h1-eth0', params1={'ip':'10.1.1.1/24'},
                     intfName2='r1-eth1', params2={'ip':'10.1.1.254/24'})
        self.addLink(host2, r2, 
                     intfName1='h2-eth0', params1={'ip':'10.2.2.1/24'},
                     intfName2='r2-eth1', params2={'ip':'10.2.2.254/24'})



class StarTopo(Topo):
    "A simple star topology with a central router connecting three hosts"
    def build(self, **_opts):
        central_router = self.addHost('r', ip=None)

        for i in range(1, 4):
            host = self.addHost(f'h{i}', ip=f'10.{i}.{i}.1/24', defaultRoute=f'via 10.{i}.{i}.254')
            # Link each host to the router with a unique subnet per host
            self.addLink(host, central_router,
                         intfName1=f'h{i}-eth0', params1={'ip': f'10.{i}.{i}.1/24'},
                         intfName2=f'r-eth{i}', params2={'ip': f'10.{i}.{i}.254/24'})

class MeshTopo(Topo):
    "A fully connected mesh topology with four hosts"
    def build(self, **_opts):
        hosts = []
        # Create 4 hosts with unique IP addresses
        for i in range(1, 5):
            host = self.addHost(f'h{i}', ip=f'10.{i}.{i}.1/24', defaultRoute=f'via 10.{i}.{i}.254')
            hosts.append(host)
        
        # Fully connect all hosts with unique subnets for each pair link
        subnet_counter = 1
        for i, host1 in enumerate(hosts):
            for j, host2 in enumerate(hosts):
                if j > i:  # To avoid duplicate connections
                    self.addLink(host1, host2, 
                                 intfName1=f'h{i+1}-eth{subnet_counter}', params1={'ip': f'10.{i}.{i}.1/24'},
                                 intfName2=f'h{j+1}-eth{subnet_counter}', params2={'ip': f'10.{i}.{j}.254/24'})
                    subnet_counter += 1

class BarTopo(Topo):
    "A linear (bar) topology with five hosts connected in a chain"
    def build(self, **_opts):
        previous_host = None
        # Loop to create 5 hosts
        for i in range(1, 6):
            host = self.addHost(f'h{i}', ip=f'10.0.{i}.1/24', defaultRoute=f'via 10.0.{i-1}.254' if i > 1 else None)
            if previous_host:
                # Each link has unique IPs for the host pair to ensure IP connectivity
                self.addLink(previous_host, host,
                             intfName2=f'h{i}-eth0', params2={'ip': f'10.0.{i}.1/24'},
                             intfName1=f'h{i-1}-eth1', params1={'ip': f'10.0.{i-1}.254/24'})
            previous_host = host

class RingTopo(Topo):
    "A ring topology with five hosts"
    def build(self, **_opts):
        hosts = []
        for i in range(1, 6):
            host = self.addHost(f'h{i}', ip=f'10.0.{i}.1/24', defaultRoute=f'via 10.0.{i}.254')
            hosts.append(host)
        
        # Connect each host in a ring configuration with distinct IPs for each link
        for i in range(len(hosts)):
            next_host = hosts[(i + 1) % len(hosts)]
            self.addLink(hosts[i], next_host,
                         intfName1=f'h{i}-eth0', params1={'ip': f'10.0.{i+1}.1/24'},
                         intfName2=f'h{i}-eth1', params2={'ip': f'10.0.{i+1}.254/24'})

def _get_info(nodes, net: Mininet):
    "Helper function to gather interface and neighbor information."
    route_info = {}
    for node in nodes:
        interfaces = node.intfList()
        neighbors = []
        for intf in interfaces:
            # Find the link connected to this interface
            link: Link
            for link in net.links:
                # Check if the link has one of the node interfaces
                if intf.name == link.intf2.name or intf.name == link.intf1.name:
                    neighbor = link.intf1 if link.intf2 == intf.name else link.intf1
                    # Identify the neighbor based on the other interface in the link
                    neighbors.append({
                        'network': neighbor.IP(),
                        'mask': neighbor.prefixLen,
                        'next_hop': None,
                        'iface': intf.name,
                        'cost': 0
                    })

        route_info[node.name] = neighbors

    return route_info

def configure_initial_table(net):
    route_info = _get_info(net.hosts, net)
    "Outputs routing configurations for each host and writes to a file."
    for host_name, config in route_info.items():
        if not os.path.exists('./tmp'):
            os.makedirs('./tmp')

        config_file = f"./tmp/{host_name}.json"
        with open(config_file, 'w') as f:
            json.dump(config, f)

def run(topo_class):
    "Run Mininet with the chosen topology"
    net = Mininet(topo=topo_class(), controller=None)
    for _, v in net.nameToNode.items():
        for itf in v.intfList():
            v.cmd('ethtool -K '+itf.name+' tx off rx off')
    net.start()

    configure_initial_table(net)
    
    CLI(net)
    net.stop()

def main():
    parser = argparse.ArgumentParser(description="Run a Mininet topology")
    parser.add_argument("--topo", type=str, choices=['Basic', 'Star', 'Mesh', 'Bar', 'Ring', 'Example'], default='Basic',
                        help="Choose the topology to run (default: Basic). Options: Basic, Star, Mesh, Bar, Ring.")
    args = parser.parse_args()

    topo_classes = {
        'Basic': BasicTopo,
        'Example': ExampleTopo,
        'Star': StarTopo,
        'Mesh': MeshTopo,
        'Bar': BarTopo,
        'Ring': RingTopo
    }

    topo_class = topo_classes.get(args.topo)
    info(f"*** Starting topology: {args.topo}\n")
    run(topo_class)

if __name__ == '__main__':
    setLogLevel('info')
    main()

