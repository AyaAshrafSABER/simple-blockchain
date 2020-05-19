import random
from typing import List

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

from client.broadcast_event import BroadcastEvent
from model._bft.bft_context import BFTContext
from model._bft.bft_state import PrePreparedState
from model._broadcast_handler import BroadcastHandler
from model._server_handler import ServerHandler
from util.message.bft import PrePrepareMessage, PrepareMessage, CommitMessage
from util.peer_data import PeerData


class Model:
    active_peers: List[PeerData]
    peer_data: PeerData
    server_handler: ServerHandler
    broadcast_handler: BroadcastHandler
    bft_context: BFTContext

    def __init__(self, peer_data, sk, server_queue, broadcast_queue, peers_database, mode, bft_leader=False):
        self.peer_data = peer_data
        self.server_queue = server_queue
        self.broadcast_queue = broadcast_queue
        self.active_peers = []
        self.server_handler = ServerHandler(self)
        self.broadcast_handler = BroadcastHandler(self)
        self.bft_context = BFTContext(self.active_peers, self, bft_leader)
        if mode == 'client':
            self.sk = sk
            self.pk = serialization.load_pem_public_key(peer_data.pk, backend=default_backend())

    def handle_broadcast_responses(self, message, responses):
        return self.broadcast_handler.handle(message, responses)

    def handle_server_message(self, message):
        return self.server_handler.handle(message)

    def broadcast_pre_prepare(self, message: PrePrepareMessage):
        self.bft_context.transition_to(PrePreparedState)
        self.bft_context.pre_prepare_message = message
        pre_prepare_event = BroadcastEvent(message)
        with pre_prepare_event.condition:
            self.broadcast_queue.put(pre_prepare_event)
            pre_prepare_event.condition.wait()
        print(pre_prepare_event.responses)

    def broadcast_prepare(self, message: PrepareMessage):
        prepare_event = BroadcastEvent(message)
        self.broadcast_queue.put(prepare_event)

    def broadcast_commit(self, message: CommitMessage):
        commit_event = BroadcastEvent(message)
        self.broadcast_queue.put(commit_event)

