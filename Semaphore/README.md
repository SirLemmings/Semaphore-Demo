# Welcome to the proof-of-concept implementation for Semaphore

## Running a node
Dependencise can be installed by running:

    pip install -r requirements.txt

To run a node on your local network, run node.py

Enter alias (numerical) when prompted. Enter network port and ip when prompted.

When running nodes on local host:
    Leave ip address blank
    easiest to set alias n's port to nnnn
    for n 1-9

Connecting to other nodes (in your local network) via the "connect" command will allow your node to connect with another node. You will have to provide the peer's alias, ip address, and port number, which are provided when the node is initialized.

Connected nodes configured by default to send test mesages each epoch and will save blocks to a file with the alias as its name.

To initialize a node the "activate" command should be used if the node is starting the blockchain from scratch or has no peers. To activate a node that is connected to at least one peer, the "init" command should be used.

Anything written to the terminal will be broadcasted unless it is a command.

If you want to restart the network from scratch, you must manually delete each alias' directory

Full list of commands is:

    "connect": establish a symetric connection with a peer
    
    "fc": fast connect to all peers 1-9 with alias and port in the format n, nnnn
    
    "see_peers": show all peer aliases
    
    "see_peers_active": show all activated peer aliases
    
    "see_peers_sockets": show all peer sockets
    
    "chat": send a message to the console of a peer
    
    "remove": disconnect from a peer
    
    "exit": elegantly close the node
    
    "init": initialize/activate a node with peers
    
    "activate": bootstrap network without peers

## Blockchain parameters can be changed by editing params.json

Parameters that you may want to change are:

    "TIME_BASE_OFFSET": constant shift to local time
    
    "EPOCH_TIME": length of time of an epoch
    
    "VOTE_INIT_CONF": initial confidence in favor of broadcast
    
    "VOTE_INIT_CONF_NEG": initial confidence against broadcast
    
    "VOTE_SAMPLE_NUM": number of peers sampled in each vote round
    
    "VOTE_CONSENSUS_LEVEL": number of sampled peers that must agree to update confidence
    
    "VOTE_CERTAINTY_LEVEL": confidence value lock-in
    
    "VOTE_ROUND_TIME": time between vote rounds
    
    "SLACK_EPOCHS": number of epochs following true epoch when message will be accepted
    
    "VOTE_MAX_EPOCHS": number of epochs for epoch vote to occur
    
    "MINIMUM_REORG_DEPTH": minimum depth of fork before evaluating reorg

## Node configuration can be changed by editing config.json

Configurations you amy want to change are:
    
    "ENABLE_MANUAL_BC": allows user to submit broadcasts
    
    "SEND_TEST_BC": makes node send broadcast each epoch automatically
    
    "RANDOM_DELAY": add random latancy to initial relay (WARNING: THIS WILL CAUSE PROBLEMS AFTER RUNNING FOR A FEW MIN)
    
    "SHOW_RELAYS": display bcid's of broadcasts when seen in initial relay
    
    "SHOW_BLOCK_INFO": print the block hash of each epoch
    
    "SHOW_EPOCH_INFO": print the timestamp for each epoch
    
    "SHOW_SEEN_CONF_BC": show broadcasts before and after epoch vote
    
    "SHOW_VOTE_CONFS": show the confidences for each bcid for each round of voting

## BEWARE OF BUGS

This is a basic prototype, not a production system

have fun :)
