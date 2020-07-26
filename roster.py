
import sys
import time
from os import fsync,system,_exit
import draftlogging
from defines import Defines as defs
from player import Player

prepend_printlist = ["QB:    | ", "RB1:   | ", "RB2:   | ", "WR1:   | ",\
        "WR2:   | ", "TE:    | ", "FLEX:  | ", "DST:   | ", "K:     | ",\
        "BENCH: | "]

class Roster():
    def __init__(self, position, name, player_csv, logger):
        self.position = position
        self.name = name
        self.max_bench = 7
        self.bench = []
        self.player_list = []
        #see enum at top of file.
        self.sorted_playerlist = []
        self.max_players = 16
        self.logger = logger
        self.b_idx = defs.PLAYERSTATUS_BENCH
        self.rosterfile = "rosters/%d_roster.ros"%(self.position)
        self.player_csv = player_csv
        with open(self.player_csv,'r') as f:
            self.logger.logg("able to open file", 0)
        dummy = "Empty"
        for i in range(0, self.max_players):
            self.sorted_playerlist.append(dummy)
        self.address = None
    def fill_in(self):
        #finish me
        print("HELLO")
        self.logger.logg("fill_in", 0)
        self.b_idx = defs.PLAYERSTATUS_BENCH
        dummy = "Empty"
        for i in range(0, self.max_players):
            self.sorted_playerlist[i] = dummy
        i = 0
        for player in self.player_list:
            if player.position == defs.PLAYERTYPE_QB:
                self.logger.logg("found qb at%d"%(i), 0)
                if self.sorted_playerlist[defs.PLAYERSTATUS_QB] == "Empty":
                    self.logger.logg("starting qb at%d"%(i), 0)
                    self.sorted_playerlist[defs.PLAYERSTATUS_QB] = player
                    player.status = defs.PLAYERSTATUS_QB
                else:
                    self.logger.logg("bench qb at%d"%(i), 0)
                    self.bench_player_add(player)
            elif player.position == defs.PLAYERTYPE_RB:
                self.logger.logg("found rb at%d"%(i), 0)
                if self.sorted_playerlist[defs.PLAYERSTATUS_RB1] == "Empty":
                    self.sorted_playerlist[defs.PLAYERSTATUS_RB1] = player
                    player.status = defs.PLAYERSTATUS_RB1
                    self.logger.logg("starting rb1 at%d"%(i), 0)
                elif self.sorted_playerlist[defs.PLAYERSTATUS_RB2] == "Empty":
                    self.sorted_playerlist[defs.PLAYERSTATUS_RB2] = player
                    player.status = defs.PLAYERSTATUS_RB2
                    self.logger.logg("starting rb2 at%d"%(i), 0)
                elif self.sorted_playerlist[defs.PLAYERSTATUS_FLEX] == "Empty":
                    self.sorted_playerlist[defs.PLAYERSTATUS_FLEX] = player
                    player.status = defs.PLAYERSTATUS_FLEX
                    self.logger.logg("starting flex at%d"%(i), 0)
                else:
                    self.logger.logg("bench rb at%d"%(i), 0)
                    self.bench_player_add(player)
            elif player.position == defs.PLAYERTYPE_WR:
                self.logger.logg("found wr at%d"%(i), 0)
                if self.sorted_playerlist[defs.PLAYERSTATUS_WR1] == "Empty":
                    self.sorted_playerlist[defs.PLAYERSTATUS_WR1] = player
                    player.status = defs.PLAYERSTATUS_WR1
                    self.logger.logg("starting wr1 at%d"%(i), 0)
                elif self.sorted_playerlist[defs.PLAYERSTATUS_WR2] == "Empty":
                    self.sorted_playerlist[defs.PLAYERSTATUS_WR2] = player
                    player.status = defs.PLAYERSTATUS_WR2
                    self.logger.logg("starting wr2 at%d"%(i), 0)
                elif self.sorted_playerlist[defs.PLAYERSTATUS_FLEX] == "Empty":
                    self.sorted_playerlist[defs.PLAYERSTATUS_FLEX] = player
                    player.status = defs.PLAYERSTATUS_FLEX
                    self.logger.logg("starting flex at%d"%(i), 0)
                else:
                    self.logger.logg("bench wr at%d"%(i), 0)
                    self.bench_player_add(player)
            elif player.position == defs.PLAYERTYPE_TE:
                self.logger.logg("found te at%d"%(i), 0)
                if self.sorted_playerlist[defs.PLAYERSTATUS_TE] == "Empty":
                    self.logger.logg("starting te at%d"%(i), 0)
                    self.sorted_playerlist[defs.PLAYERSTATUS_TE] = player
                    player.status = defs.PLAYERSTATUS_TE
                elif self.sorted_playerlist[defs.PLAYERSTATUS_FLEX] == "Empty":
                    self.sorted_playerlist[defs.PLAYERSTATUS_FLEX] = player
                    player.status = defs.PLAYERSTATUS_FLEX
                    self.logger.logg("starting flex at%d"%(i), 0)
                else:
                    self.logger.logg("bench te at%d"%(i), 0)
                    self.bench_player_add(player)
            elif player.position == defs.PLAYERTYPE_DST:
                self.logger.logg("found dst at%d"%(i), 0)
                if self.sorted_playerlist[defs.PLAYERSTATUS_DST] == "Empty":
                    self.logger.logg("starting dst at%d"%(i), 0)
                    self.sorted_playerlist[defs.PLAYERSTATUS_DST] = player
                    player.status = defs.PLAYERSTATUS_DST
                else:
                    self.logger.logg("bench dst at%d"%(i), 0)
                    self.bench_player_add(player)
            elif player.position == defs.PLAYERTYPE_KICKER:
                self.logger.logg("kicker found at%d"%(i), 0)
                if self.sorted_playerlist[defs.PLAYERSTATUS_KICKER] == "Empty":
                    self.logger.logg("starting kicker at%d"%(i), 0)
                    self.sorted_playerlist[defs.PLAYERSTATUS_KICKER] = player
                    player.status = defs.PLAYERSTATUS_KICKER
                else:
                    self.logger.logg("bench kicker at%d"%(i), 0)
                    self.bench_player_add()
            else:
                self.logger.logg("unknown found at%d"%(i), 1)
            i += 1
        self.print_roster()

    def bench_player_add(self, player):
        try:
            self.sorted_playerlist[self.b_idx] = player
        except IndexError:
            # they ran out of bench room. just extend it for them.
            self.sorted_playerlist.append(player)

        player.status = defs.PLAYERSTATUS_BENCH
        self.b_idx += 1


    def print_roster(self):
        self.logger.logg("print_roster", 0)
        self.logger.logg("Team:%s"%(self.name), 1)
        out_strin = "Ros    | "
        max_name_len = 4
        for player in self.player_list:
            if (len(player.name) > max_name_len):
                max_name_len = len(player.name)
        name_str = "Name"
        while (len(name_str) < max_name_len):
            name_str += " "
        out_strin += name_str
        out_strin += " | Pos | Rank | Team | Pick | Ovrall | ADP |" 
        output = out_strin + '\n'
        self.logger.logg(out_strin, 1)

        i = 0
        with open(self.rosterfile,'w') as f:
            for player in self.sorted_playerlist:
                if i < defs.PLAYERSTATUS_BENCH:
                    prepend = prepend_printlist[i]
                else:
                    prepend = prepend_printlist[defs.PLAYERSTATUS_BENCH]
                try:
                    out_strin = player.print_info(max_name_len, prepend)
                except AttributeError:
                    out_strin = prepend+"empty"
                self.logger.logg(out_strin, 1)
                output += out_strin + "\n"
                i += 1
            f.write(output)
            

if __name__ == '__main__':
    main()
