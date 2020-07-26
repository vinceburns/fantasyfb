
import sys
import copy
import time
from os import fsync,system,_exit
import draftlogging
from defines import Defines as defs
from roster import Roster
from player import Player
import threading

class Draft():
    def __init__(self, position, name, players, n_players, player_csv, load=None):
        self.roster = []
        self.mutex = threading.Lock()
        self.players = players
        self.allplayers = copy.copy(players)
        max_name = 10
        for player in players:
            if len(player.name) > max_name:
                max_name = len(player.name)
        self.maxnamelen = max_name
        self.user_pos = (position - 1)
        self.round = 0
        self.rd_pick = 0
        self.total_pick = 1
        self.n_rosters = n_players
        self.selections = []
        filname = 'logs/draft/Draft_' + time.strftime('%m_%d_%y') + '.log'
        self.logger = draftlogging.Logger(filname)
        filname = 'logs/picks/Draft_picks' + time.strftime('%m_%d_%y_%H') + '.log'
        self.picklogger = filname
        self.player_csv = player_csv
        self.user_name = name
        for i in range(1, (self.n_rosters+1)):
            if i == self.user_pos:
                ros_str = name
            else:
                ros_str = "comp%d"%(i)
            roster = Roster(i, ros_str, self.player_csv, self.logger)
            if i == self.user_pos:
                self.user_roster = roster
            self.roster.append(roster)
        if load != None:
            str =  "loading draft"
            self.logger.logg(str, 1)
        self.current_roster = self.roster[0]

    def acquire(self):
        self.mutex.acquire()

    def release(self):
        self.mutex.release()

    def my_turn(self):
        if self.current_roster == self.user_roster:
            return True
        return False

    def show_topavail(self, pos):
        filterlist = []

        return_list = []
        if pos != None:
            desired = pos.upper()
            if desired in defs.PLAYERTYPE_QB:
                filterlist.append(defs.PLAYERTYPE_QB)
            elif desired in defs.PLAYERTYPE_RB:
                filterlist.append(defs.PLAYERTYPE_RB)
            elif desired in defs.PLAYERTYPE_WR:
                filterlist.append(defs.PLAYERTYPE_WR)
            elif desired in defs.PLAYERTYPE_TE:
                filterlist.append(defs.PLAYERTYPE_TE)
            elif desired in "flex ":
                filterlist.append(defs.PLAYERTYPE_RB)
                filterlist.append(defs.PLAYERTYPE_WR)
                filterlist.append(defs.PLAYERTYPE_TE)
            elif desired in defs.PLAYERTYPE_DST:
                filterlist.append(defs.PLAYERTYPE_DST)
            elif desired in defs.PLAYERTYPE_KICKER:
                filterlist.append(defs.PLAYERTYPE_KICKER)
            else:
                filterlist = []

        out_strin = "#  | "

        name_str = "Name"
        while (len(name_str) < self.maxnamelen):
            name_str += " "
        out_strin += name_str
        out_strin += " | Pos | Rank | Team | Pick | Ovrall | ADP |" 
        self.logger.logg(out_strin, 1)
        count = 0
        printer = ''
        for i in range(0, len(self.players)):
            if count >= 20:
                break
            if len(filterlist):
                if self.players[i].position not in filterlist:
                    continue
            count += 1
            printer += self.players[i].print_info(self.maxnamelen, "%02d | "%(count))
            printer += "\n"
            return_list.append(i)

        self.logger.logg(printer, 1)
        return return_list

    def draft_player(self, player_idx):
        with open(self.picklogger, 'a+') as f:
            #pick | roster_idx | player rank
            f.write("%d|%d|%d\n"%(self.total_pick, roster_idx, self.players[player_idx].rank))
        self.logger.logg("%s selected %s"%(self.current_roster.name, self.players[player_idx].name), 1)
        self.players[player_idx].pick = self.rd_pick + 1
        self.players[player_idx].overallpick = self.total_pick
        self.selections.append(self.players[player_idx].rank)
        self.current_roster.player_list.append(self.players[player_idx])
        del self.players[player_idx]
        self.total_pick += 1
        self.rd_pick += 1
        if (self.rd_pick == self.n_rosters):
            self.rd_pick = 0
            self.round += 1
        self.current_roster.fill_in()

        roster_idx = self.rd_pick
        if self.round % 2 != 0:
            #going down the snake. or should i say snek
            roster_idx = ((self.n_rosters-1) - self.rd_pick)
        self.current_roster = self.roster[roster_idx]
        # time.sleep(1)

    def confirm_selection(self, selections, uIn):
        if selections == None:
            return None
        # selection = input("Would you like to select one of those players? if so please send y<selection> for example if you want #10 from that list please send 'y10'\n")
        uIn = "y:1"
        if not uIn.startswith("y"):
            return None
        player_idx =  int(uIn.split(":", 10)[1])
        if ((player_idx <= len(selections)) and (player_idx > 0)):
            return self.draft.players[player_idx-1].name, selections[player_idx-1]
        else:
            self.logger.logg("confirm_select fail. player_idx:{0}, len:{1}".format(player_idx, len(selections)), 1)
            return None

    def sync_draft(self, selections):
        self.players = copy.copy(self.allplayers)
        self.round = 0
        self.rd_pick = 0
        self.total_pick = 0
        self.selections = []
        while (self.total_pick < len(selections)):
            self.logger.logg("round:{0} roster:{1} self.rd_pick:{2}".format(self.round, self.current_roster.name, self.rd_pick), 1)
            player_idx = len(self.players)
            for i in range(0, len(self.players)):
                if self.players[i].rank == selections[self.total_pick]:
                    player_idx = i
                    break;
            if (player_idx == len(self.players)):
                self.logger.logg("invalid player selection", 1)
                sys.exit(2)

            self.draft_player(player_idx)

        self.logger.logg("total_pick:{0} len:{1}".format(self.total_pick, len(selections)), 1)
        return True

    def resume_draft(self, file_name):
        selections = []
        try:
            with open(file_name, 'r') as f:
                for line in f:
                    #pick | roster_idx | player rank
                    try:
                        selections.append(int(line.split("|")[2], 10))
                    except:
                        self.logger.logg("cant split! {0}".foramt(line), 1)
                        return
            self.sync_draft(selections)

        except:
            self.logger.logg("Invalid Log file!",1)


if __name__ == '__main__':
    main()
