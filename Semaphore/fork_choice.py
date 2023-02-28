import config as cfg
import communications as cm
import consensus as cs
import blocks as bk
import timing as tm
from process import Process
import ast
import os
import json
import state as st

reorg_processes = set()


def request_fork_history(alias):
    print("~requesting fork")
    index = cfg.MINIMUM_REORG_DEPTH
    past_epochs = []
    while True:
        try:
            past_epochs.append(cfg.epochs[-index])
            index *= 2
        except:
            break

    past_hashes = [cfg.hashes[epoch] for epoch in past_epochs if epoch > cfg.DELAY - 1]
    Process(
        1,
        format_fork_request,
        conclude_fork_process,
        "fork_request",
        (past_hashes, past_epochs),
        True,
        specific_peers=[alias],
    )


def fulfill_fork_request(alias, query_id, past):
    """send history including common epoch"""
    # print("~fulfilling fork")
    if cfg.activated:
        if (
            len(past[0]) > 0
        ):  # sometimes peer does not send any epochs because there arent enough epochs. this handles that case. might be worth fixing on the other end
            past_hashes = past[0]
            past_epochs = past[1]
            if past_hashes[0] in cfg.hashes.values():
                print("reorg not deep enough")
                return
        else:
            past_hashes = past[0]
            past_epochs = past[0]
        shared_block_index = cfg.DELAY - 1

        # TODO pretty sure this works right but actually dont know for sure
        for block_hash, block_epoch in zip(past_hashes[1:], past_epochs[1:]):
            # print("~index", index)
            # print(print("~start epoch", cfg.epochs[index]))
            if block_hash not in cfg.epoch_chain_commit:
                continue
            if cfg.hashes[block_epoch] != block_hash:
                print("hash/epoch dont match")
                return
            shared_block_index = cfg.epochs.index(block_epoch)
            break
            # if block_hash in cfg.epoch_chain_commit:
            #     shared_epoch = past_epochs[past_hashes.index(block_hash)]
            #     if cfg.hashes[shared_epoch] != block_hash:
            #         print("hash/epoch dont match")
            #         return
            #     index = cfg.epochs.index(shared_epoch)
            #     break

        history_epochs = cfg.epochs[shared_block_index:]
        # print('~epochs',cfg.epochs)
        # print("~index", index)
        # print("~start epoch", cfg.epochs[index])
        history_blocks = [cfg.blocks[epoch] for epoch in history_epochs]
        history_blocks = [
            block.convert_to_dict() if block != "GENESIS" else block
            for block in history_blocks
        ]
        # history_blocks = []
        # for epoch in history_epochs:
        #     block = cfg.blocks[epoch]
        #     if type(block) is str:
        #         history_blocks.append(block)
        #     else:
        #         history_blocks.append(block.convert_to_dict())
        print("fulfilled fork successfully")
        cm.send_peer_message(alias, f"query_fulfillment|{query_id}|{history_blocks}")
    else:
        print("not activated. delaying fork fulfillment")


def format_fork_request(query, response):
    # print("~formatting fork")
    received_blocks = ast.literal_eval(response)
    if type(received_blocks) is not list:
        raise Exception("reveiced_blocks is not list")
    for block in received_blocks:
        if type(block) is dict:
            if set(block.keys()) != {
                "block_index",
                "chain_commitment",
                "epoch_timestamp",
                "bc_root",
                "sig_root",
                "bc_body",
                "sig_body",
            }:
                print("~2")
                raise Exception("block keys are incorrect")
            int(block["block_index"])
            if len(block["chain_commitment"]) != cfg.CHAIN_COMMIT_LEN:
                print("~3")
                raise Exception("chain_commit len wrong")
            int(block["epoch_timestamp"])
            if len(block["bc_root"]) != 64 or len(block["sig_root"]) != 64:
                print("~4")
                raise Exception("root len incorrect")
            if (
                type(block["bc_body"]) is not list
                or type(block["sig_body"]) is not list
            ):
                print("~5")
                raise Exception("body is not list")
        elif block == "GENESIS":
            pass
        else:
            print("~6")
            raise Exception("block is of wrong type")
    return received_blocks


def conclude_fork_process(process):
    # print("~concluding fork")
    blocks = process.cached_responses[0]
    for block in blocks:
        if type(block) is bk.Block:
            if not block.check_block_valid():
                print("bad block")
                return
    blocks = [bk.Block(init_dict=block) for block in blocks if block != "GENESIS"]
    last_common_epoch = find_last_common_epoch(blocks.copy())

    print('bbef',[b.epoch_timestamp for b in blocks])
    swap = compare_weight(blocks.copy(), last_common_epoch)
    print('baft',[b.epoch_timestamp for b in blocks])
    print("~SWAP", swap)

    if swap:
        print("***REORG***")
        tm.deactivate()
        remove_history(last_common_epoch)
        for block in blocks:
            
            # block = bk.Block(init_dict=block)
            block_epoch = block.epoch_timestamp
            if block_epoch<= last_common_epoch:
                continue
            if block_epoch >= cfg.current_epoch - cfg.MINIMUM_REORG_DEPTH:
                break
            cs.load_block_data(block)
            dump = json.dumps(block.convert_to_dict())
            name = os.path.join(f"./{cfg.ALIAS}/blocks", f"{block_epoch}.json")
            with open(name, "wb") as f:
                f.write(dump.encode("utf-8"))
        cfg.initialized = True
        cfg.enforce_chain = True
        global reorg_processes
        reorg_processes = set()
    else:
        print("~no reorg")


