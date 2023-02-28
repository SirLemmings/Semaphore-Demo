from argparse import ArgumentParser
from node import Node
import connections as cn
import timing as tm
import json
import config as cfg
from typing import List

def get_peers(alias: int, edges: List[List[int]], size: int) -> List[int]:
    """
    Finds a node's peers (connections) given a list of edges or network size.

    If edges is None instead of a list of tuples, the function will
    fully connect the node to the entire network.

    Parameters:
        alias (int): The index of the node.
        edges (list[list[int]]): A list of edges in the network.
        size (int): The size of the network.

    Returns: A list of the node's peers in the network.
    """
    if edges is None:
        return [i for i in range(size) if i != alias]
    peers = []
    for edge in edges:
        if alias in edge:
            peer = edge[1] if alias == edge[0] else edge[0]
            peers.append(peer)
    return peers

class DemoNode:
    """
    A wrapper class for a node in a demo network.

    This class is designed to be instantiated as a subprocess within
    an arbitrarily defined demo network via a single command.

    Attributes:
        ALIAS: The alias of the node
        PORTS: The mapping of alias to listening port in the network
        peers: The peers that the Node will connect to
        Node: The wrapped node object
    """
    def __init__(self, alias: int, ports: List[int], peers: List[int]):
        self.ALIAS = alias
        self.PORTS = ports
        self.peers = peers
        self.Node = Node(alias, ports[alias])
        print("Node " + str(alias) + " created")
        if alias == 0:
            print("activating")
            self.activate()
        else:
            self.connect_peers()
            tm.initialize()

    def activate(self) -> None:
        """
        Activates the node and bootstraps a new network.
        """
        cfg.initialized = True
        cfg.committed_epoch = cfg.current_epoch
        cfg.synced = True
        cfg.activated = True
        cfg.enforce_chain = True
        cfg.activation_epoch = cfg.current_epoch
        epochs = [
            epoch
            for epoch in range(
                cfg.current_epoch
                + cfg.EPOCH_TIME * (cfg.FORWARD_SLACK_EPOCHS),
                cfg.current_epoch
                + cfg.EPOCH_TIME
                * (cfg.FORWARD_SLACK_EPOCHS + cfg.DELAY - 1),
                cfg.EPOCH_TIME,
            )
        ]
        delays = [i for i in range(cfg.DELAY - 1, 0, -1)]
        cfg.chain_commit_offset = {e: d for e, d in zip(epochs, delays)}
        cn.signal_activation()

    def connect_peers(self) -> None:
        """
        Connects the node to listed peers.

        This will only connect to peers that have already been initialized.
        This operates under the assumption that nodes are initialized in
        numerical order of their aliases.
        """
        for peer in self.peers:
            if peer < self.ALIAS: # only connect "backwards" to peers that have already been initialized
                peer_port = self.PORTS[peer]
                cn.request_connection(peer, str(cfg.IP), peer_port)


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("alias", type=int)
    args = parser.parse_args()
    alias = args.alias
    with open("demo_network_structure.json") as f:
        demo_network = json.load(f)
    ports = demo_network["ports"]
    peers = get_peers(alias, demo_network["edges"], demo_network["size"])
    print("launching demo node")
    b = DemoNode(alias, ports, peers)

if __name__ == "__main__":
    main()