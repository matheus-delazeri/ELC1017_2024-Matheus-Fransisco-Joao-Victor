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

class ThreeRoutersTopo(Topo):

    def build(self, **_opts):
        # Add routers
        r1 = self.addSwitch('s1')
        r2 = self.addSwitch('s2')
        r3 = self.addSwitch('s3')

        # Add hosts
        host1 = self.addHost('h1', ip='10.1.1.1/24', defaultRoute='via 10.1.1.254')
        host2 = self.addHost('h2', ip='10.2.2.1/24', defaultRoute='via 10.2.2.254')

        # Link r1 and r2 on a unique subnet
        self.addLink(r1, r2, 
                     intfName1='s1-eth0', params1={'ip': '10.0.1.1/24'},
                     intfName2='s2-eth0', params2={'ip': '10.0.1.2/24'})

        # Link r2 and r3 on another unique subnet
        self.addLink(r2, r3, 
                     intfName1='s2-eth1', params1={'ip': '10.0.2.1/24'},
                     intfName2='s3-eth0', params2={'ip': '10.0.2.2/24'})

        # Link host1 to r1
        self.addLink(host1, r1, 
                     intfName1='h1-eth0', params1={'ip': '10.1.1.1/24'},
                     intfName2='s1-eth1', params2={'ip': '10.1.1.254/24'})

        # Link host2 to r3
        self.addLink(host2, r3, 
                     intfName1='h2-eth0', params1={'ip': '10.2.2.1/24'},
                     intfName2='s3-eth1', params2={'ip': '10.2.2.254/24'})

    def __str__(self):
        return """
        3 routers connecting two hosts

            h1 -- s1 -- s2 -- s3 -- h2
        """

class TwoPathsTopo(Topo):
   
    def build(self, **_opts):
        # Add routers
        s0 = self.addSwitch('s0')
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')
        s3 = self.addSwitch('s3')
        s4 = self.addSwitch('s4')

        # Add hosts
        host1 = self.addHost('h1', ip='10.1.1.1/24', defaultRoute='via 10.1.1.254')
        host2 = self.addHost('h2', ip='10.2.2.1/24', defaultRoute='via 10.2.2.254')

        # Links to r0
        self.addLink(host1, s0, 
                     intfName1='h1-eth0', params1={'ip': '10.1.1.1/24'},
                     intfName2='s0-eth0', params2={'ip': '10.1.1.254/24'})

        self.addLink(s0, s1, 
                     intfName1='s0-eth1', params1={'ip': '10.0.1.1/24'},
                     intfName2='s1-eth0', params2={'ip': '10.0.1.2/24'})

        self.addLink(s0, s3, 
                     intfName1='s0-eth2', params1={'ip': '10.0.2.1/24'},
                     intfName2='s3-eth0', params2={'ip': '10.0.2.2/24'})
        
        # Links r1 and r2
        self.addLink(s1, s2, 
                     intfName1='s1-eth1', params1={'ip': '10.0.3.1/24'},
                     intfName2='s2-eth0', params2={'ip': '10.0.3.2/24'})

        # Links to r4
        self.addLink(s2, s4, 
                     intfName1='s2-eth1', params1={'ip': '10.0.4.1/24'},
                     intfName2='s4-eth0', params2={'ip': '10.0.4.2/24'})

        self.addLink(s3, s4, 
                     intfName1='s3-eth1', params1={'ip': '10.0.5.1/24'},
                     intfName2='s4-eth1', params2={'ip': '10.0.5.2/24'})

        self.addLink(host2, s4, 
                     intfName1='h2-eth0', params1={'ip': '10.2.2.1/24'},
                     intfName2='s4-eth2', params2={'ip': '10.2.2.254/24'})
    def __str__(self):
        return  """
        One host connected to others with two different paths

                  |-- s1 --- s2 --|  
            h1 -- s0              s4 -- h2
                  |------ s3 -----| 
        """

