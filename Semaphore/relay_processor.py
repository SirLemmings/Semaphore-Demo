from process import Process
import config as cfg
import communications as cm
import broadcasts as bc
import peers as pr
import ast


class RelayProcessor:
    def __init__(self, epoch):
        self.seen_bc = set()
        self.epoch = epoch

    def handle_relay(
        self, alias: int, broadcast: str,
    ):
        """
        Stores the data associated with a valid relay
        
        Parameters:
            relay (str): The valid relay to cache
            alias (int): The alias of the node that generated the broadcast within the relay
        """
        if self.epoch >= cfg.activation_epoch:
            if not bc.check_broadcast_validity(broadcast):
                print("broadcast invalid")
                return
            # SHOULD ALSO CHECK FOR 'MALFEASANCE'
        else:
            if not bc.verify_message_sig:
                return
        
        if broadcast not in self.seen_bc:
            self.seen_bc.add(broadcast)
            msg=bc.split_broadcast(broadcast)['message']
            if cfg.SHOW_RELAYS and msg != "test" and alias != cfg.ALIAS:
                print(f"{alias}: {msg}")
            cm.gossip_msg(f"relay|{broadcast}", {alias})

    # def request_seen_bc(self, alias):
    #     """send peer request for all seen broadcasts"""
    #     Process(
    #         1,
    #         RelayProcessor.format_seen_bc_response,
    #         self.conclude_seen_bc,
    #         "seen_bc_request",
    #         self.epoch,
    #         True,
    #         specific_peers=[alias],
    #     )

    # def fulfill_seen_bc_request(self, alias, request_id):
    #     """send seen broadcasts to peers"""
    #     cm.send_peer_message(alias, f"query_fulfillment|{request_id}|{self.seen_bc}")

    # @staticmethod
    # def format_seen_bc_response(query, response):
    #     """format string to set"""
    #     received_seen_bc = ast.literal_eval(response)
    #     if type(received_seen_bc) is set:
    #         return received_seen_bc

    # def conclude_seen_bc(self, process):
    #     """incorporate info from broadcast request"""
    #     received_bc = process.cached_responses[0]
    #     for broadcast in received_bc:
    #         bc_data = bc.split_broadcast(broadcast)
    #         chain_commit = bc_data["chain_commit"]
    #         if (
    #             not bc.check_broadcast_validity(broadcast)
    #             or cfg.epoch_chain_commit[self.epoch] != chain_commit
    #         ):
    #             print("broadcast invalid1")
    #             received_bc.remove(broadcast)
    #             pr.remove_peer(process.specific_peers[0])

    #     self.seen_bc = self.seen_bc.union(received_bc)
