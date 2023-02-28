import socket
import config as cfg
import broadcasts as bc
import peers as pr
import communications as cm
import time


def generate_config_msg(alias: int, peer_ip: str, peer_port: int):
    """
    Generates a message used in connecting to a new peer containing alias and both's IP and port
    
    Parameters:
        alias (int): A valid alias of the the peer to message
        peer_ip (str): The IP address of the peer node's device
        peer_port (int): The device port used by the peer for Semaphore communication

    Returns: Signature plus message (node IP and port, peer alias, IP, and port)
    """
    msg = f"|{cfg.IP}|{cfg.PORT}|{alias}|{peer_ip}|{peer_port}|{1 if cfg.activated else 0}"
    msg = bc.sign_msg(msg)
    return msg


def request_connection(peer_alias: int, peer_ip: str, peer_port: int):
    """
    Requests another node to accept an outgoing connection
    
    Parameters:
        alias (int): A valid alias of the the peer to connect to
        peer_ip (str): The IP address of the peer node's device
        peer_port (int): The device port used by the peer for Semaphore communication
    """
    if peer_alias == cfg.ALIAS:
        return
    listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listening_socket.connect((peer_ip, int(peer_port)))
    listening_socket.setblocking(False)

    pr.add_new_peer(peer_alias)
    peer = cfg.peers[peer_alias]
    peer.update_listening(listening_socket)

    connection_message = generate_config_msg(peer_alias, peer_ip, peer_port)
    connection_message = bc.format_message(connection_message)
    peer_socket = cfg.peers[peer_alias].listening
    peer_socket.send(connection_message)

    print(f"requested connection to {peer_alias}, ({peer_ip}, {peer_port})")


def handle_connection_request():
    """
    Accepts an incomming connection and send a return outgoing connection if necessary
    
    Rejects the message if invalid (empty of unverified) or if they provide the wrong alias
    """
    peer_socket, peer_address = cfg.server_socket.accept()
    connection_message = cm.receive_message(peer_socket)
    if connection_message is False:
        print("msg_false")
        peer_socket.shutdown(socket.SHUT_RDWR)
        peer_socket.close()
        return
    if not bc.verify_message_sig(
        connection_message
    ):  # FIX SINGATURE CHECK ###I am looking at this later and dont know if its been fixed or not TODO figure this out
        print("not_verify")
        peer_socket.shutdown(socket.SHUT_RDWR)
        peer_socket.close()
        return

    connection_data = connection_message.split("|")
    peer_alias = int(connection_data[0][-cfg.ALIAS_LEN :])
    peer_ip = connection_data[1]
    peer_port = connection_data[2]
    request_alias = int(connection_data[3])
    peer_activated = bool(int(connection_data[-1]))
    if request_alias != cfg.ALIAS:
        print("wrong_peer")
        print(request_alias)
        print(cfg.ALIAS)
        peer_socket.shutdown(socket.SHUT_RDWR)
        peer_socket.close()
        return

    # TODO make it so that the peers wont add each other a bunch of times sometimes
    pr.add_new_peer(peer_alias)
    if cfg.peers[peer_alias].speaking is None:
        cfg.peers[peer_alias].update_speaking(peer_socket)
    if cfg.peers[peer_alias].listening is None:
        time.sleep(0.1)
        request_connection(peer_alias, peer_ip, peer_port)
    if peer_activated:
        pr.activate_peer(peer_alias)

    print(f"accepted connection from {peer_alias}, {peer_address}")

def signal_activation():
    for peer in cfg.peers:
        cm.send_peer_message(peer,'activate')

def signal_deactivation():
    for peer in cfg.peers:
        cm.send_peer_message(peer,'deactivate')