import os, errno, ast
import config as cfg
import communications as cm
import connections as cn
import consensus as cs
import peers as pr
import clock as cl
import timing as tm
import broadcasts as bc
import blocks as bk
import syncing as sy
import fork_choice as fc
import state as st

import time
import json
from alias_management import get_pubkey
from query import Query
from threading import Thread


class Node:
    def __init__(self, alias: int, port: int):
        cfg.ALIAS = int(alias)
        cfg.PORT = int(port)

        with open("encrypted&secure_document.txt", "r") as f:
            key_dict = eval(f.read())
        cfg.pk = get_pubkey(cfg.ALIAS)
        cfg.sk = key_dict[cfg.pk]

        cfg.server_socket.bind((cfg.IP, cfg.PORT))
        cfg.server_socket.listen()

        folder = str(cfg.ALIAS)
        if os.path.isdir(folder):
            block_files = [
                file
                for file in os.listdir(f"{folder}/blocks")
                if file.endswith(".json")
            ]
            numbers = [int(name.split(".")[0]) for name in block_files]
            block_files = [file for _, file in sorted(zip(numbers, block_files))]
            for file in block_files:
                name = os.path.join(f"./{folder}/blocks", f"{file}")
                with open(name, "rb") as f:
                    block = bk.Block(init_dict=json.load(f))
                    cs.load_block_data(block, calc_state=False)

            state_files = [
                file
                for file in os.listdir(f"{folder}/states")
                if file.endswith(".json")
            ]
            numbers = [int(name.split(".")[0]) for name in state_files]
            state_files = [file for _, file in sorted(zip(numbers, state_files))]
            for file in state_files:
                name = os.path.join(f"./{folder}/states", f"{file}")
                with open(name, "rb") as f:
                    state = st.State(init_dict=json.load(f))
                    cfg.historic_states[state.epoch] = state
                    cfg.historic_epochs.append(state.epoch)
            st.initialize_buckets()
            cfg.current_state = cfg.historic_states[cfg.historic_epochs[-1]]
        else:
            os.mkdir(f"{cfg.ALIAS}")
            os.mkdir(f"{cfg.ALIAS}/blocks")
            os.mkdir(f"{cfg.ALIAS}/states")

        t_socket = Thread(
            target=cm.socket_events, args=[self.interpret_message], name="socket"
        )
        t_command = Thread(target=self.commands, name="commands")
        t_timing = Thread(target=tm.time_events, name="timing")
        t_socket.start()
        t_command.start()
        t_timing.start()

    def interpret_message(self, msg: str, alias: int):
        """
        Determines the type of a received message and calls the right function to process it

        Parameters: 
            msg (str): The received message to be interpreted
            alias (int): The alias of the sender
        """
        # Use | as delimeter for message information
        data = msg.split("|")
        # TODO HANDLE SPLITTING MORE ELEGANTLY
        # NOT SURE WHAT CASE THIS IS HANDLING - OSCAR
        if len(data) > 2:
            if data[-2][-1] == "\\":
                join = data[-2] + data[-1]
                data[-2:] = [join]
        msg_type = data[0]

        if msg_type == "chat":
            print(data[1])

        elif msg_type == "activate":
            pr.activate_peer(alias)

        elif msg_type == "deactivate":
            pr.deactivate_peer(alias)

        elif msg_type == "time_request":
            query_id = data[1]
            if len(query_id) > 40:
                print("~7")
                return
            cl.fulfill_time_request(alias, query_id)

        elif msg_type == "vote_request" and cfg.activated:
            query_id = data[1]
            if len(query_id) > 40:
                print("~8")
                return
            try:
                epoch = int(data[2])
            except:
                print("~9")
                return
            self.execute_process(epoch, "vote", "vote_request", alias, query_id)

        elif msg_type == "query_fulfillment":
            query_id = data[1]
            if len(query_id) > 40:
                print("~10")
                return

            response = data[2]
            if query_id not in Query.open_queries:
                print(f"{query_id} not in open queries")
                self.peer_manager.remove_peer(alias)
                return
            Query.open_queries[query_id].process_query_response(response, alias)

        elif msg_type == "bc_request" and cfg.activated:
            query_id = data[1]
            if len(query_id) > 40:
                print("~11")
                return
            data = ast.literal_eval(data[2])
            epoch, bcid = data
            try:
                epoch = int(epoch)
            except:
                print("~12")
                return
            self.execute_process(epoch, "vote", "bc_request", alias, query_id, bcid)

        elif msg_type == "history_request":
            query_id = data[1]
            if len(query_id) > 40:
                print("~13")
                return
            chain_tip_info = ast.literal_eval(data[2])
            chain_tip_epoch, chain_tip_hash = chain_tip_info
            try:
                chain_tip_epoch = int(chain_tip_epoch)
            except:
                print("~14")
                return
            if len(chain_tip_hash) != 64:
                print(chain_tip_hash)
                print(len(chain_tip_hash))
                print("~15")
                return
            Thread(
                target=sy.fulfill_history_request,
                args=[alias, query_id, chain_tip_epoch, chain_tip_hash],
                name="history_fulfill",
            ).start()

        elif msg_type == "fork_request":
            query_id = data[1]
            if len(query_id) > 40:
                print("~16")
                return
            alt_past = ast.literal_eval(data[2])
            fc.fulfill_fork_request(alias, query_id, alt_past)

        elif msg_type == "relay":
            broadcast = data[1]
            try:
                bc_data = bc.split_broadcast(broadcast)
            except:
                return
            chain_commit = bc_data["chain_commit"]
            if len(chain_commit) != cfg.CHAIN_COMMIT_LEN:
                print("~17")
                return
            if cfg.synced:
                if chain_commit in cfg.epoch_chain_commit.inverse.keys():
                    epoch = cfg.epoch_chain_commit.inverse[chain_commit]
                    self.execute_process(epoch, "relay", "relay", alias, broadcast)

                elif cfg.activated:
                    print("~broadcast not in valid epoch")
                    if chain_commit not in fc.reorg_processes and cfg.activated:
                        fc.reorg_processes.add(chain_commit)
                        fc.request_fork_history(alias)

    def execute_process(self, epoch: int, state: str, process: str, alias: int, *args):
        if epoch in cfg.epoch_processes.keys():
            epoch_processor = cfg.epoch_processes[epoch]
            epoch_processor.execute_new_process(state, process, alias, *args)

    def commands(self):
        """
        Input manual commands when not in testing mode.
        
        The following are the supported commands and arguments.
        
        - connect: Attempts to connect with a specified peer node
        Arguments:
            peer_alias (int): valid alias of a peer to connect to
            peer_ip (str or int): IP address of the peer node
            peer_port (int): device port that the peer is using
        
        - see_peers: Displays all peers connected to the node

        - chat: sends a direct message to a peer with a specified alias
        Arguments:
            alias (int): valid alias of a connected peer
            message (str): message to send to peer. Character limit is ??

        - remove: Removes a connected peer with a specified alias
        Arguments:
            alias (int): valid alias of the peer to be removed

        - exit: Halts the node's processes and exits the Semaphore network

        - epoch: Displays the Semaphore network's current epoch according to the node's time

        - time_synch: Displays the node's network time after sampling peers

        - broadcast: Broadcasts a message to the Semaphore network
        Arguments:
            msg (str): The message to be broadcast. Character limit is ??

        - badcast (str): Creates and distributes an invalid broadcast to test the network
        """
        while True:
            try:
                command = input()
                if command == "connect":
                    alias = int(input("peer_alias: "))
                    ip = input("peer_ip: ")
                    if "." not in ip:
                        ip = str(cfg.IP)
                    port = input("peer_port: ")
                    try:
                        cn.request_connection(alias, ip, port)
                    except IOError as e:
                        print(e)
                        print("refused")
                        if e.errno == errno.ECONNREFUSED:
                            pass
                elif command == "fc":
                    for i in range(10):
                        if i not in cfg.peers and i != cfg.ALIAS:
                            try:
                                cn.request_connection(i, str(cfg.IP), f"{i}" * 4)
                            except:
                                pass
                elif command == "see_peers":
                    print(cfg.peers.keys())
                elif command == "see_peers_active":
                    print(cfg.peers_activated.keys())

                elif command == "see_peer_sockets":
                    print(cfg.peer_manager.peers)
                    print(cfg.peer_manager.all_listening)
                    print(cfg.peer_manager.all_speaking)

                elif command == "chat":
                    alias = int(input("alias: "))
                    msg = input("message: ")
                    cm.send_peer_chat(alias, msg)

                elif command == "remove":
                    alias = int(input("alias: "))
                    pr.remove_peer(alias)

                elif command == "exit":
                    os._exit(0)

                elif command == "time_sync":
                    cl.initiate_time_update()
                    time.sleep(0.1)
                    print(cl.network_time())
                elif command == "init":
                    if not cfg.initialized:
                        tm.initialize()
                    else:
                        print("already initialiazed")

                elif command == "activate":
                    if not cfg.initialized:
                        cfg.initialized = True
                        cfg.committed_epoch = cfg.current_epoch
                        cfg.synced = True
                        cfg.activated = True
                        cfg.enforce_chain = True
                        cfg.activation_epoch = cfg.current_epoch
                        cfg.bootstrapping = True
                        cfg.bootstrapped_epoch = (
                            cfg.current_epoch
                            + cfg.FORWARD_SLACK_EPOCHS * cfg.EPOCH_TIME
                            + 5
                        )
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
                    else:
                        print("already activated")
                elif command == "deactivate":
                    if cfg.activated:
                        tm.deactivate()
                    else:
                        print("not activated")

                elif command == "get_alt":
                    alias = int(input("peer_alias: "))
                    fc.request_fork_history(alias)
                elif (
                    command == "badcast"
                ):  # SEND MESSAGE WITH BAD SIGNATURE FOR TESTING
                    timestamp = self.time_event_manager.epoch
                    broadcast = self.broadcast_manager.generate_broadcast(
                        f"{self.ALIAS}badcast", timestamp, ""
                    )
                    if self.ALIAS != 0:
                        broadcast = broadcast[:128] + "0000000000" + broadcast[138:]
                    else:
                        broadcast = broadcast[:128] + "0000000001" + broadcast[138:]
                    timestamps = self.time_event_manager.timestamps
                    if timestamp in timestamps:
                        self.relay_manager.unconf_bc[timestamps[timestamp]].add(
                            broadcast
                        )
                    self.peer_manager.gossip_msg(f"relay|{broadcast}")
                elif command == "update_nym":
                    nym = input("nym: ")
                    broadcast = bc.update_nym(nym)
                    cfg.epoch_processes[cfg.current_epoch].processor.handle_relay(
                        cfg.ALIAS, broadcast
                    )
                elif cfg.ENABLE_MANUAL_BC and len(command) >= 1:
                    try:
                        cm.originate_broadcast(command)
                    except:
                        pass

            except EOFError:
                os._exit(0)


if __name__ == "__main__":
    b = Node(input("alias: "), input("port: "))

