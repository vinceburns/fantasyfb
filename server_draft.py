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
confirm_selection_str = "It's your turn. Would you like to select one of those players? if so please send y:<selection> for example if you want #10 from that list please send 'y:10'\n"

'''
Controls received events and decides to send acks.
'''
conn_threads = []
key_thr = None
debug = 0

class TimerThread(threading.Thread):
    def __init__(self, draft):
        threading.Thread.__init__(self)
        self.draft = draft
        self.warning = 0

    def run(self):
        while True:
            if self.draft.started == 1:
                current_counter = (time.time() - self.draft.turn_ts)
                if ((current_counter >= 120) and (self.warning != 2)):
                    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\r\n\r\n{0} has been on the clock for {1} seconds!\r\n\r\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!".format(self.draft.current_roster.name, int(current_counter)))
                    self.warning = 2
                elif ((current_counter >= 60) and (self.warning == 0)):
                    print("{0} has been on the clock for {1} seconds!".format(self.draft.current_roster.name, int(current_counter)))
                    self.warning = 1
                elif (current_counter <= 10):
                    #assume a pick happend and reset warning state
                    self.warning = 0
            time.sleep(1)


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
        self.error = 0

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
                        self.error = 0
            except socket.timeout:
                self.error += 1
                if self.error == 20:
                    print("THREAD DIED")
                    return
            except Exception as ex:
                template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                message = template.format(type(ex).__name__, ex.args)
                print(message)
                return
            while not self.txqueue.empty():
                data = self.txqueue.get()
                self.sock.sendall((data+"|").encode())
            # print("Recv process time:{0}".format(time.time()-self.ts))
    def handle_msg(self, splitter):
        if (splitter[0] == "draft_player"):
            if ((self.draft.current_roster.name == self.roster.name)):
                if (splitter[1].startswith("p_name=") and splitter[2].startswith("p_rank=")):
                    p_name = splitter[1].split("=",1)[1]
                    p_rank = int(splitter[2].split("=",1)[1], 10)
                    player_idx = 0
                    for player in self.draft.players:
                        if player.name == p_name and player.rank == p_rank:
                            self.draft.acquire(5)
                            self.draft.draft_player(player_idx, 1)
                            self.sock.sendall("draftack|".encode())
                            draft_player(self.draft)
                            self.draft.release()
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
            send_str = "roster_names"
            for i in range(0, self.draft.n_rosters):
                send_str += ",{0}".format(self.draft.roster[i].name)
            self.sock.sendall((send_str+"|").encode())
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
        self.test = 0
        self.pick_outcome = 0
        self.selections = []

    def run(self):
        while True:
            try:
                if self.test == 1:
                    if self.state == 0:
                        uIn = "1"
                    else:
                        uIn = "y:1"
                else:
                    uIn = input()
                self.parse_input(uIn)
            except EOFError:
                _exit(1)
    def parse_input(self, uIn):
        draft = self.draft
        if (draft.acquire(5) == False):
            print("FAILED ACQUIRE!!! GAHHHH!!!")
            _exit(1)

        if draft.done == 1:
            self.state = "Done"
            self.test = 0
        if len(uIn) == 0:
            self.state = 0
            self.draft.release()
            return
        if self.state == 0:
            if uIn == "h":
                draft.logger.logg("help menu\nInput       | Function", 1)
                draft.logger.logg("1           | Print Best available", 1)
                draft.logger.logg("2           | Print Current Roster", 1)
                draft.logger.logg("3           | Revert Pick todo", 1)
                draft.logger.logg("4           | resume draft", 1)
                draft.logger.logg("5           | starred players check", 1)
                draft.logger.logg("6           | roster_addrs", 1)
                draft.logger.logg("7           | force sync", 1)
                draft.logger.logg("8           | Print draft info", 1)
                draft.logger.logg("9           | Print Roster Position Count Chart", 1)
                draft.logger.logg("test        | Enter Test mode", 1)
                draft.logger.logg("!de:connid  | enable debugging", 1)
                draft.logger.logg("!dd:connid  | disabling debugging", 1)
                draft.logger.logg("start fuzzy finding any name to search for a player you would like. See creator for what fuzzy finding means:) (he stole the idea from a vim plugin he uses)", 1)
                self.draft.release()
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
                if draft.started == 0:
                    draft.start_draft()
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
                        self.draft.release()
                        return
                    roster = draft.roster[position - 1]
                except:
                    pass
                roster.print_roster()
            elif uIn.startswith("3"):
                self.draft.revert_pick()
                sync_up(self.draft)
            elif uIn.startswith("4"):
                file_name = uIn.split(':')[1]
                draft.resume_draft(file_name)
                sync_up(self.draft)
            elif uIn.startswith("5"):
                draft.check_starred()
            elif uIn.startswith("6"):
                for roster in draft.roster:
                    print(roster.name, roster.addr)
            elif uIn.startswith("7"):
                sync_up(self.draft)
            elif uIn.startswith("8"):
                draft.print_info(1)
            elif uIn.startswith("9"):
                draft.poscnt_print()
            elif uIn.startswith("test"):
                self.test = 1
            elif uIn.startswith("!de:"):
                try:
                    idx = int(uIn.split(":", 1)[1], 10)
                    if (idx < len(conn_threads)):
                        conn_threads[idx].debug = 1
                        draft.logger.logg("Enabling {0}'s debugs!".format(conn_threads[idx].name), 1)
                except:
                    self.draft.release()
                    return
            elif uIn.startswith("!dd:"):
                try:
                    idx = int(uIn.split(":", 1)[1], 10)
                    if (idx < len(conn_threads)):
                        conn_threads[idx].debug = 0
                        draft.logger.logg("Disabling {0}'s debugs!".format(conn_threads[idx].name), 1)
                except:
                    self.draft.release()
                    return
            else:
                self.selections = draft.player_fzf(uIn)
                if (len(self.selections) == 0):
                    self.draft.release()
                    return
                if ((draft.current_roster.addr == None) or override):
                    draft.logger.logg(confirm_selection_str, 1)
                    self.state = "confirm_selections"
        elif self.state == "confirm_selections":
            name, player_idx = draft.confirm_selection(self.selections, uIn)
            if (name != None) and (player_idx != None):
                self.draft.draft_player(player_idx, 1)
                draft_player(self.draft)
            self.state = 0
        elif self.state == "Done":
            if uIn == "h":
                draft.logger.logg("Draft complete help menu!\nInput       | Function", 1)
                draft.logger.logg("2           | Print Current Roster", 1)
                draft.logger.logg("9           | Print Roster Position Count Chart", 1)
            elif uIn.startswith("2"):
                roster = draft.user_roster
                try:
                    position = int(uIn.split(':')[1], 10)
                    if position >= draft.n_rosters + 1:
                        draft.logger.logg("Invalid roster position", 1)
                        self.draft.release()
                        return
                    roster = draft.roster[position - 1]
                except:
                    pass
                roster.print_roster()
            elif uIn.startswith("9"):
                draft.poscnt_print()
        else:
            self.state = 0
        self.draft.release()
        return 

