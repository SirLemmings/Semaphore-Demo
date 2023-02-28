import sched
import time
import random
from query import Query
import config as cfg
import peers as pr


class Process:
    """
    A class used to track and handle all of the node's open processes
    """

    open_processes = {}

    def __init__(
        self,
        sample_num: int,
        format_query_function,
        conclude_function,
        process_type: str,
        data,
        send_data=False,
        alloted_time=None,
        specific_peers=None,
    ):
        """
        Creates a Process object
        
        Parameters:
            parent (manager object): The manager object that creates the processes # WE'D NEED TO CREATE A PARENT MANAGER CLASS FOR THIS TO BE STRONGLY TYPED - OSCAR
            process_type (str): The type of query (voting_process, time_process, etc.)
            alloted_time (float): The time scheduled before the process will end
        """
        self.format_query_function = format_query_function
        self.conclude_function = conclude_function
        self.alloted_time = alloted_time
        self.process_type = process_type
        self.sample_num = sample_num
        self.open_queries = []
        self.cached_responses = []
        self.peers_responded = {}
        self.data = data
        self.send_data = send_data
        self.specific_peers = specific_peers
        
        if self.alloted_time is not None:
            self.scheduler = sched.scheduler(time.time, time.sleep)
            self.scheduler.enter(self.alloted_time, 0, self.delete)
            self.scheduler.run()

        while True:
            random_number = random.randint(0, 1000000000)
            self.id = str(random_number)+self.process_type
            if self.id not in Process.open_processes.keys():
                break
        Process.open_processes[self.id] = self

        self.create_queries()

    def delete(self):
        del Process.open_processes[self.id]

    def create_queries(self):
        '''create query object for communicating with each peer of process'''
        if self.specific_peers is None:
            peers = cfg.peers.keys()
            sample_num = min(self.sample_num, len(peers))
            peers = random.sample(peers, sample_num)
        else:
            peers = self.specific_peers
        self.sample_num = len(peers)
        if len(peers)==0:
            self.delete()
        for alias in peers:
            self.open_queries.append(
                Query(
                    alias,
                    self.process_type,
                    self,
                    self.format_query_function,
                    self.data,
                    self.send_data,
                    self.alloted_time,
                )
            )

    def process_query(self, query, response):
        '''process the response to a query'''
        if query.peer_alias in self.peers_responded:
            print(f"peer {query.peer_alias} responded more than once")
            pr.remove_peer(query.peer_alias)
            return

        self.peers_responded[query.peer_alias] = response
        if query in self.open_queries:
            self.open_queries.remove(query)
        else:  # the response has returned before self.open_queries appends the query
            sched.scheduler(time.time, time.sleep).enter(
                0.01, 0, self.open_queries.remove, argument=query
            )
        self.cached_responses.append(response)
        if len(self.cached_responses) == self.sample_num:
            self.conclude_function(self)
            self.delete()

