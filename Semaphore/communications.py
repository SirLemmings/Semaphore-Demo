import select
import config as cfg
import connections as cn
import broadcasts as bc
import peers as pr

import random
import sched
from threading import Thread
import time


s = sched.scheduler(time.time, time.sleep)


def receive_message(client_socket):
    """
    Returns string of message with header removed
    
    Receives a message from the specified listening socket and decodes it to a string
    
    Parameters;
        client_socket: The socket to receive the message from
    
    Returns:
        False if message is improperly formatted or the socket is invalid
        The message decoded from bytes to string, otherwise
    """
    MAX_BUF = 2000
    try:
        message_header = client_socket.recv(cfg.HEADER_LENGTH)
        if not len(message_header):
            return False
        message_length = int(message_header.decode("utf-8").strip())
        data = b""
        while message_length > 0:
            buffer = min(MAX_BUF, message_length)
            new = b""
            while len(new) < buffer:
                new += client_socket.recv(buffer - len(new))
            data += new
            message_length -= buffer

        data = data.decode("utf-8")
        return data
    except Exception as e:
        print(e)
        return False


def socket_events(interpret_msg_func):
    """
    Executes necessary functions when a speaking socket is notified by a peer
    
    The event loop runs continuously on its own thread. 
    """
    while True:
        read_sockets, _, exception_sockets = select.select(
            list(cfg.all_speaking) + [cfg.server_socket],
            [],
            list(cfg.all_speaking) + [cfg.server_socket],
        )
        for notified_socket in read_sockets:
            # handle new connection
            if notified_socket == cfg.server_socket:
                cn.handle_connection_request()
            else:
                # Receive message
                message = receive_message(notified_socket)
                # If False, client disconnected, cleanup
                if message is False:
                    pr.remove_peer(socket=notified_socket)
                    continue

                speaking_alias = cfg.all_speaking[notified_socket]
                interpret_msg_func(message, speaking_alias)

        # handle exceptions just in case
        for notified_socket in exception_sockets:
            print("some sort of error")
            pr.remove_peer(socket=notified_socket)


def send_peer_chat(alias, msg):
    """
    Sends a message that appears in a peer's terminal
    
    Parameters:
        alias (int): A valid alias of the peer to direct message
        msg (str): The message to be sent. Character limit is ??
    """
    if pr.full_connection(alias):
        msg = f"chat|{msg}"
        cfg.peers[alias].listening.send(bc.format_message(msg))


def send_peer_message(alias: int, message: str):
    """
    Sends a string message to a peer after validating a connection with them
    
    Parameters: 
        alias (int): A valid alias of a connected node to send the message to
        message (str): A message to send directly to the peer. Size limit is ?? characters
    """
    if pr.full_connection(alias):
        message = bc.format_message(message)
        peer_socket = cfg.peers[alias].listening
        try:
            peer_socket.send(message)
        except Exception as e:
            pr.remove_peer(alias)
            print(f"failed to send to {alias}")
            print(e)


def gossip_msg(msg: str, excluded=set()):
    """
        Sends a message to all peers, except those in the excluded set
        
        Parameters:
            msg (str): The message to be gossiped. Character limit is ??
            excluded (set): The set of all excluded nodes
        """

    if cfg.RANDOM_DELAY is False:
        for alias in cfg.peers.copy():
            if alias not in excluded:
                send_peer_message(alias, msg)

    else:
        for alias in cfg.peers.copy():
            if alias not in excluded:
                time = (random.random() * 2.2 + 3) * (cfg.ALIAS != 1)
                s.enter(
                    time, 0, send_peer_message, argument=[alias, msg],
                )
                Thread(target=s.run, name=f"gossip_{alias}").start()


def originate_broadcast(message: str, parent=""):
    """
        Creates a properly formatted broadcast, adds to seen broadcasts and relays to peers
        
        Parameters: 
            message (str): A message to broadcast out to the Semaphore network. Size limit is ?? characters
            parent (str): An optional ID of a parent broadcast
        """
    try:
        chain_com = cfg.epoch_chain_commit[
            cfg.current_epoch
        ] 
    except:
        print('uhh')
        return
    broadcast = bc.generate_broadcast(message, chain_com, parent)
    cfg.epoch_processes[cfg.current_epoch].processor.handle_relay(cfg.ALIAS, broadcast)

