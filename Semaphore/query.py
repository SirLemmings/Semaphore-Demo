import sched
import time
import random
import communications as cm
import peers as pr


class Query:
    """
    A class used to track and handle all of the node's open queries
    
    """

    open_queries = {}

    def __init__(
        self,
        peer_alias: int,
        query_type: str,
        parent_process,
        format_query_function,
        data,
        send_data,
        alloted_time=None,
    ):
        """
        Creates a Query object
        
        Parameters:
            peer_alias (int): The alias of the peer to be queried
            query_type (str): The type of query (vote_request, time_request, etc.)
            parent_process (Process): The parent process of the query
            parent_node (Node): The node that is parent of everything
            alloted_time (float): The time scheduled before the query will be destroyed
        """
        self.parent_process = parent_process
        self.peer_alias = peer_alias
        self.alloted_time = alloted_time
        self.response = None
        self.type = query_type
        self.format_query_function = format_query_function
        self.data = data
        self.send_data = send_data
        if self.alloted_time is not None:
            self.scheduler = sched.scheduler(time.time, time.sleep)
            self.scheduler.enter(time.time, 0, self.delete)
            self.scheduler.run()

        while True:
            random_number = random.randint(0, 1000000000)
            self.id = str(random_number) + self.type
            if self.id not in Query.open_queries.keys():
                break

        Query.open_queries[self.id] = self
        self.send_query()

    def delete(self):
        del Query.open_queries[self.id]

    def send_query(self):
        """send message to peer with info for query"""
        if self.send_data:
            cm.send_peer_message(self.peer_alias, f"{self.type}|{self.id}|{self.data}")
        else:
            cm.send_peer_message(self.peer_alias, f"{self.type}|{self.id}")

    def process_query_response(self, response: str, peer_alias: int):
        """process validate and format the response to query before sending to parent process"""
        if peer_alias != self.peer_alias:
            print(f"{peer_alias} is incorrect alias")
            pr.remove_peer(peer_alias)
        try:
            formatted_response = self.format_query_function(self, response)
        except Exception as e:
            print("errr", e)
            print("type", self.type)
            print("func", self.format_query_function)
            print("response formatted incorrectly")
            pr.remove_peer(peer_alias)
            return
        self.parent_process.process_query(self, formatted_response)
        self.delete()
