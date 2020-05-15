import argparse
import threading
from time import sleep
import grpc
import requests

import blockchain_pb2_grpc
from blockchain_pb2 import PingMsg
from server_thread import ServerThread
import yaml


def parse_args():
    parser = argparse.ArgumentParser(description='Simple blockchain client-server')
    parser.add_argument('mode', type=str, choices=['miner', 'client'], default='miner',
                        help='mode for the client-server to operate in')
    parser.add_argument('-p', '--port', dest='port', default=9980, help='port number for the server')
    parser.add_argument('-pl', '--peers-list', dest='peers_path', default='./peers.yaml',
                        help='peers list yaml file')
    parser.add_argument('-c', '--consensus', dest='algorithm', type=str, choices=['pow', 'bft'], default='pow',
                        help='consensus algorithm to use')
    parser.add_argument('-t', '--transactions', dest='transactions path', default=None,
                        help='path to transactions file to be used. If not provided, random transactions will be '
                             'generated')
    return parser.parse_args()


def get_peers_list(path, self_port):
    peer_dicts = []
    with open(path, 'r') as file:
        peers_yaml = yaml.load(file, Loader=yaml.FullLoader)
        peer_dicts = peers_yaml['peers']

    peers_list = []
    for peer_dict in peer_dicts:
        ip, start_port, count = peer_dict['ip'], peer_dict['start_port'], peer_dict['count']
        peers_list.extend(['%s:%d' % (ip, port) for port in range(start_port, start_port + count)])

    self_ip = requests.get('https://api.ipify.org').text
    # self_ip = '197.135.207.32'
    print(self_ip)
    self_address = self_ip + ':' + str(self_port)

    peers_list.remove(self_address)
    return peers_list


if __name__ == '__main__':
    args = parse_args()
    peers = get_peers_list(args.peers_path, args.port)
    print(peers)
    server_cond = threading.Condition()

    server_thread = ServerThread(args.port, server_cond)
    server_thread.start()

    channels = [grpc.insecure_channel(peer) for peer in peers]
    stubs = [blockchain_pb2_grpc.BlockchainServiceStub(channel) for channel in channels]

    try:
        while True:
            for i in range(len(stubs)):
                stub, peer = stubs[i], peers[i]
                ping_msg = PingMsg(msg="hello")
                print('pinging', peer, ' :', ping_msg.msg)
                try:
                    reply = stub.Ping(ping_msg)
                    print('reply:', reply.msg)
                except grpc._channel._InactiveRpcError as e:
                    print(peer, 'not online')
                    channel = grpc.insecure_channel(peer)
                    stubs[i] = blockchain_pb2_grpc.BlockchainServiceStub(channel)
                sleep(1)
    except KeyboardInterrupt:
        with server_cond:
            server_cond.notify()