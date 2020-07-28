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

    def run(self):
        while True:
            while not self.queue.empty():
                data = self.queue.get()
                self.draft.logger.logg("Sending Thread! {0}".format(data), 1)
                self.sock.sendto(data.encode(), self.send_addr)
            time.sleep(1)


class ReceiverThread(threading.Thread):
    def __init__(self, port, keyqueue, txqueue, draft):
        threading.Thread.__init__(self)
        self.keyqueue = keyqueue
        self.name = 'ReceiverThread'
        self.txqueue = txqueue
        self.draft = draft

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(1)
        self.sock.settimeout(10)
        self.sock.bind(('',port))
        out_string = "Socket open on {}! Listening...".format(port)
        self.draft.logger.logg(out_string, 1)
        self.connected = 0

    def run(self):
        while True:
            if self.connected == 0:
                init_string = "init,name={0},pos={1}".format(self.draft.user_pos, self.draft.user_name)
                self.txqueue.put_nowait(init_string)
                self.draft.logger.logg("init put!", 1)
            try:

                data, addr = self.sock.recvfrom(4096)
                data = str(data)
                out_string = (strftime("[%H:%M:%S] ",localtime()) + str(data) + " from " + str(addr[0]) + ":" + str(addr[1]))
                self.draft.acquire()
                self.draft.logger.logg(out_string, 1)
                splitter = data.split(",")
                if splitter[0] == "sync":
                    selections = []
                    for i in range(1, len(splitter)):
                        selections = int(splitter[i])
                    self.draft.sync_draft(selections)
                    self.keyqueue.put_nowait("sync")
                if splitter[0] == "error":
                    self.keyqueue.put_nowait(data)
                    self.send_server("ack")
                if splitter[0] == "draftack":
                    self.keyqueue.put_nowait(data)
                    self.send_server("ack")
                if splitter[0] == "init":
                    if splitter[1] == "success":
                        self.connected = 1
                self.draft.release()
            except socket.timeout:
                out_string = "timeout exception"
                self.draft.logger.logg(out_string, 1)
            except Exception as ex:
                template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                message = template.format(type(ex).__name__, ex.args)
                print(message)

    def send_server(self, msg):
        self.txqueue.put_nowait("{0},{1},{2}".format(self.draft.user_roster.name, self.draft.user_roster.pos, msg))

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
        self.selections = []
        self.my_turn = False

    def run(self):
        while True:
            try:
                uIn = input()
                if uIn:
                    self.parse_input(uIn)
            except EOFError:
                _exit(1)
            except TimeoutExpired:
                pass
    def wait_server(self):
        while not self.rxqueue.empty():
            data = self.rxqueue.get()
            if data == "sync":
                self.synced = 1
            if data == "draftack":
                #improve this. 
                self.draft.logger.logg("Congrats you drafted the player you wanted.", 1)
                self.pick_outcome = "success"
            if data == "error":
                self.pick_outcome = "failure"
            self.rxqueue.task_done()
        return
    def parse_input(self, uIn):
        draft = self.draft
        print("self.state:{0}len:{1}".format(self.state, len(uIn)))
        if len(uIn) == 0:
            self.state = 0
            return
        if self.state == 0:
            if uIn == "h":
                draft.logger.logg("help menu\nInput | Function|", 1)
                draft.logger.logg("1  | Print Best available", 1)
                draft.logger.logg("2  | Print Current Roster", 1)
                draft.logger.logg("5  | starred players check", 1)
                draft.logger.logg("start fuzzy finding any name to search for a player you would like. See creator for what fuzzy finding means:) (he stole the idea from a vim plugin he uses)", 1)
                return
            elif uIn.startswith("1"):
                try:
                    position = uIn.split(':')[1]
                except:
                    position = None
                self.selections = draft.show_topavail(position)
                if draft.my_turn():
                    draft.logger.logg(confirm_selection_str, 1)
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
            elif uIn.startswith("5"):
                draft.check_starred()
            else:
                self.selections = draft.player_fzf(uIn)
                if (len(self.selections) == 0):
                    return
                if draft.my_turn():
                    draft.logger.logg(confirm_selection_str, 1)
                    self.state = "confirm_selections"
        elif self.state == "confirm_selections":
            name, player_idx = draft.confirm_selection(self.selections, uIn)
            if (name != None) and (player_idx != None):
                self.synced = 0
                self.pick_outcome = 0
                self.send_server("draft_player,p_name={0},p_rank={1}".format(name, self.draft.players[player_idx].rank))
                while ((self.synced == 0) and (self.pick_outcome == 0)):
                    self.wait_server()
                    if self.pick_outcome == "success":
                        draft.logger.logg("Congrats you draft the player you wanted", 1)
                        draft.logger.logg("waiting sync", 1)
                    if self.pick_outcome == "failure":
                        draft.logger.logg("Error :( Vince can't write code", 1)
                        draft.logger.logg("waiting sync", 1)
                        self.synced = 0
                draft.logger.logg("turn complete", 1)
        else:
            self.state = 0
        return 

    def send_server(self, msg):
        self.txqueue.put_nowait("{0},{1},{2}".format(self.draft.user_roster.name, self.draft.user_roster.pos, msg))


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
        adp = int(lis[11], 10)
    except ValueError:
        adp = "No data"
    if len(lis) >= 14:
        try:
            starred = int(lis[13], 10)
        except ValueError:
            starred = 0
    else:
        starred = 0
    player = Player(position, rank, name, team, bye, adp, starred)
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
    except KeyboardInterrupt:
        _exit(1)
    return

if __name__ == '__main__':
    main()
