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

#@note (vburns) this will only work on a windows machine currently due to the winsound requirement

send_address = ("192.168.0.106", 7096)
confirm_selection_str = "It's your turn. Would you like to select one of those players? if so please send y<selection> for example if you want #10 from that list please send 'y10'\n"

'''
Controls received events and decides to send acks.
'''
conn_threads = []
key_thr = None
debug = 0

class ClientThread(threading.Thread):
    def __init__(self, conn, keyqueue, txqueue, draft, addr, index):
        threading.Thread.__init__(self)
        self.keyqueue = keyqueue
        self.txqueue = txqueue
        self.index = index
        self.debug = 0
        self.name = 'ClientThread' + str(index)
        self.draft = draft
        self.sock = conn
        self.addr = addr
        self.initialized = 0
        self.roster = None

        self.ts = None

    def run(self):
        while True:
            try:
                self.ts = time.time()
                data, addr = self.sock.recvfrom(4096)
                #here initialize
                out_string = (strftime("[%H:%M:%S] ",localtime()) + str(data) + " from " + self.name)
                self.draft.logger.logg(out_string, self.debug)
                msgs = (data.decode().split("|"))
                for msg in msgs:
                    splitter = msg.split(",")
                    if (str(splitter[0]) == "init"):
                        self.init_roster(splitter)
                    else:
                        self.handle_msg(splitter)
            except socket.timeout:
                return
            while not self.txqueue.empty():
                data = self.txqueue.get()
                self.sock.sendall((data+"|").encode())
                # except Exception as ex:
                # template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                # message = template.format(type(ex).__name__, ex.args)
                # print(message)
            # print("Recv process time:{0}".format(time.time()-self.ts))
    def handle_msg(self, splitter):
        if (splitter[0] == "draft_player"):
            print(self.draft.current_roster.name, self.roster.name) 
            if ((self.draft.current_roster.name == self.roster.name)):
                print(splitter[1], splitter[2]) 
                if (splitter[1].startswith("p_name=") and splitter[2].startswith("p_rank=")):
                    p_name = splitter[1].split("=",1)[1]
                    p_rank = int(splitter[2].split("=",1)[1], 10)
                    player_idx = 0
                    for player in self.draft.players:
                        if player.name == p_name and player.rank == p_rank:
                            self.draft.acquire()
                            self.draft.draft_player(player_idx, 1)
                            self.draft.release()
                            self.sock.sendall("draftack|".encode())
                            #here
                            sync_up(self.draft)
                            return
                        player_idx += 1
                    self.sock.sendall("error|".encode())
            else:
                self.sock.sendall("error|".encode())

    def init_roster(self, splitter):
        found = 0
        #todo check to make sure this name isn't already being used
        if ((splitter[1].startswith("name=") == False) or \
                (splitter[2].startswith("pos=") == False)):
            return
        r_name = splitter[1].split("=")[1]
        try:
            r_pos = int(splitter[2].split("=")[1], 10)
        except:
            draft.logger.logg("invalid pos", 1)
            return

        self.draft.logger.logg("name:{0}, pos:{1}".format(r_name, r_pos), 1)
        for roster in self.draft.roster:
            if roster.position == r_pos:
                roster.name = r_name
                self.name = r_name
                self.roster = roster
                found = 1
                break

        if found == 1:
            self.sock.sendall("init,success|".encode())
            if len(self.draft.selections):
                sync_str = "sync"
                for i in range(0, len(self.draft.selections)):
                    sync_str += ",{0}".format(self.draft.selections[i])
                self.sock.sendall((sync_str+"|").encode())
        else:
            self.sock.sendall("init,failure|".encode())

