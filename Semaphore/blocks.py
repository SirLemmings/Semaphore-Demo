import hashlib
from time import time
import broadcasts as bccc
import config as cfg
import consensus as cs


def sha_hash(preimage: str) -> str:
    """Calculate the sha256 hash of a preimage"""
    sha = hashlib.sha256
    return sha(preimage.encode()).hexdigest()


def build_merkle_tree(data: list) -> list:
    """builds a merkle tree from a list of elements"""
    if data == []:
        return []

    def tree_hash(base: list) -> list:
        base = [sha_hash(item) for item in base]
        if len(base) == 1:
            return [base]
        if len(base) % 2 == 1:
            base.append(base[-1])
        left = base[::2]
        right = base[1::2]
        new_layer = [left[i] + right[i] for i in range(len(left))]
        above_layers = tree_hash(new_layer)
        above_layers.append(base)
        return above_layers

    data = [str(item) for item in data]
    tree = tree_hash(data)
    tree.append(data)
    return tree


def construct_merkle_proof(tree: list, item: str) -> tuple:
    """constructs a merkle path for a item in the tree"""
    if item not in tree[-1]:
        raise Exception(f"{item} not in data of {tree[0][0]}")
    data_index = tree[-1].index(item)
    index = data_index
    path = []
    for layer in tree[-2:0:-1]:
        if index % 2 == 0:
            path.append(layer[index + 1])
        else:
            path.append(layer[index - 1])
        index //= 2
    path.append(tree[0][0])
    return item, data_index, path


def verify_proof(proof: tuple) -> bool:
    """verifies a merkle proof"""
    item = proof[0]
    index = proof[1]
    path = proof[2]
    node = sha_hash(item)
    for sibling in path[:-1]:
        if index % 2 == 0:
            preimage = node + sibling
        else:
            preimage = sibling + node
        index //= 2
        node = sha_hash(preimage)
    return node == path[-1]


def verify_block_chain(blocks):
    first_block = blocks[0]
    first_block_epoch = first_block.epoch_timestamp
    previous_epochs = [epoch for epoch in cfg.epochs if epoch < first_block_epoch][
        -cfg.DELAY * 2 :
    ]
    if first_block_epoch - cfg.EPOCH_TIME in cfg.historic_states:
        previous_state = cfg.historic_states[first_block_epoch - cfg.EPOCH_TIME]
    else:
        last_saved_state_epoch = [
            epoch for epoch in cfg.historic_epochs if epoch < first_block_epoch
        ][-1]
        last_common_epoch = [
            epoch for epoch in cfg.epochs if epoch < first_block_epoch
        ][-1]
        starting_state = cfg.historic_states[last_saved_state_epoch]
        epochs_to_recalc = cfg.epochs[
            cfg.indexes[last_saved_state_epoch]+1 : cfg.indexes[last_common_epoch]+1
        ]
        for epoch in epochs_to_recalc:
            starting_state = cs.calc_state_update(cfg.blocks[epoch], starting_state)
        previous_state = starting_state

    previous_hashes = {epoch: cfg.hashes[epoch] for epoch in previous_epochs}
    for block in blocks:
        if not block.check_chain_commitment(previous_epochs, previous_hashes):
            print("commit")
            return False
        if not block.check_block_valid(previous_epochs, previous_state):
            print("block")
            return False
        previous_state = cs.calc_state_update(block,previous_state)
        previous_epochs.append(block.epoch_timestamp)
        previous_hashes[block.epoch_timestamp] = block.block_hash
    return True


