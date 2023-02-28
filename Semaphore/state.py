from blocks import build_merkle_tree, sha_hash
import config as cfg
import json
import os


class State:
    def __init__(self, init_dict=None) -> None:
        if init_dict is None:
            self.epoch = 0
            self.bc_epochs = {}  # {epoch: {aliases}}
            self.taken_nyms = set()
            self.nym_owners = {}  # {alias: nym}
        else:
            self.epoch = init_dict["epoch"]
            self.bc_epochs = {
                int(epoch): set(init_dict["bc_epochs"][epoch])
                for epoch in init_dict["bc_epochs"]
            }
            self.taken_nyms = set(init_dict["taken_nyms"])
            self.nym_owners = init_dict["nym_owners"]

    def duplicate(self):  # this should probably override copy instead
        dup = State()
        dup.epoch = self.epoch
        dup.bc_epochs = self.bc_epochs
        dup.taken_nyms = list(self.taken_nyms)
        dup.nym_owners = self.nym_owners
        return dup

    def write_to_disk(self):
        output = {}
        output["epoch"] = self.epoch
        output["bc_epochs"] = {
            epoch: list(self.bc_epochs[epoch]) for epoch in self.bc_epochs
        }
        output["taken_nyms"] = list(self.taken_nyms)
        output["nym_owners"] = self.nym_owners

        dump = json.dumps(output)
        name = os.path.join(f"./{cfg.ALIAS}/states", f"{self.epoch}.json")
        with open(name, "wb") as f:
            f.write(dump.encode("utf-8"))

    def __del__(self):
        if self.epoch > 0 and cfg.ALIAS is not None:
            name = os.path.join(f"./{cfg.ALIAS}/states", f"{self.epoch}.json")
            os.remove(name)

    @property
    def state_hash(self):
        bc_epoch_list = sorted([(epoch,sorted(self.bc_epochs[epoch])) for epoch in self.bc_epochs])
        taken_nyms_list = sorted(self.taken_nyms)
        nym_owners_list = sorted([(alias,self.nym_owners[alias]) for alias in self.nym_owners])
        state_str = ""
        state_str += str(self.epoch)
        state_str += build_merkle_tree(bc_epoch_list)[0][0]
        state_str += build_merkle_tree(taken_nyms_list)[0][0]
        state_str += build_merkle_tree(nym_owners_list)[0][0]
        return sha_hash(state_str)


buckets = []


def initialize_buckets():
    global buckets
    buckets = []
    history = cfg.historic_epochs[1:]
    for i in range(len(history) - 1):
        buckets.append(
            list(
                range(
                    history[i],
                    history[i + 1],
                    cfg.RECENT_SAVED_STATES_NUM * cfg.EPOCH_TIME,
                )
            )
        )
    buckets.append([cfg.historic_epochs[-1]])


def clear_state():
    if len(cfg.historic_epochs) > cfg.RECENT_SAVED_STATES_NUM + 1:
        history = cfg.historic_epochs[1 : -cfg.RECENT_SAVED_STATES_NUM]
        last_epoch = history[-1]
        if last_epoch % cfg.SAVED_STATE_RATE != 0:
            del cfg.historic_states[last_epoch]
            cfg.historic_epochs.remove(last_epoch)
        else:
            buckets.append([last_epoch])

            for i in range(len(buckets) - 2, 0, -1):
                if len(buckets[i - 1]) == len(buckets[i]) and len(buckets[i]) == len(
                    buckets[i + 1]
                ):
                    buckets[i - 1] += buckets.pop(i)
            saved_epochs = {b[0] for b in buckets}

            for epoch in history:
                if epoch not in saved_epochs:
                    cfg.historic_epochs.remove(epoch)
                    del cfg.historic_states[epoch]