def find_last_common_epoch(blocks):
    print("recieved blocks", [block.epoch_timestamp for block in blocks])
    common_epoch = cfg.DELAY-1
    while len(blocks)>0:
        comparison_block = blocks.pop(0)
        block_epoch = comparison_block.epoch_timestamp
        block_hash = comparison_block.block_hash
        if block_epoch not in cfg.hashes:
            break
        elif block_hash != cfg.hashes[block_epoch]:
            break
        else:
            common_epoch = block_epoch
    print("LAST COMMON EPOCH: ", common_epoch)
    return common_epoch


def remove_history(last_common_epoch):
    # print("bef", cfg.epochs[-15:])
    fork_index = cfg.epochs.index(last_common_epoch) + 1
    print("LCE", fork_index)
    print("LCI", fork_index)
    for epoch in cfg.epochs[fork_index:]:
        if cfg.blocks[epoch] == "GENESIS":
            fork_index += 1
            continue

        del cfg.blocks[epoch]
        del cfg.hashes[epoch]
        del cfg.indexes[epoch]
        if epoch in cfg.historic_states:
            cfg.historic_epochs.remove(epoch)
            del cfg.historic_states[epoch]
            print("removing state", epoch)
        name = os.path.join(f"./{cfg.ALIAS}/blocks", f"{epoch}.json")
        os.remove(name)
    cfg.epochs = cfg.epochs[:fork_index]

    st.initialize_buckets()
    start_epoch = cfg.historic_epochs[-1]
    cfg.current_state = cfg.historic_states[start_epoch]
    epochs_to_recalc = cfg.epochs[cfg.indexes[start_epoch] + 1 :]
    print("~~~~~~~~")
    print(start_epoch)
    print(cfg.indexes[start_epoch] + 1)
    print(epochs_to_recalc)
    print("~~~~~~~~")

    for epoch in epochs_to_recalc:
        print("recalc")
        cs.update_state(cfg.blocks[epoch])
    # RECALCULATE STATE UP TO MOST RECENT EPOCH
    print("aft", cfg.epochs[-30:])


def compare_weight(alt_blocks, last_common_epoch):
    # print('fc')
    # print(last_common_epoch)
    # print(cfg.epochs)
    # print(cfg.epochs.index(last_common_epoch) + 1)
    # print(cfg.epochs[cfg.epochs.index(last_common_epoch) + 1 :])
    # print(cfg.epochs)
    current_blocks = [
        block
        for block in [
            cfg.blocks[epoch]
            for epoch in cfg.epochs[cfg.epochs.index(last_common_epoch) + 1 :]
        ]
        if block != "GENESIS"
    ]

    if len(alt_blocks) == 0 or len(current_blocks) == 0:
        print("~uhhhhh", len(alt_blocks), len(current_blocks))
        return

    chain_engagements_alt = set()
    chain_engagements_current = set()
    shallow_block_alt = alt_blocks.pop(-1)
    time_alt = shallow_block_alt.epoch_timestamp
    shallow_block_current = current_blocks.pop(-1)
    time_current = shallow_block_current.epoch_timestamp

    while True:
        if time_current > time_alt:
            pre_engagements = shallow_block_current.get_block_engagements()
            pre_engagements -= chain_engagements_alt
            chain_engagements_current = chain_engagements_current.union(pre_engagements)
            if len(current_blocks) == 0:
                time_current = -1
            else:
                shallow_block_current = current_blocks.pop(-1)
                time_current = shallow_block_current.epoch_timestamp

        elif time_alt > time_current:
            pre_engagements = shallow_block_alt.get_block_engagements()
            pre_engagements -= chain_engagements_current
            chain_engagements_alt = chain_engagements_alt.union(pre_engagements)
            if len(alt_blocks) == 0:
                time_alt = -1
            else:
                shallow_block_alt = alt_blocks.pop(-1)
                time_alt = shallow_block_alt.epoch_timestamp

        else:
            current_pre_engagements = shallow_block_current.get_block_engagements()
            current_pre_engagements -= chain_engagements_alt
            alt_pre_engagements = shallow_block_alt.get_block_engagements()
            alt_pre_engagements -= chain_engagements_current
            chain_engagements_current = chain_engagements_current.union(
                current_pre_engagements
            )
            chain_engagements_alt = chain_engagements_alt.union(alt_pre_engagements)
            if len(current_blocks) == 0:
                time_current = -1
            else:
                shallow_block_current = current_blocks.pop(-1)
                try:
                    time_current = shallow_block_current.epoch_timestamp
                except Exception as e:
                    print(shallow_block_current)
                    print(e)

            if len(alt_blocks) == 0:
                time_alt = -1
            else:
                shallow_block_alt = alt_blocks.pop(-1)
                time_alt = shallow_block_alt.epoch_timestamp

        if time_current == -1 and time_alt == -1:
            break

    print(
        f"~alternate_weight: {len(chain_engagements_alt)}, current_weight: {len(chain_engagements_current)}"
    )
    return len(chain_engagements_alt) > len(chain_engagements_current)