class Block:
    def __init__(self, broadcasts=None, epoch=None, init_dict=None):
        """Create a block from a set of broadcasts or from a dict"""
        if init_dict is None:
            data = [bccc.split_broadcast(broadcast) for broadcast in broadcasts]
            if cfg.activated:
                self.chain_commitment = cfg.epoch_chain_commit[epoch]
            else:
                self.chain_commitment = data[0]["chain_commit"]
            self.epoch_timestamp = epoch

            alias_list = [bc["alias"] for bc in data]
            bc_data = [bc["sig_image"] for bc in data]
            bc_data = [
                bc[: cfg.ALIAS_LEN] + bc[cfg.ALIAS_LEN + cfg.CHAIN_COMMIT_LEN :]
                for bc in bc_data
            ]  # removes chain commitment from each broadcast

            bc_data = [broadcast for _, broadcast in sorted(zip(alias_list, bc_data))]
            sig_data = [bc["signature"] for bc in data]
            sig_data = [bc for _, bc in sorted(zip(alias_list, sig_data))]

            # remove duplicate aliases/broadcasts

            seen_aliases = set()
            bc_data_filtered = []
            sig_data_filtered = []
            for alias, broadcast, sig in zip(sorted(alias_list), bc_data, sig_data):
                if alias not in seen_aliases:
                    bc_data_filtered.append(broadcast)
                    sig_data_filtered.append(sig)
                    seen_aliases.add(alias)

            # STATE STUFF
            bc_data_final = []
            sig_data_final = []
            block_taken_nyms = set()
            relevant_state = cfg.current_state
            if cfg.MINIMUM_BROADCAST_TIMEOUT > 0:
                timeout_epochs = cfg.epochs[-cfg.MINIMUM_BROADCAST_TIMEOUT :]
                timeout_epochs = [
                    epoch
                    for epoch in timeout_epochs
                    if epoch
                    > self.epoch_timestamp
                    - cfg.MINIMUM_BROADCAST_TIMEOUT
                    - cfg.SYNC_EPOCHS
                ]
                timeout_aliases = set()
                # print(relevant_state.bc_epochs)
                # print(timeout_epochs)
                for epoch in timeout_epochs:
                    if epoch in relevant_state.bc_epochs:
                        # print(relevant_state.bc_epochs[epoch])
                        timeout_aliases = timeout_aliases.union(
                            relevant_state.bc_epochs[epoch]
                        )
                # print(timeout_aliases)
            else:
                timeout_aliases = set()
            for bc, sig in zip(bc_data_filtered, sig_data_filtered):
                indicator = int(bc[cfg.ALIAS_LEN : cfg.ALIAS_LEN + cfg.INDICATOR_LEN])
                message = bc[cfg.ALIAS_LEN + cfg.INDICATOR_LEN + indicator :]
                alias = int(bc[: cfg.ALIAS_LEN])

                if alias in timeout_aliases:
                    pass
                    continue  # DO NOT ADD TO FINAL LIST

                if message[0] != "!":  # broadcast is not an operator
                    bc_data_final.append(bc)
                    sig_data_final.append(sig)
                else:
                    operator = message.split(".")
                    if operator[0] == "!update_nym":
                        new_nym = operator[1]
                        if (
                            new_nym not in cfg.current_state.taken_nyms
                            and new_nym not in block_taken_nyms
                        ):
                            block_taken_nyms.add(new_nym)
                            bc_data_final.append(bc)
                            sig_data_final.append(sig)
            # /STATE STUFF

            if len(bc_data_final) == 0:
                raise BlockEmptyException
            bc_tree = build_merkle_tree(bc_data_final)
            sig_tree = build_merkle_tree(sig_data_final)

            self.bc_root = bc_tree[0][0]
            self.sig_root = sig_tree[0][0]
            self.bc_body = bc_tree[-1]
            self.sig_body = sig_tree[-1]

            # ***SANITYCHECK***
            commit = self.chain_commitment
            commits = [bc["chain_commit"] for bc in data]
            commits = set(commits)
            if len(commits) > 1:
                raise Exception("commits are not the same")
            try:
                c = commits.pop()
                if c != commit:
                    raise Exception("commit doesnt match epoch commit")
            except:
                pass
        else:
            self.block_index = init_dict["block_index"]
            self.chain_commitment = init_dict["chain_commitment"]
            self.epoch_timestamp = init_dict["epoch_timestamp"]
            self.bc_root = init_dict["bc_root"]
            self.sig_root = init_dict["sig_root"]
            self.bc_body = init_dict["bc_body"]
            self.sig_body = init_dict["sig_body"]

        # self.aliases = set()
        # self.state_transition = []
        # for broadcast in self.bc_body:
        #     self.aliases.add(int(broadcast[:cfg.ALIAS_LEN]))

    def update_index(self):
        self.block_index = len(cfg.indexes)

    @property
    def block_hash(self) -> str:
        """calculates the hash of a block"""
        header_str = ""
        header_str += self.bc_root
        header_str += self.sig_root
        header_str += self.chain_commitment
        header_str += str(self.epoch_timestamp)
        return sha_hash(header_str)

    def convert_to_dict(self):
        output = {}
        output["block_index"] = self.block_index
        output["chain_commitment"] = self.chain_commitment
        output["epoch_timestamp"] = self.epoch_timestamp
        output["bc_root"] = self.bc_root
        output["sig_root"] = self.sig_root
        output["bc_body"] = self.bc_body
        output["sig_body"] = self.sig_body
        return output

    def check_block_valid(self, previous_epochs, previous_state):
        """checks that all the contents of a block are valid"""
        # validate epoch_timestamp
        if type(self.epoch_timestamp) is not int:
            print(0)
            return False
        if self.epoch_timestamp % cfg.EPOCH_TIME != 0:
            print(1)
            return False
        if self.epoch_timestamp <= previous_epochs[-1]:
            print(2)
            return False
        uncommitted_epochs = [
            epoch
            for epoch in previous_epochs
            if epoch > self.epoch_timestamp - (cfg.DELAY - 1) * cfg.EPOCH_TIME
        ]
        if len(uncommitted_epochs) > 0:
            first_uncommitted_epoch = uncommitted_epochs[0]
            if (
                self.epoch_timestamp
                >= first_uncommitted_epoch + (cfg.DELAY - 1) * cfg.EPOCH_TIME
            ):
                print(3)
                return False
        # Validate body
        if (
            len(self.bc_body) == 0
            or len(self.sig_body) == 0
            or len(self.sig_body) != len(self.bc_body)
        ):
            print(4)
            return False
        bc_list = [
            f"{sig}{bc[:cfg.ALIAS_LEN]}{self.chain_commitment}{bc[cfg.ALIAS_LEN:]}"
            for sig, bc in zip(self.sig_body, self.bc_body)
        ]
        alias_list = [bccc.split_broadcast(bct)["alias"] for bct in bc_list]
        if alias_list != sorted(alias_list):
            print(5)
            return False
        if len(alias_list) != len(set(alias_list)):
            print(6)
            return False
        for bct in bc_list:
            if not bccc.verify_broadcast_rules(bct):
                print(7)
                return False
        
        if cfg.MINIMUM_BROADCAST_TIMEOUT > 0:
            timeout_epochs = cfg.epochs[-cfg.MINIMUM_BROADCAST_TIMEOUT :]
            timeout_epochs = [
                epoch
                for epoch in timeout_epochs
                if epoch
                > self.epoch_timestamp
                - cfg.MINIMUM_BROADCAST_TIMEOUT
                - cfg.SYNC_EPOCHS
            ]
            timeout_aliases = set()
                # print(relevant_state.bc_epochs)
                # print(timeout_epochs)
            for epoch in timeout_epochs:
                if epoch in previous_state.bc_epochs:
                    # print(relevant_state.bc_epochs[epoch])
                    timeout_aliases = timeout_aliases.union(
                        previous_state.bc_epochs[epoch]
                    )
            for alias in alias_list:
                if alias in timeout_aliases:
                    print(11)
                    return False
        # validate bc_root and sig_root
        if self.bc_root != build_merkle_tree(self.bc_body)[0][0]:
            print(8)
            return False
        if self.sig_root != build_merkle_tree(self.sig_body)[0][0]:
            print(9)
            return False
        # TODO check validity of state transition

        # STATE STUFF
        block_taken_nyms = set()
        for bc in self.bc_body:
            indicator = int(bc[cfg.ALIAS_LEN : cfg.ALIAS_LEN + cfg.INDICATOR_LEN])
            message = bc[cfg.ALIAS_LEN + cfg.INDICATOR_LEN + indicator :]

            if message[0] == "!":  # broadcast is not an operator
                operator = message.split(".")
                if operator[0] == "!update_nym":
                    new_nym = operator[1]
                    if (
                        new_nym in cfg.current_state.taken_nyms
                        or new_nym in block_taken_nyms
                    ):
                        print(10)
                        return False
        # /STATE STUFF

        return True

    def check_chain_commitment(self, previous_epochs, previous_hashes):
        """checks that the chain commitment is valid and not in the future"""
        committed_epochs = [
            epoch
            for epoch in previous_epochs
            if epoch <= self.epoch_timestamp - (cfg.DELAY - 1) * cfg.EPOCH_TIME
        ][-cfg.DELAY :]
        committed_hashes = [previous_hashes[i] for i in committed_epochs]
        correct_commitment = cs.hash_commitments(committed_hashes)
        # print('bb', self.epoch_timestamp, correct_commitment, committed_hashes)
        # print(previous_epochs)
        # print()
        # print('dd', self.chain_commitment)
        # print()
        diff = (
            int((self.epoch_timestamp - committed_epochs[-1]) / cfg.EPOCH_TIME)
            % cfg.DELAY
        )
        correct_commitment += f"{diff:02d}"
        return correct_commitment == self.chain_commitment

    def get_block_engagements(self) -> set:
        """returns a set of all aliases broadcasting in a block"""
        if self.bc_body == "None":
            return set()
        return {int(broadcast[: cfg.ALIAS_LEN]) for broadcast in self.bc_body}


class BlockEmptyException(Exception):
    pass
