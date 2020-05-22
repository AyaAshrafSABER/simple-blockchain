import time
from abc import ABC, abstractmethod
from collections import Counter

from typing import TYPE_CHECKING

from chain.block import Block
from chain.blockchain import Blockchain
from util.message.bft import PrepareMessage, CommitMessage

if TYPE_CHECKING:
    from model._bft.bft_context import BFTContext


class BFTState(ABC):
    context: 'BFTContext'

    def __init__(self, context):
        print("***************** ENTERING ", self.__class__.__name__, "********************")
        self.context = context

    @abstractmethod
    def pre_prepare(self, message):
        pass

    @abstractmethod
    def prepare(self, message):
        pass

    @abstractmethod
    def commit(self, message):
        pass

    def verify_block(self, blockchain: Blockchain, block: Block):
        if blockchain.block.block_hash == block.previous_hash:
            return True
        for child in blockchain.block_chain:
            if self.verify_block(child, block):
                return True
        return False


class IdleState(BFTState):
    context: 'BFTContext'

    def __init__(self, context):
        super().__init__(context)
        self.context.pre_prepare_message = None
        self.context.prepare_messages = []
        self.context.commit_messages = []

    def pre_prepare(self, message):
        if self.context.leader:
            print("Invalid pre-prepare message")
            return
        if not self.verify_block(self.context.model.blockchain, message.block):
            return
        self.context.pre_prepare_message = message
        self.context.prepare_messages = []
        self.context.commit_messages = []
        self.context.transition_to(PrePreparedState)
        self.context.model.broadcast_prepare(PrepareMessage(message.block))

    def prepare(self, message):
        print("Invalid prepare message")

    def commit(self, message):
        print("Invalid commit message")


class PrePreparedState(BFTState):
    context: 'BFTContext'

    def __init__(self, context):
        super().__init__(context)
        self.context.prepare_messages = []
        self.faults = 0

    def pre_prepare(self, message):
        raise UnsupportedStateAction

    def prepare(self, message):
        if not self.verify_block(self.context.model.blockchain, message.block):
            self.faults += 1
            if self.faults > self.context.tolerated_faults:
                self.context.transition_to(IdleState)

        self.context.prepare_messages.append(message)
        if self.context.leader and len(self.context.prepare_messages) >= self.context.tolerated_faults + 1:
            self.context.transition_to(PreparedState)
            self.context.model.broadcast_commit(CommitMessage())
        if (not self.context.leader) and len(self.context.prepare_messages) >= self.context.tolerated_faults:
            self.context.transition_to(PreparedState)
            self.context.model.broadcast_commit(CommitMessage())

    def commit(self, message):
        self.context.commit_messages.append(message)


class PreparedState(BFTState):
    context: 'BFTContext'

    def __init__(self, context):
        super().__init__(context)
        if len(self.context.commit_messages) >= self.context.tolerated_faults + 1:
            self.persist()
            self.context.transition_to(IdleState)

    def pre_prepare(self, message):
        raise UnsupportedStateAction

    def prepare(self, message):
        self.context.prepare_messages.append(message)

    def commit(self, message):
        self.context.commit_messages.append(message)
        if len(self.context.commit_messages) >= self.context.tolerated_faults + 1:
            self.persist()
            self.context.transition_to(IdleState)

    def persist(self):
        voted_block = self._majority_vote()
        print("=========================> Majority vote:")
        print(str(voted_block))

        if self.context.leader:
            self.context.model.block_logger.log(time.time() - self.context.model.block_start_time)

        self.context.model.blockchain.add_block(voted_block)
        if self.context.model.mode == 'client':
            self.context.model.maybe_store_output(voted_block)

    def _majority_vote(self):
        blocks = [self.context.pre_prepare_message.block]
        blocks.extend(map(lambda x: x.block, self.context.prepare_messages))
        block_hashes = list(map(lambda x: x.block_hash, blocks))
        most_common_hash, _ = Counter(block_hashes).most_common()[0]
        idx = block_hashes.index(most_common_hash)
        return blocks[idx]


class UnsupportedStateAction(Exception):
    pass
