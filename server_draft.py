import socket
from os import fsync,system,_exit
from time import strftime,localtime,sleep
import sys
import threading
import select
from multiprocessing import *
from draft import Draft
from roster import Roster
from player import Player
import msvcrt
import time


send_address = ("192.168.0.106", 7096)
confirm_selection_str = "It's your turn. Would you like to select one of those players? if so please send y<selection> for example if you want #10 from that list please send 'y10'\n"

'''
Controls received events and decides to send acks.
'''

class SendingThread(threading.Thread):
    def __init__(self, sock, queue, draft, send_addr):
        threading.Thread.__init__(self)
        self.name = 'SendingThread'
        self.sock = sock
        self.queue = queue
        self.draft = draft
        self.send_addr = send_addr
        self.ts = None

    def run(self):
        while True:
            self.ts = time.time()
            while not self.queue.empty():
                data, addr = self.queue.get()
                self.sock.sendto(data.encode(), addr)
                self.queue.task_done()
            # print("Send process time:{0}".format(time.time()-self.ts))
            time.sleep(.5)


class ReceiverThread(threading.Thread):
    def __init__(self, port, keyqueue, txqueue, draft):
        threading.Thread.__init__(self)
        self.keyqueue = keyqueue
        self.name = 'ReceiverThread'
        self.txqueue = txqueue
        self.draft = draft

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(0)
        self.sock.settimeout(3)
        self.sock.bind(('',port))
        out_string = "Socket open on {}! Listening...".format(port)
        self.draft.logger.logg(out_string, 1)
        self.connected = 0
        self.ts = None

    def run(self):
        while True:
            try:
                self.ts = time.time()
                data, addr = self.sock.recvfrom(4096)
                data = str(data)
                out_string = (strftime("[%H:%M:%S] ",localtime()) + str(data) + " from " + str(addr[0]) + ":" + str(addr[1]))
                self.draft.logger.logg(out_string, 1)
                splitter = data.split(",")
                #@todo (vburns) move all of these strings to defines that client and server can share
                if splitter[0] == "init":
                    self.init_roster(splitter, addr)
                else:
                    self.handle_msg(splitter, addr)
            except socket.timeout:
                pass
            # except Exception as ex:
                # template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                # message = template.format(type(ex).__name__, ex.args)
                # print(message)
            # print("Recv process time:{0}".format(time.time()-self.ts))
    def handle_msg(self, splitter, addr):
        if splitter[0] == "draft_player":
            r_name = splitter[1]
            r_pos = splitter[2]
            if (self.draft.current_roster.name == r_name) and \
                splitter[3].startswith("p_name=") and splitter[4].startswith("p_rank=") and \
                addr == self.current_roster.addr:
                p_name = splitter[3].split("=",1)[1]
                p_rank = splitter[4].split("=",1)[1]
                player_idx = 0
                for player in self.draft.players:
                    if player.name == p_name and player.rank == p_rank:
                        self.draft.draft_player(player_idx)
                if player_idx == len(self.draft.players):
                    self.txqueue.put_nowait("error",addr)
                else:
                    self.txqueue.put_nowait("draftack",addr)
                    self.sync_up(self.draft, self.txqueue)
            else:
                self.txqueue.put_nowait("error",addr)

    def init_roster(self, splitter, addr):
        found = 0
        #todo check to make sure this name isn't already being used
        for roster in self.draft.roster:
            if roster.pos == pos:
                roster.address = addr
                roster.name = name
                found = 1
                break
        if found == 1:
            self.txqueue.put_nowait("init,success", addr)
            if len(self.draft.selections):
                sync_str = "sync"
                for i in range(0, len(self.draft.selections)):
                    sync_str += ",{0}".format(self.draft.selections[i])
                self.txqueue.put_nowait(sync_str, addr)
        else:
            self.txqueue.put_nowait("init,failure", addr)

