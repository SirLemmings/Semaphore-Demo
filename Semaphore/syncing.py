from process import Process
import config as cfg
import blocks as bk
import communications as cm
import consensus as cs
import ast


def request_history():
    chain_tip_epoch = cfg.epochs[-1]
    chain_tip_hash = cfg.hashes[chain_tip_epoch]
    for alias in cfg.peers_activated:
        Process(
            1,
            format_history_response,
            conclude_history_process,
            "history_request",
            (chain_tip_epoch, chain_tip_hash),
            True,
            specific_peers=[alias],
        )


def fulfill_history_request(alias, query_id, chain_tip_epoch, chain_tip_hash):
    """send block history to requesting peer"""
    # print("~fulfilling history")
    if not cfg.activated:
        print("~not activated. delayint fulfillment")
    if chain_tip_epoch not in cfg.epochs:
        print("~no block from epoch", chain_tip_epoch)
        cm.send_peer_message(alias, f"query_fulfillment|{query_id}|no_block")
        return

    if chain_tip_hash != cfg.hashes[chain_tip_epoch]:
        print("~block from alternate chain")
        cm.send_peer_message(alias, f"query_fulfillment|{query_id}|no_block")
        return

    index = cfg.epochs.index(chain_tip_epoch) + 1
    history_epochs = cfg.epochs[index:]
    history_blocks = [cfg.blocks[epoch].convert_to_dict() for epoch in history_epochs]
    cm.send_peer_message(alias, f"query_fulfillment|{query_id}|{history_blocks}")


def format_history_response(query, response):
    """format received string to list of dicts"""
    if response == "no_block":
        return response
    received_blocks = ast.literal_eval(response)
    if type(received_blocks) is not list:
        print('~18')
        raise Exception("blocks is not a list")
    for block in received_blocks:
        if type(block) is not dict:
            raise Exception("block is not a dict")
        if set(block.keys()) != {
            "block_index",
            "chain_commitment",
            "epoch_timestamp",
            "bc_root",
            "sig_root",
            "bc_body",
            "sig_body",
        }:
            print('~19')
            raise Exception("block keys are incorrect")
        int(block['block_index'])
        if len(block['chain_commitment']) != cfg.CHAIN_COMMIT_LEN:
            print('~20')
            raise Exception('chain_commit len wrong')
        int(block['epoch_timestamp'])
        if len(block['bc_root']) != 64 or len(block['sig_root']) != 64:
            print('~21')
            raise Exception('root len incorrect')
        if type(block['bc_body']) is not list or type(block['sig_body']) is not list:
            print('~22')
            raise Exception('body is not list')
    return received_blocks


def conclude_history_process(process):
    # TODO!!!!MUST MAKE SURE THAT BLOCKS DONT GET ADDED MULTIPLE TIMES BY MULTIPLE PROCESSES!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    """incorporate information from history request"""
    if process.cached_responses[0] == "no_block":
        print("got no block")
        return

    blocks = [bk.Block(init_dict=block) for block in process.cached_responses[0]]
    if not bk.verify_block_chain(blocks):
        return
    
    for block in blocks[-cfg.DELAY :]:
        if (
            block.block_hash != cfg.temp_hashes[block.epoch_timestamp]
            or block.epoch_timestamp not in cfg.temp_hashes.keys()
        ):
            print("different chain")
            print(block.block_hash)
            print(cfg.temp_hashes[block.epoch_timestamp])
            print(block.epoch_timestamp)
            print(cfg.temp_hashes.keys())
            return

    cfg.staged_sync_blocks = blocks