def sync_up(draft):
    if len(draft.selections):
        sync_str = "sync"
        for i in range(0, len(draft.selections)):
            sync_str += ",{0}".format(draft.selections[i])
        for t in conn_threads:
            if (t.is_alive()):
                print(sync_str)
                t.txqueue.put_nowait(sync_str)
            else:
                pass

def draft_player(draft):
    if len(draft.selections):
        sync_str = "draft_player"
        sync_str += ",{0}".format(draft.selections[len(draft.selections)-1])
        for t in conn_threads:
            if (t.is_alive()):
                t.txqueue.put_nowait(sync_str)
            else:
                pass


def player_generate_fromcsv(line):
    starred = 0
    if line == "":
        return None
    lis = line.strip().split(",")
    print(lis)
    
    for idx in range(0, len(lis)):
        lis[idx] = lis[idx].replace("\"", "").replace("\n", "")
    rank = int(lis[0], 10)
    try:
        position = lis[4]
        uppers = [l for l in position if l.isupper()]
        position = "".join(uppers)
        while (len(position) < 3):
            position += " "
    except:
        print("position")
        return
    name = lis[2]
    team = lis[3]
    while (len(team) < 3):
        team += " "
    try:
        bye = int(lis[5], 10)
    except:
        bye = 0
    try:
        adp_diff = int(lis[7], 10)
        adp = rank + adp_diff
    except:
        adp = rank
    try:
        sos = int(lis[6][0])
    except:
        sos = 0
    try:
        posrank = lis[4]
    except:
        posrank = "unk"
    try:
        tier = int(lis[1])
    except:
        tier = 0
    player = Player(position, rank, name, team, bye, adp, starred, posrank, tier, sos)
    return player

def main():
    players = []
    player_csv = "FantasyPros_2020_Draft_Overall_Rankings.csv"
    position = 6
    user_name = "vinny"
    n_rosters = 8
    names = []
    for i in range(0, 14):
        names.append("comp{0}".format(i))
    with open("server_cfg.cfg",'r') as f:
        for line in f:
            if line.startswith("CSVFILE"):
                player_csv = line.split("=", 1)[1].strip()
            elif line.startswith("PORT"):
                port = int(line.split("=", 1)[1], 10)
            elif line.startswith("DRAFTPOSITION"):
                position = int(line.split("=", 1)[1], 10)
            elif line.startswith("N_TEAMS"):
                n_rosters = int(line.split("=", 1)[1], 10)
            elif line.startswith("USER_NAME"):
                user_name = line.split("=", 1)[1].strip()
            elif line.startswith("TEAM_NAME"):
                stuff = line.split("=", 1)[1].strip()
                roster_position = int(stuff.split(",", 1)[0], 10)
                name = stuff.split(",", 1)[1]
                names[roster_position] = name
            elif line.startswith("SERVER_ADDRESS"):
                ip = line.split("=", 1)[1].split(",", 1)[0].strip()
                send_port = int(line.split("=", 1)[1].split(",", 1)[1], 10)
                send_address = (ip, send_port)

    with open(player_csv,'r') as f:
        count = 0
        f.__next__()
        for line in f:
            if count < 10:
                print(line)
            if count > 180:
                break
            player = player_generate_fromcsv(line)
            if player != None:
                players.append(player)
                count += 1
            else:
                print(error)


    draft = Draft(position, user_name, players, n_rosters, player_csv)
    for i in range(0, draft.n_rosters):
        if i != draft.user_pos:
            draft.roster[i].name = names[i]

    keyboard_rxqueue = Queue()
    print(f"port:{port}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5) 
    sock.bind(('',port))
    sock.listen(1)

    key_thr = KeyboardThread(draft, keyboard_rxqueue)
    timer_thread = TimerThread(draft)

    key_thr.start()
    timer_thread.start()
    while True:
        try:
            conn, addr = sock.accept()
            draft.logger.logg("New conn! addr:{0}".format(addr), 1)
            q = Queue()
            conn.settimeout(5)
            new_thread = ClientThread(conn, keyboard_rxqueue, q, draft, addr, len(conn_threads))
            new_thread.start()

            conn_threads.append(new_thread)
        except socket.timeout:
            pass
        i = 0
        deleted = 0

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
            print("Keyboard Thread Died!!")
            _exit(1)

        time.sleep(1)

    _exit(1)
    return

if __name__ == '__main__':
    main()
