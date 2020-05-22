import argparse
import pickle
import socket
import threading
from queue import Queue
from time import sleep
import requests
import yaml
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

import model
from client.broadcast_event import BroadcastEvent
from client.client_dispatcher import ClientDispatcher
from model._bft.bft_state import PrePreparedState
from model._transaction_generator import TransactionGenerator
from server.server_dispatcher import ServerDispatcher
from server.server_thread import ServerThread
from util.logger import Logger
from util.message.advertise_self_message import AdvertiseSelfMessage
from util.message.bft import PrePrepareMessage
from util.message.ping_message import PingMessage
from util.peer_data import PeerData

def parse_args():
    parser = argparse.ArgumentParser(description='Simple blockchain client-server')
    parser.add_argument('-p', '--port', dest='port', type=int, default=9980, help='port number for the server')
    parser.add_argument('-pl', '--peers-list', dest='peers_path', default='./peers.yaml',
                        help='peers list yaml file')
    parser.add_argument('-c', '--consensus', dest='algorithm', type=str, choices=['pow', 'bft'], default='pow',
                        help='consensus algorithm to use')
    parser.add_argument('-t', '--transactions', dest='transactions path', default=None,
                        help='path to transactions file to be used. If not provided, random transactions will be '
                             'generated')
    return parser.parse_args()


def process_peer_configs():
    peer_dicts = []
    with open(args.peers_path, 'r') as file:
        peers_yaml = yaml.load(file, Loader=yaml.FullLoader)
        peer_dicts = peers_yaml['peers']

    peers_list = []
    all_peers_list = []
    found_self = False
    for peer_dict in peer_dicts:
        ip = peer_dict['ip']
        for peer_info in peer_dict['peers']:
            peer_data = PeerData(ip + ':' + str(peer_info['port']))
            if peer_info['type'] == 'client':
                peer_data.pk = key_pairs_database[peer_info['key-pair-id']]['pk']
            if peer_info['port'] == args.port and ip == self_ip:  # This is me!
                found_self = True
                my_self_peer_data = peer_data
                my_bft_leader = 'bft-leader' in peer_info and peer_info['bft-leader']

                if peer_info['type'] == 'client':
                    skb = key_pairs_database[peer_info['key-pair-id']]['sk']
                    my_sk = serialization.load_pem_private_key(skb, password=b'password', backend=default_backend())
                else:
                    my_sk = None
                self_mode = peer_info['type']
                all_peers_list.append(peer_data)
                continue
            peers_list.append(peer_data)
            all_peers_list.append(peer_data)

    return peers_list, my_self_peer_data, self_mode, my_bft_leader, my_sk, all_peers_list


def server_address():
    return self_ip + ':' + str(args.port)


if __name__ == '__main__':
    self_ip = requests.get('https://api.ipify.org').text
    print(self_ip)

    args = parse_args()
    key_pairs_database = pickle.load(open("key_pairs", "rb"))
    peers_data, self_peer_data, mode, bft_leader, sk, all_peers_data = process_peer_configs()

    peers_address_database = list(map(lambda x: x.address, peers_data))
    print(peers_address_database)

    # Logger.type = mode
    Logger.port = args.port
    Logger.dir = 'logs/'

    BUF_SIZE = 100
    server_queue = Queue(BUF_SIZE)
    broadcast_queue = Queue(BUF_SIZE)
    model = model.Model(self_peer_data, sk, server_queue, broadcast_queue, all_peers_data, mode, bft_leader, args.algorithm)

    server_thread = ServerThread(args.port, server_queue)
    server_dispatcher = ServerDispatcher(server_queue, model)

    server_thread.setDaemon(True)
    server_thread.start()
    server_dispatcher.setDaemon(True)
    server_dispatcher.start()

    client_dispatcher = ClientDispatcher(broadcast_queue, model)
    client_dispatcher.setDaemon(True)
    client_dispatcher.start()

    advertise_event = BroadcastEvent(AdvertiseSelfMessage(model.peer_data), peers=peers_address_database)
    with advertise_event.condition:
        broadcast_queue.put(advertise_event)
        advertise_event.condition.wait()

    if mode == 'client':
        tx_gen = TransactionGenerator(model)
        tx_gen.start()

    # while bft_leader:
    #     print("sad")
    #     # msg = input("Enter message: ")
    #     # if msg == '':
    #     #     continue
    #     # advertise_event = BroadcastEvent(PingMessage(msg))
    #     #
    #     # with advertise_event.condition:
    #     #     broadcast_queue.put(advertise_event)
    #     #     advertise_event.condition.wait()
    #     if len(model.active_peers) == 3:
    #         model.broadcast_pre_prepare(PrePrepareMessage("hello"))
    #         sleep(5)
    #         model.broadcast_pre_prepare(PrePrepareMessage("hello 2"))
    #         break

    while True:
        sleep(3600)
    # while True:
    #     print('yay')
    #     sleep(5)
