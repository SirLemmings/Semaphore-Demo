from ecdsa import SigningKey, VerifyingKey, keys, SECP256k1
import hashlib
import config as cfg


def generate_broadcast(message: str, chain_commit: str, parent=""):
    """
    Returns a properly formatted broadcast string for the current epoch

    Parameters:
        message (str): The message to be broadcast
        chain_commit (str): The chain commitment corresponding to the current epoch
        parent (str): The ID corresponding to a parent broadcast
    """
    chain_commit = str(chain_commit).zfill(cfg.CHAIN_COMMIT_LEN)
    indicator = len(parent)
    indicator = str(indicator).zfill(cfg.INDICATOR_LEN)
    broadcast = chain_commit + indicator + parent + str(message)
    broadcast = sign_msg(broadcast)
    return broadcast


def calc_sig(msg: str):
    """
    Generates a valid signature for the given msg using sk

    Parameters:
        msg (str): The message to be signed. Character limit is ??

    Returns: The valid signature
    """
    privkey = SigningKey.from_string(bytes.fromhex(cfg.sk), curve=SECP256k1)
    b_msg = bytes(msg, "utf-8")
    sig = privkey.sign(b_msg)
    return sig.hex()


def sign_msg(msg: str):
    """
    Returns a valid signature appended to signed message
    
    Signs the message through the broadcast manager and appends it to the message

    Parameters:
        msg (str): The message to be signed. Character limit is ??
    
    Returns: Signature plus message
    """
    msg = f"{str(cfg.ALIAS).zfill(cfg.ALIAS_LEN)}{msg}"
    sig = calc_sig(msg)
    msg = f"{sig}{msg}"
    return msg


def format_message(msg):
    """
    Retreives bytes formatted for broadcasting with a proper header
    
    Parameters:
        msg (str): The message to be formatted for broadcasting

    Returns: The encoded message with a header attached
    """
    header = f"{len(msg):<{cfg.HEADER_LENGTH}}".encode("utf-8")
    message = msg.encode("utf-8")
    return header + message


def verify_broadcast_rules(message):
    if not verify_message_sig:
        return False
    # other rulese
    return True


def verify_message_sig(message):
    """
    Checks the validity of a properly formatted message

    Parameters:
        broadcast (str): The broadcast to be verified

    Returns:
        True if the the broadcast is valid, False otherwise
    """
    signature, message = message[: cfg.SIG_LEN], message[cfg.SIG_LEN :]
    alias = message[: cfg.ALIAS_LEN]
    pk = cfg.alias_keys[int(alias)]

    pubkey = VerifyingKey.from_string(bytes.fromhex(pk), curve=SECP256k1)
    sig_image = str.encode(message)
    signature = bytes.fromhex(signature)

    try:
        pubkey.verify(signature, sig_image)
        return True
    except keys.BadSignatureError:
        print("invalid signature")
        return False


def check_broadcast_validity(broadcast,) -> bool:
    """checks that a broadcast breaks no network rules"""
    try:
        bc_data = split_broadcast(broadcast)
    except:
        return False
    chain_commit = bc_data["chain_commit"]
    if chain_commit not in cfg.epoch_chain_commit.inverse.keys():
        print("invalid 1")
        print(chain_commit)
        print(cfg.epoch_chain_commit.inverse.keys())
        return False
    epoch = cfg.epoch_chain_commit.inverse[chain_commit]
    if epoch < cfg.current_epoch - cfg.SLACK_EPOCHS * cfg.EPOCH_TIME:
        print("invalid 2")
        return False
    if epoch > cfg.current_epoch + cfg.FORWARD_SLACK_EPOCHS * cfg.EPOCH_TIME:
        print("invalid 3")
        return False
    return verify_broadcast_rules(broadcast)
    # return verify_message_sig(broadcast)


def check_broadcast_validity_vote(broadcast, vote_epoch) -> bool:
    """checks that a broadcast breaks no network rules"""
    bc_data = split_broadcast(broadcast)
    chain_commit = bc_data["chain_commit"]
    if cfg.activated:
        if chain_commit != cfg.epoch_chain_commit[vote_epoch]:
            return False
        return verify_broadcast_rules(broadcast)
        # return verify_message_sig(broadcast)
    else:
        return verify_broadcast_rules(broadcast)
        # return verify_message_sig(broadcast)


def split_broadcast(broadcast: str):
    """
    Splits a broadcast into its constituent parts
    
    Parameters:
        broadcast (str): The received broadcast to be split
    
    Returns: A dictionary with the following data
        alias (int): the alias of the sender
        chain_commit (str): a chain_commit corresponding to when the broadcast was sent
        parent (str): the ID of a parent broadcast
        message (str): the message of the broadcast
        signature (str): the signature for the entire broadcast
        sig_image (str): the broadcast image that is signed
    """
    try:
        orig = broadcast
        signature, broadcast = broadcast[: cfg.SIG_LEN], broadcast[cfg.SIG_LEN :]
        sig_image = broadcast
        alias, broadcast = broadcast[: cfg.ALIAS_LEN], broadcast[cfg.ALIAS_LEN :]
        chain_commit, broadcast = (
            broadcast[: cfg.CHAIN_COMMIT_LEN],
            broadcast[cfg.CHAIN_COMMIT_LEN :],
        )
        indicator, broadcast = (
            broadcast[: cfg.INDICATOR_LEN],
            broadcast[cfg.INDICATOR_LEN :],
        )
    except:
        print("~1")
        raise Exception("broadcast incorrectly formatted")
    try:
        alias = int(alias)
        chain_commit = str(chain_commit)
        indicator = int(indicator)
        parent, message = broadcast[:indicator], broadcast[indicator:]
    except Exception as e:
        try:
            print("~STUFF:")
            print("orig", orig)
            print(alias)
            print(indicator)
            print(parent)
            print(message)
            print(e)
        except:
            raise Exception("broadcast incorrectly formatted")
    return {
        "alias": alias,
        "chain_commit": chain_commit,
        "parent": parent,
        "message": message,
        "signature": signature,
        "sig_image": sig_image,
    }


def calc_bcid(broadcast: str) -> str:
    """
    Returns the broadcast ID of a broadcast
    
    Parameters:
        broadcast (str): The broadcast to be identified
    
    Returns: The hex code of the hash of the encoded broadcast
    """
    body = split_broadcast(broadcast)["sig_image"]
    b_broadcast = body.encode()
    b_hash = hashlib.sha256(b_broadcast)
    return b_hash.hexdigest()


def update_nym(nym: str) -> str:
    if len(nym) <= 20:
        return generate_broadcast(
            f"!update_nym.{nym}", cfg.epoch_chain_commit[cfg.current_epoch], ""
        )