class KeyboardThread(threading.Thread):
    def __init__(self, draft, rxqueue):
        threading.Thread.__init__(self)
        self.name = 'KeyboardThread'
        self.draft = draft
        self.rxqueue = rxqueue
        self.state = 0
        self.synced = 0
        self.selected = 0
        self.pick_outcome = 0
        self.ts = time.time()
        self.selections = []

    def run(self):
        while True:
            uIn = input()
            # print("In between execute:{0}".format(time.time()-self.ts))
            try:
                self.ts = time.time()
                self.parse_input(uIn)
            except EOFError:
                _exit(1)
            # print("Keyboard process time:{0}".format(time.time()-self.ts))
            self.ts = time.time()
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
                draft.logger.logg("3  | Revert Pick todo", 1)
                draft.logger.logg("4  | resume draft", 1)
                draft.logger.logg("5  | starred players check", 1)
                draft.logger.logg("6  | roster_addrs", 1)
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
                if ((draft.current_roster.addr == None) or override):
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
            elif uIn.startswith("4"):
                try:
                    file_name = uIn.split(':')[1]
                    draft.resume_draft(file_name)
                except:
                    draft.logger.logg("Invalid file name", 1)
            elif uIn.startswith("5"):
                draft.check_starred()
            elif uIn.startswith("6"):
                for roster in draft.roster:
                    print(roster.name, roster.addr)
            elif uIn.startswith("!de:"):
                try:
                    idx = int(uIn.split(":", 1)[1], 10)
                    if (idx < len(conn_threads)):
                        conn_threads[idx].debug = 1
                        draft.logger.logg("Enabling {0}'s debugs!".format(conn_threads[idx].name), 1)
                except:
                    return
            elif uIn.startswith("!dd:"):
                try:
                    idx = int(uIn.split(":", 1)[1], 10)
                    if (idx < len(conn_threads)):
                        conn_threads[idx].debug = 0
                        draft.logger.logg("Disabling {0}'s debugs!".format(conn_threads[idx].name), 1)
                except:
                    return
            else:
                self.selections = draft.player_fzf(uIn)
                if (len(self.selections) == 0):
                    return
                if ((draft.current_roster.addr == None) or override):
                    draft.logger.logg(confirm_selection_str, 1)
                    self.state = "confirm_selections"
        elif self.state == "confirm_selections":
            name, player_idx = draft.confirm_selection(self.selections, uIn)
            if (name != None) and (player_idx != None):
                self.draft.acquire()
                self.draft.draft_player(player_idx, 1)
                self.draft.release()
                sync_up(self.draft)
            self.state = 0
        else:
            self.state = 0
        return 

def sync_up(draft):
    print("sync_up{0}".format(len(draft.selections)))
    if len(draft.selections):
        sync_str = "sync"
        for i in range(0, len(draft.selections)):
            sync_str += ",{0}".format(draft.selections[i])
        for t in conn_threads:
            print("addr{0}".format(t.addr))
            if (t.is_alive()):
                print("{0}".format(sync_str))
                t.txqueue.put_nowait(sync_str)
            else:
                print (t.is_alive())


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
        lis[11] = lis[11].split('.')[0]
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

    keyboard_rxqueue = Queue()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('',port))
    sock.listen(1)

    key_thr = KeyboardThread(draft, keyboard_rxqueue)

    key_thr.start()
    while True:
        conn, addr = sock.accept()
        draft.logger.logg("New conn! addr:{0}".format(addr), 1)
        q = Queue()
        conn.settimeout(5)
        new_thread = ClientThread(conn, keyboard_rxqueue, q, draft, addr, len(conn_threads))
        new_thread.start()

        conn_threads.append(new_thread)
        i = 0
        deleted = 0

        print("hello")
        while (i < len(conn_threads)):
            if (conn_threads[i].is_alive() == False):
                draft.logger.logg("Dead Thread {0}".format(addr), 1)
                conn_threads[i].sock.close()
                conn_threads.pop(i)
            i += 1
        if deleted:
            i = 0
            while (i < len(conn_threads)):
                conn_threads[i].index = i
        if (key_thr.is_alive() == False):
            _exit(1)

        time.sleep(1)

    _exit(1)
    return

if __name__ == '__main__':
    main()
