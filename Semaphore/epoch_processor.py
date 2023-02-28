from relay_processor import RelayProcessor
from vote_processor import VoteProcessor
from build_processor import BuildProcessor
import config as cfg
import connections as cn
import broadcasts as bc
import consensus as cs

EPOCH_VOTE_DELAY = (cfg.FORWARD_SLACK_EPOCHS + cfg.SLACK_EPOCHS) * cfg.EPOCH_TIME
BUILD_DELAY = (
    cfg.VOTE_MAX_EPOCHS + cfg.SLACK_EPOCHS + cfg.FORWARD_SLACK_EPOCHS
) * cfg.EPOCH_TIME
FINALIZE_DELAY = (
    cfg.SYNC_EPOCHS + cfg.VOTE_MAX_EPOCHS + cfg.SLACK_EPOCHS + cfg.FORWARD_SLACK_EPOCHS
) * cfg.EPOCH_TIME


class EpochProcessor:
    """class that handles the processing of everything for a particular epoch. makes a child processor for each stage of epoch processing"""

    def __init__(self, epoch):
        self.epoch = epoch
        self.cached_processes = []
        self.staged_cached_processes = []
        self.processor = RelayProcessor(self.epoch)
        self.state = "relay"
        self.time_alive = 0
        if epoch >= cfg.committed_epoch:
            try:
                if cfg.synced:
                    cfg.epoch_chain_commit[self.epoch] = cs.chain_commitment(
                        self.epoch, cfg.epochs, cfg.hashes, origin="ep"
                    )
                else:
                    cfg.epoch_chain_commit[self.epoch] = cs.chain_commitment(
                        self.epoch, cfg.temp_epochs, cfg.temp_hashes, origin="ep"
                    )
            except Exception as e:
                print()
                print("~", cfg.epoch_chain_commit)
                print(list(cfg.epoch_chain_commit.keys()))
                print()
                raise e
            # print(cfg.epoch_chain_commit[self.epoch])

    def step(self):
        """update processor at the end of each epoch"""
        self.time_alive += cfg.EPOCH_TIME
        if self.time_alive == FINALIZE_DELAY:
            self.processor.finalize_block()
            cfg.finished_epoch_processes.add(self.epoch)
            if self.epoch == cfg.activation_epoch - cfg.EPOCH_TIME:
                cn.signal_activation()
                cfg.activated = True
                cfg.enforce_chain = True
                print("***ACTIVATED***")
            
            if self.epoch == cfg.bootstrapped_epoch - cfg.EPOCH_TIME:
                cfg.bootstrapping = False
                print("***BOOTSTRAPPED***")

        elif self.time_alive == BUILD_DELAY:
            confirmed_bc = self.processor.terminate_vote()
            if cfg.SHOW_CONF_BC and self.epoch % (cfg.EPOCH_TIME * 2) == 0:
                print("CONFIRMED BROADCASTS:")
                output = []
                for i in confirmed_bc:
                    alias = bc.split_broadcast(i)["alias"]
                    bcid = bc.calc_bcid(i)
                    output.append((alias, bcid))
                for i in sorted(output):
                    print(f"{i[0]}: {i[1]}")
            self.processor = BuildProcessor(self.epoch, confirmed_bc)
            self.state = "sync"
        elif self.time_alive == EPOCH_VOTE_DELAY:
            seen_bc = self.processor.seen_bc
            if cfg.SHOW_SEEN_BC:
                print("SEEN BROADCASTS:")
                output = []
                for i in seen_bc:
                    alias = bc.split_broadcast(i)["alias"]
                    bcid = bc.calc_bcid(i)
                    output.append((alias, bcid))
                for i in sorted(output):
                    print(f"{i[0]}: {i[1]}")
            self.processor = VoteProcessor(self.epoch, seen_bc)
            self.state = "vote"
        self.cached_processes = self.staged_cached_processes.copy()
        self.staged_cached_processes = []
        self.execute_cached_processes()

    def kill_process(self):
        if self.state == "vote":
            self.processor.execute = False
        self.processor = None
        del cfg.epoch_processes[self.epoch]

    def execute_new_process(self, state, func, *args):
        """respond to a message from a peer. if it should be processed next epoch then it is cached"""
        if state == self.state:
            func = self.find_func(func)
            func(*args)
        else:
            self.staged_cached_processes.append(
                {"state": state, "func": func, "args": args}
            )

    def execute_cached_processes(self):
        """execute all valid processes, delete otherwise"""
        for process in self.cached_processes:
            state = process["state"]
            func = process["func"]
            args = process["args"]
            if state == self.state:
                func = self.find_func(func)
                func(*args)

    def find_func(self, func):
        """given the type of process return the correct function of child processor"""
        if func == "relay":
            func = self.processor.handle_relay
        if func == "bc_request":
            func = self.processor.fulfill_bc_request
        if func == "vote_request":
            func = self.processor.fulfill_vote_request
        return func
