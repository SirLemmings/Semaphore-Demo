Welcome to the proof-of-concept implementation for Semaphore.

To run a node on your local network, run node.py

Enter alias (numerical) when prompted. Enter network port when prompted.

Connecting to other nodes (in your local network) via the "connect" command will allow your node to connect with another node. You will have to provide the peer's alias, ip address, and port number, which are provided when the node is initialized.

Connected nodes will send test mesages each second and will save blocks to a file with the alias as its name.

To initialize a node the "activate" command should be used if the node is starting the blockchain from scratch or has no peers. To activate a node that is connected to at least one peer, the "init" command should be used.

Anything written to the terminal will be broadcasted unless it is a command.

Full list of commands is:

"connect": establish a symetric connection with a peer
"see_peers": show all peer aliases
"see_peers_active": show all activated peer aliases
"see_peers_sockets": show all peer sockets
"chat": send a message to the console of a peer
"remove": disconnect from a peer
"exit": elegantly close the node
"time_sync": update and display network time
"init": initialize/activate a node with peers
"activate": bootstrap network without peers

Beware of bugs.
