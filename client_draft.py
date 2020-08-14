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
confirm_selection_str = "It's your turn. Would you like to select one of those players? if so please send y<selection> for example if you want #10 from that list please send 'y:10'\n"

'''
Controls received events and decides to send acks.
'''

class ServerThread(threading.Thread):
    def __init__(self, port, keyqueue, txqueue, draft, server_addr):
        threading.Thread.__init__(self)
        self.name = 'ServerThread'
        self.txqueue = txqueue
        self.keyqueue = keyqueue
        self.draft = draft

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(server_addr)
        self.sock.settimeout(1)
        out_string = "Socket open on {}! Listening...".format(port)
        self.draft.logger.logg(out_string, 1)
        self.connected = 0

    def run(self):
        while True:
            if self.connected == 0:
                init_string = "init,name={0},pos={1}".format(self.draft.user_name, (self.draft.user_pos + 1))
                self.sock.sendall((init_string + "|").encode())
            try:
                data, addr = self.sock.recvfrom(4096)
                out_string = (strftime("[%H:%M:%S] ",localtime()) + str(data))
                self.draft.acquire()
                self.draft.logger.logg(out_string, 0)
                msgs = data.decode().split("|")
                for msg in msgs:
                    splitter = msg.split(",")
                    if splitter[0] == "sync":
                        selections = []
                        for i in range(1, len(splitter)):
                            selections.append(int(splitter[i]))
                        self.draft.sync_draft(selections, 0)
                        self.keyqueue.put("sync")
                    if splitter[0] == "roster_names":
                        names = []
                        for i in range(1, len(splitter)):
                            if ((i - 1) < self.draft.n_rosters):
                                self.draft.roster[i-1].name = splitter[i]
                    if splitter[0] == "draft_player":
                        player_rank = int(splitter[1], 10)
                        player_idx = self.draft.playeridx_fromrank(player_rank)
                        self.draft.draft_player(player_idx, 1)
                        self.keyqueue.put("sync")

                    if splitter[0] == "error":
                        self.sock.sendall("ack|".encode())
                    if splitter[0] == "draftack":
                        self.sock.sendall("ack|".encode())
                        self.keyqueue.put("draftack")
                    if splitter[0] == "init":
                        if splitter[1] == "success":
                            self.connected = 1
                self.draft.release()
            except socket.timeout:
                pass
            except Exception as ex:
                template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                message = template.format(type(ex).__name__, ex.args)
                print(message)
            while not self.txqueue.empty():
                data = self.txqueue.get()
                self.draft.logger.logg("Sending Thread! {0}".format(data), 0)
                self.sock.sendall((data+"|").encode())
            self.sock.sendall("ping|".encode())


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
                self.parse_input(uIn)
            except EOFError:
                _exit(1)
    def wait_server(self):
        while not self.rxqueue.empty():
            data = self.rxqueue.get()
            if data == "sync":
                self.synced = 1
            if data == "draftack":
                #improve this. 
                self.pick_outcome = "success"
            if data == "error":
                self.pick_outcome = "failure"
        return
    def parse_input(self, uIn):
        draft = self.draft
        if len(uIn) == 0:
            self.state = 0
            return
        if self.state == 0:
            if uIn == "h":
                draft.logger.logg("Input         | Function ", 1)
                draft.logger.logg('1             | Show best available (any position).', 1)
                draft.logger.logg('1:<pos>       | Show best available for supplied position. Example: "1:qb". Valid Positions: qb, rb, wr, te, dst, k.', 1)
                draft.logger.logg("2             | Show your current roster. ", 1)
                draft.logger.logg("2:<draft_pos> | Show roster for the person at supplied draft position.", 1)
                draft.logger.logg("5             | Check my starred players.", 1)
                draft.logger.logg("8             | Show draft information (who is on the clock, when your next turn is, etc.).", 1)
                draft.logger.logg("<fuzzyfind>   | Fuzzy find a players name. Ask the creator for definition of fuzzy find if you want to use this feature.", 1)
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
            elif uIn.startswith("8"):
                draft.print_info(1)
            else:
                if uIn.startswith("y:"):
                    draft.logger.logg("Sorry Incorrect state. Please bring up player menu again.", 1)
                    return

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
                #flush out any sync queues
                while not self.rxqueue.empty():
                    data = self.rxqueue.get()
                self.send_server("draft_player,p_name={0},p_rank={1}".format(name, self.draft.players[player_idx].rank))
                while ((self.synced == 0) and (self.pick_outcome == 0)):
                    self.wait_server()
                draft.logger.logg("turn complete", 0)
            self.state = 0
        else:
            self.state = 0
        return 

    def send_server(self, msg):
        self.txqueue.put_nowait(msg)


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
        bye = 0
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
    threadpool = []

    server_thr = ServerThread(port, keyboard_rxqueue, txqueue, draft, send_address)

    threadpool.append(server_thr)
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
