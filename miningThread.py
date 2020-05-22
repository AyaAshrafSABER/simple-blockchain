import threading
import time
from time import sleep
from typing import TYPE_CHECKING

from chain.block import Block
from util.helpers import CHAIN_SIZE, DIFFICULTY_LEVEL

if TYPE_CHECKING:
    from model import Model


class MiningThread(threading.Thread):

    def __init__(self, model: 'Model'):
        super(MiningThread, self).__init__()
        self.__model = model
        self.__stop_event = threading.Event()
        self.__transactions = []
        self.__prev_hash = ""
        self.__diff = DIFFICULTY_LEVEL
        # self.__block = None

    # def set_data(self, transactions, prev_block_hash, difficulty):
    #     self.__transactions = transactions
    #     self.__prev_hash = prev_block_hash
    #     self.__diff = difficulty

    # def get_block(self):
    #     return self.__block

    def stop(self):
        self.__stop_event.set()

    def stopped(self):
        return self.__stop_event.is_set()

    def run(self):
        start_time = time.time()

        self.__transactions = self.__model.unconfirmed_tx_pool[0:CHAIN_SIZE]
        self.__prev_hash = self.__model.blockchain.get_head_of_chain().block.block_hash
        pow_found = False
        nonce = 0
        block = None
        while not pow_found:
            if self.stopped():
                break
            block = Block(transactions=self.__transactions, previous_hash=self.__prev_hash, nonce=nonce)
            if block.hash_difficulty() == self.__diff:
                pow_found = True
            nonce += 1

        if pow_found:
            self.__model.unconfirmed_tx_pool[0:CHAIN_SIZE] = []
            self.__model.blockchain.add_block(block)
            self.__model.broadcast_new_block(block)

            self.__model.block_logger.log(time.time() - start_time)

            print(str(block))
            # TODO: broadcast new block
            # self.__model.verify_block(block)
