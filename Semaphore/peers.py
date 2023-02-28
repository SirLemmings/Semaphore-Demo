import socket
import config as cfg

TEST = False


class Peer:
    """
    a class used to ensure that all data relating to a peer is updated in sync
    
    Attributes:
        alias (int): A valid alias of a connected peer node
        parent (PeerManager): The peer manager object that tracks this peer
        speaking (Socket): The output socket used to speak to the peer
        listening (Socket): The input socket used to listen to the peer
    """

    def __init__(
        self, alias, speaking=None, listening=None,
    ):
        """
        Creates a peer from a parent PeerManager and valid alias,
        and optionally from pre-existing speaking and listening sockets
        
        Parameters: 
            parent (PeerManager): The peer manager object that tracks this peer
            alias (int): A valid alias of a connected peer node
            speaking (socket): The output socket used to speak to the peer
            listening (socket): The input socket used to listen to the peer
        """
        self.alias = alias
        self.speaking = speaking
        self.listening = listening

    def __del__(self):
        """
        Ensures that all data associated with peer is deleted if peer is removed
        
        Shuts down any active speaking or listening sockets used to communicate with the peer
        """
        if self.listening in cfg.all_listening:
            del cfg.all_listening[self.listening]
            try:
                self.listening.shutdown(socket.SHUT_RDWR)
                self.listening.close()
            except OSError as e: 
                pass#THIS SHOULD CHECK THAT ITS OSERROR 107
                # if e!= e.ENOTCONN:
                #     print(e)
        if self.speaking in cfg.all_speaking:
            del cfg.all_speaking[self.speaking]
            try:
                self.speaking.shutdown(socket.SHUT_RDWR)
                self.speaking.close()
            except OSError as e: 
                pass#THIS SHOULD CHECK THAT ITS OSERROR 107
                # if e!= e.ENOTCONN:
                #     print(e)

    def update_listening(self, listening):
        """
        Updates all data on listening socket in sync
        """
        self.listening = listening
        cfg.all_listening[listening] = self.alias

    def update_speaking(self, speaking):
        """
        Updates all data on speaking socket in sync
        """
        self.speaking = speaking
        cfg.all_speaking[speaking] = self.alias






def add_new_peer(alias: int):
    """
    Creates a new peer object from a valid, unconnected peer
    
    If PeerManager.peers does not have an alias: peer object pair, it creates one
    
    Parameters:
        alias (int): A valid alias of the peer to add
    """
    if alias not in cfg.peers:
        cfg.peers[alias] = Peer(alias)


def remove_peer(
    alias=None, socket=None
):  # THIS SHOULD CLOSE SOCKETS TOO ### WIAT, DOESNT THE PEER CLASS CLOSE THE SOCKET????
    """
    Removes peer from PeerManager.peers based on alias or socket
    
    Parameters:
        alias (int): A valid alias of the peer to remove
        socket (socket): A socket used to communicate with the peer to be removed
    """
    if socket is not None:
        if socket in cfg.all_speaking:
            alias = cfg.all_speaking[socket]
        if socket in cfg.all_listening:
            alias = cfg.all_listening[socket]
    if alias in cfg.peers:
        print(f'~removing peer {alias}')
        del cfg.peers[alias]
    if alias in cfg.peers_activated:
        del cfg.peers_activated[alias]


def full_connection(alias: int) -> bool:
    """
    Verifies if the node has an incoming and outgoing connection to the peer
    
    Parameters:
        alias (int): A valid alias of the peer to remove

    Returns:
        True if the peer alias is recognized and shares a listening and a speaking socket with the node,
        False otherwise
    """
    if alias not in cfg.peers:
        print(f"{alias} not in peer list!")
        return False
    if cfg.peers[alias].listening is None or cfg.peers[alias].speaking is None:
        return False
    return True


def fully_connected_peer_aliases():
    """
    Retreives the set of all peers with a full connection
    
    Returns: A set object with every fully connected peer tracked by the peer manager
    """
    peers = cfg.peers.copy()
    return {alias for alias in peers if cfg.full_connection(alias)}

def activate_peer(alias:int):
    if alias in cfg.peers.keys():
        cfg.peers_activated[alias]=cfg.peers[alias]

def deactivate_peer(alias:int):
    if alias in cfg.peers_activated:
        del cfg.peers_activated[alias]