class KeyboardThread(threading.Thread):
    def __init__(self, draft, txqueue, rxqueue):
        threading.Thread.__init__(self)
        self.name = 'KeyboardThread'
        self.draft = draft
        self.rxqueue = rxqueue
        self.txqueue = txqueue
        self.state = 0
        self.synced = 0
        self.selected = 0
        self.pick_outcome = 0
        self.ts = time.time()
        self.selections = []

    def run(self):
        while True:
            try:
                uIn = input()
                # print("In between execute:{0}".format(time.time()-self.ts))
                self.ts = time.time()
                if uIn:
                    self.parse_input(uIn)
            except EOFError:
                _exit(1)
            # print("Keyboard process time:{0}".format(time.time()-self.ts))
            self.ts = time.time()
    def parse_input(self, uIn):
        draft = self.draft
        print("self.state:{0}".format(self.state))
        if self.state == 0:
            if uIn == "h":
                draft.logger.logg("help menu\nInput | Function|", 1)
                draft.logger.logg("1  | Print Best available", 1)
                draft.logger.logg("2  | Print Current Roster", 1)
                draft.logger.logg("3  | Revert Pick todo", 1)
                draft.logger.logg("4  | resume draft", 1)
                draft.logger.logg("start fuzzy finding any name to search for a player you would like. See creator for what fuzzy finding means:) (he stole the idea from a vim plugin he uses)", 1)
                return
            elif uIn.startswith("1"):
                override = 0
                try:
                    position = uIn.split(':')[1]
                    try:
                        override = int(uIn.split(':')[2], 10)
                    except:
                        pass
                except:
                    position = None
                self.selections = draft.show_topavail(position)
                draft.logger.logg(confirm_selection_str, 1)
                if ((draft.current_roster.addr == None) or override):
                    self.state = "confirm_selections"
            elif uIn.startswith("2"):
                roster = draft.user_roster
                try:
                    position = int(uIn.split(':')[1], 10)
                    if position >= draft.n_rosters + 1:
                        draft.logger.logg("Invalid roster position", 1)
                        return
                    roster = draft.roster[position - 1]
                except:
                    pass
                roster.print_roster()
            elif uIn.startswith("4"):
                try:
                    file_name = uIn.split(':')[1]
                    draft.resume_draft(file_name)
                except:
                    draft.logger.logg("Invalid file name", 1)

        elif self.state == "confirm_selections":
            name, player_idx = draft.confirm_selection(self.selections, uIn)
            if (name != None) and (player_idx != None):
                self.draft.draft_player(player_idx)
            self.state = 0
        return 

    def send_server(self, msg):
        self.txqueue.put_nowait("{0},{1}".format(self.draft.user_name, msg))

def sync_up(draft, txqueue):
    if len(draft.selections):
        sync_str = "sync"
        for i in range(0, len(draft.selections)):
            sync_str += ",{0}".format(draft.selections[i])
        for roster in self.draft.rosters:
            if roster.addr != None:
                self.txqueue.put_nowait(sync_str, roster.addr)


def player_generate_fromcsv(line):
    if line == "":
        return None
    lis = line.replace("\"", "").split(",")
    try:
        rank = int(lis[0], 10)
    except:
        return
    try:
        position = lis[5]
        uppers = [l for l in position if l.isupper()]
        position = "".join(uppers)
        while (len(position) < 3):
            position += " "
    except:
        return
    name = lis[3]
    team = lis[4]
    while (len(team) < 3):
        team += " "
    try:
        bye = int(lis[6], 10)
    except:
        bye = None
    try:
        adp = lis[11].split('.')[0]
    except IndexError:
        #unlucky see if it is not a float
        pass
    try:
        adp = int(adp, 10)
    except ValueError:
        adp = "No data"
    player = Player(position, rank, name, team, bye, adp)
    return player


def main():
    players = []
    player_csv = "FantasyPros_2020_Draft_Overall_Rankings.csv"
    position = 6
    name = "vinny"
    n_rosters = 8
    with open("user_cfg.cfg",'r') as f:
        for line in f:
            if line.startswith("CSVFILE"):
                player_csv = line.split("=", 1)[1].strip()
            elif line.startswith("PORT"):
                port = int(line.split("=", 1)[1], 10)
            elif line.startswith("DRAFTPOSITION"):
                position = int(line.split("=", 1)[1], 10)
            elif line.startswith("N_TEAMS"):
                n_rosters = int(line.split("=", 1)[1], 10)
            elif line.startswith("TEAM_NAME"):
                name = line.split("=", 1)[1].strip()
            elif line.startswith("SERVER_ADDRESS"):
                ip = line.split("=", 1)[1].split(",", 1)[0].strip()
                send_port = int(line.split("=", 1)[1].split(",", 1)[1], 10)
                send_address = (ip, send_port)

    with open(player_csv,'r') as f:
        f.__next__()
        for line in f:
            player = player_generate_fromcsv(line)
            if player != None:
                players.append(player)

    draft = Draft(position, name, players, n_rosters, player_csv)

    txqueue = Queue()
    keyboard_rxqueue = Queue()

    receive_thr = ReceiverThread(port, keyboard_rxqueue, txqueue, draft)
    threadpool = []
    threadpool.append(receive_thr)
    send_thr = SendingThread(receive_thr.sock, txqueue, draft, send_address)
    threadpool.append(send_thr)
    key_thr = KeyboardThread(draft, txqueue, keyboard_rxqueue)

    threadpool.append(key_thr)

    for t in threadpool:
        t.start()
    alive = True
    try:
        while alive:
            for t in threadpool:
                if not t.is_alive():
                    try:
                        print(t.name + " has died! Exiting.")
                    except:
                        _exit(1)
                    _exit(1)
                    alive = False
                if draft.done == 1:
                    print("Draft complete!")
                    alive = False
                    _exit(1)

    except KeyboardInterrupt:
        _exit(1)
    return

if __name__ == '__main__':
    main()
