import connections as cn
import config as cfg
import sched
import time
import clock as cl
import communications as cm
import consensus as cs
from epoch_processor import EpochProcessor
from bidict import bidict
import random
import state as st

FREQ = int(cfg.EPOCH_TIME / cfg.CLOCK_INTERVAL)
position = 0
aligned = False
ideal_time = 0


def time_events():
    """
    Executes actions on ticks of the clock, including at start of epoch
    
    The event loop runs continuously on its own thread managing time synchronization, epoch tracking, and . 
    """

    s = sched.scheduler(time.time, time.sleep)

    def event_loop():
        """functions that execute on a timer with epochs"""
        global position
        global aligned
        global ideal_time
        now = cl.network_time()
        cl.initiate_time_update()
        if aligned:
            s.enter(ideal_time + cfg.CLOCK_INTERVAL - now, 0, event_loop)
            ideal_time += cfg.CLOCK_INTERVAL
        else:
            offset = now % cfg.CLOCK_INTERVAL
            s.enter((cfg.CLOCK_INTERVAL - offset), 0, event_loop)

        if not aligned and round(now, 2) % cfg.EPOCH_TIME == 0:
            aligned = True
            ideal_time = round(now, 2)

        if aligned:
            if position == 0:
                run_epoch()
            position += 1
            position %= FREQ

    s.enter(0, 0, event_loop)
    s.run()


def run_epoch():
    next_epoch = cfg.current_epoch + cfg.FORWARD_SLACK_EPOCHS * cfg.EPOCH_TIME
    if cfg.SHOW_EPOCH_INFO:
        print()
        print()
        print()
        print("~EPOCH", cfg.current_epoch)
        # print(list(cfg.epoch_processes.keys()))
        # print("st epochs", list(cfg.current_state.bc_epochs.keys()))
        # print('hs',cfg.hashes)
        # print(cfg.historic_states)
        # try:
        # print(list(cfg.current_state.bc_epochs.keys()))
        # print(cfg.current_state.taken_nyms)
        # print(cfg.current_state.nym_owners)
        # print(cfg.historic_epochs)
        # except:
        #     pass
        # print(cfg.epochs[-5:])
        # print(cfg.indexes)
        # print(sorted(cfg.hashes))
        # print(sorted(cfg.temp_hashes))

    if cfg.initialized:
        # Handle the processing of each active epoch
        try:
            for epoch in cfg.epoch_processes:
                cfg.epoch_processes[epoch].step()

            if (
                next_epoch not in cfg.epoch_processes
            ):  # TODO do something better than this check
                start_epoch_process(next_epoch)
        except RuntimeError as e:  # occasional issue upon reorging
            print("IGNORING ERROR:")
            print(e)

        if cfg.current_epoch > 0:
            # Send test broadcast each epoch
            if cfg.SEND_TEST_BC and cfg.activated and len(cfg.epoch_processes) > 1:
                for i in range(1):
                    if random.random() < 1 or cfg.bootstrapping:
                        cm.originate_broadcast(f"sync{i}")

            # delete epoch processor when epoch is no longer active
            for epoch in cfg.finished_epoch_processes:
                try:
                    cfg.epoch_processes[epoch].kill_process()
                except KeyError as e:  # occasional error upon reorging
                    print("IGNORING ERROR:")
                    print(e)
            cfg.finished_epoch_processes = set()
            cs.load_staged_updates()

            if len(cfg.staged_sync_blocks) > 0:
                cs.sync_func(cfg.staged_sync_blocks)

        if cfg.committed_epoch == float("inf"):
            if len(cfg.temp_epochs) == cfg.DELAY:
                cfg.committed_epoch = cfg.current_epoch + cfg.EPOCH_TIME
        elif (
            not cfg.synced
        ):  # TODO this is delayed by cfg.DELAY periods because the chain commit might be borked if it is run not at the start of epoch process. should fix the function and remove the extra delay
            cs.sync()

    if cfg.current_epoch == 0:
        cfg.current_epoch = round(cl.network_time()) + cfg.EPOCH_TIME
    else:
        cfg.current_epoch += cfg.EPOCH_TIME
        if cfg.current_epoch != round(cl.network_time()) + cfg.EPOCH_TIME:
            pass


# TODO remove this function once we know its working. just merge with run_epoch
def start_epoch_process(epoch=cfg.current_epoch):
    """initiate new epoch process"""
    if epoch in cfg.epoch_processes:
        print("something went very wrong. epoch process already exists")
    if (
        epoch not in cfg.epoch_processes
    ):  # this check prevents ValueDuplicationError upon reorg
        cfg.epoch_processes[epoch] = EpochProcessor(epoch)


def initialize():
    print("EPOCH PROCESSING ACTIVATED")
    cfg.initialized = True


def deactivate():
    print("EPOCH PROCESSING HALTED")
    cn.signal_deactivation()
    processor_epochs = [epoch for epoch in cfg.epoch_processes.keys()]
    for epoch in processor_epochs:
        try:
            cfg.epoch_processes[epoch].kill_process()
        except:
            pass

    cfg.initialized = False
    cfg.committed_epoch = float("inf")
    cfg.synced = False
    cfg.activated = False
    cfg.enforce_chain = False
    cfg.activation_epoch = float("inf")

    cfg.temp_blocks = {}
    cfg.temp_epochs = []
    cfg.temp_hashes = bidict({})
    cfg.staged_sync_blocks = []

    cfg.staged_block_updates = []
    cfg.temp_staged_block_updates = []
    cfg.staged_sync_blocks = []

    cfg.finished_epoch_processes = set()