class MeshTopo(Topo):

    def build(self, **_opts):
        # Create switches for each host
        switches = []
        for i in range(1, 5):
            switch = self.addSwitch('s{}'.format(i))
            switches.append(switch)

            # Create hosts and link each to its switch
            host = self.addHost('h{}'.format(i), ip='10.{}.{}.1/24'.format(i, i), defaultRoute='via 10.{}.{}.254'.format(i, i))
            self.addLink(host, switch,
                         intfName1='h{}-eth0'.format(i), params1={'ip': '10.{}.{}.1/24'.format(i, i)},
                         intfName2='s{}-eth0'.format(i), params2={'ip': '10.{}.{}.254/24'.format(i, i)})

        # Fully connect switches
        subnet_counter = 1
        for i, sw1 in enumerate(switches):
            for j, sw2 in enumerate(switches):
                if j > i:  # Avoid duplicate connections
                    self.addLink(sw1, sw2,
                                 intfName1='s{}-eth{}'.format(i+1, subnet_counter), params1={'ip': '10.5.{}.{}/24'.format(subnet_counter, i)},
                                 intfName2='s{}-eth{}'.format(j+1, subnet_counter), params2={'ip': '10.5.{}.{}/24'.format(subnet_counter, j)})
                    subnet_counter += 1

    def __str__(self):
        return """
        A fully connected mesh topology with four hosts

              h1      h2      h3      h4
               |       |       |       |
              s1 ---- s2 ---- s3 ---- s4
               | ----- x ----- x ----- |
                       | ----- |
                           x
        """

def _get_info(nodes, net):
    "Helper function to gather interface and neighbor information."
    route_info = {}
    for node in nodes:
        interfaces = node.intfList()
        neighbors = []
        for intf in interfaces:
            # Find the link connected to this interface
            for link in net.links:
                # Check if the link has one of the node interfaces
                if intf.name == link.intf2.name or intf.name == link.intf1.name:
                    neighbor = link.intf1 if link.intf2 == intf.name else link.intf1
                    # Identify the neighbor based on the other interface in the link
                    neighbors.append({
                        'network': neighbor.IP(),
                        'mask': neighbor.prefixLen,
                        'next_hop': '0.0.0.0',
                        'iface': intf.name,
                        'cost': 0
                    })

        route_info[node.name] = neighbors

    return route_info

def configure_initial_table(net):
    # Combine host and switch info
    hosts_info = _get_info(net.hosts, net)
    switches_info = _get_info(net.switches, net)
    route_info = {**hosts_info, **switches_info}  # Use dictionary unpacking alternative

    "Outputs routing configurations for each host and writes to a file."
    for host_name, config in route_info.items():
        if not os.path.exists('./tmp'):
            os.makedirs('./tmp')

        config_file = "./tmp/{}.json".format(host_name)
        with open(config_file, 'w') as f:
            json.dump(config, f)

def run(topo):
    "Run Mininet with the chosen topology"
    net = Mininet(topo=topo, controller=None)
    for _, v in net.nameToNode.items():
        for itf in v.intfList():
            v.cmd('ethtool -K '+itf.name+' tx off rx off')
    net.start()

    configure_initial_table(net)
    
    CLI(net)
    net.stop()

def main():
    parser = argparse.ArgumentParser(description="Run a Mininet topology")
    parser.add_argument("--topo", type=str, choices=['Basic', 'Mesh', 'ThreeRouters', "TwoPaths"], default='Basic',
                        help="Choose the topology to run (default: Basic). Options: Basic, Mesh, ThreeRouters, TwoPaths.")
    args = parser.parse_args()

    topo_classes = {
        'Basic': BasicTopo,
        'TwoPaths': TwoPathsTopo,
        'ThreeRouters': ThreeRoutersTopo,
        'Mesh': MeshTopo
    }

    topo_class = topo_classes.get(args.topo)
    topo = topo_class()
    info("*** Starting topology: {}\n".format(args.topo))
    info(str(topo))
    run(topo)

if __name__ == '__main__':
    setLogLevel('info')
    main()

