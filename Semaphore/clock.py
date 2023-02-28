import time

from process import Process
import config as cfg
import communications as cm
import random


network_offset = 0
base_offset = cfg.TIME_BASE_OFFSET
correction_offset = 0
correction_factor = 0


def local_time() -> float:
    """return node local time"""
    return time.time() + base_offset


def network_time() -> float:
    """return node network time"""
    return local_time() + network_offset


def report_time() -> float:
    """return node reported network time"""
    return network_time() + correction_factor


def total_offset() -> float:
    """return total offset to nodes local time"""
    return network_offset + base_offset


def update_correction() -> None:
    """
    Calculates the amount to over/underreport to correct perceived network time error
    
    Returns: The correction factor offset used for reporting network time
    """
    global correction_offset
    if abs(network_offset) <= cfg.TIME_ERROR_THRESHOLD:
        if correction_offset > 0:
            correction_offset -= cfg.CORRECTION_DRIFT
        elif correction_offset < 0:
            correction_offset += cfg.CORRECTION_DRIFT
        global correction_factor
        correction_factor = 0
    else:
        if abs(correction_offset) < cfg.REPORT_ERROR_THRESHOLD - cfg.SAFETY_FACTOR:
            if network_offset > 0:
                correction_offset -= cfg.CORRECTION_DRIFT
            else:
                correction_offset += cfg.CORRECTION_DRIFT
        correction_factor = correction_offset


def update_network_offset(offsets: list) -> None:
    """
    Updates the estimated network time offset based on sampled time offsets
    Parameters:
        times (list): A list of times sampled from random peers
    """
    offsets = [offset for offset in offsets if abs(offset) < cfg.REPORT_ERROR_THRESHOLD]
    if len(offsets) == 0:
        return
    sample = sum(offsets) / (len(offsets))
    global network_offset
    network_offset+=sample*(1-cfg.TIME_INERTIA)
    update_correction()
    cfg.network_offset = network_offset



def initiate_time_update() -> None:
    """
    Creates the time update process and time request and sends the time request to peers
    """
    Process(
        cfg.TIME_SAMPLE_NUM,
        format_response,
        conclude_process,
        "time_request",
        time.time(),
    )


def fulfill_time_request(alias: int, query_id: str) -> None:
    """
    Sends a message to a specified peer to fulfill their received request
    
    Parameters:
        alias (int): A valid alias of the peer who sent the request
        request_id (str): The ID corresponding to the peer's time process that the request belongs to
    """
    cm.send_peer_message(alias, f"query_fulfillment|{query_id}|{report_time()}")



def format_response(query, response: str) -> float:
    """converte reported time to offset"""
    received_time = float(response)
    ping_correction = (time.time() - query.data) / 2
    offset = received_time + ping_correction - network_time()
    return offset


def conclude_process(process) -> None:
    """
    Concludes the time update process
    """
    update_network_offset(process.cached_responses)

