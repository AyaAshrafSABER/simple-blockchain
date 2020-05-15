import time
from concurrent.futures.thread import ThreadPoolExecutor
from threading import Thread

import grpc
import blockchain_pb2_grpc
from blockchain_servicer import BlockchainServicer
from blockchain_pb2 import PongMsg, PingMsg


class ServerThread(Thread):

    def __init__(self, port, cond, max_workers=10):
        super().__init__()
        self.cond = cond
        self.server = grpc.server(ThreadPoolExecutor(max_workers=max_workers))
        blockchain_pb2_grpc.add_BlockchainServiceServicer_to_server(BlockchainServicer(), self.server)
        self.server.add_insecure_port('0.0.0.0:' + str(port))

    def run(self):
        self.server.start()
        with self.cond:
            self.cond.wait()
        print("================== Stopping server gracefuly ====================")
        self.server.stop(0)
        # try:
        #     while True:
        #         time.sleep(60 * 60 * 24)
        # except KeyboardInterrupt:
        #     print("================== Stopping Server ====================")
        #     self.server.stop(0)
