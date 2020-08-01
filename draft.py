
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
        self.starred_players = []
        for player in self.players:
            if player.stared == 1:
                self.starred_players.append(player)
        self.allplayers = copy.copy(players)
        max_name = 10
        self.done = 0
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
        filname = 'logs/picks/Draft_picks' + time.strftime('%m_%d_%y_%H_%M_%S') + '.log'
        self.picklogger = filname
        with open(self.picklogger, 'w+') as f:
            #ensure it is empty
            pass
        self.player_csv = player_csv
        self.user_name = name
        for i in range(1, (self.n_rosters+1)):
            if i == position:
                ros_str = name
            else:
                ros_str = "comp%d"%(i)
            roster = Roster(i, ros_str, self.player_csv, self.logger)
            if i == (self.user_pos+1):
                self.user_roster = roster
            self.roster.append(roster)
        if load != None:
            str =  "loading draft"
            self.logger.logg(str, 1)
        self.current_roster = self.roster[0]
        self.remaining_picks = (self.n_rosters * self.roster[0].max_players)

    def acquire(self):
        self.mutex.acquire()

    def release(self):
        self.mutex.release()

    def my_turn(self):
        if self.current_roster == self.user_roster:
            return True
        return False

    def revert_pick(self):
        with open(self.picklogger, 'r') as f:
            picks = f.readlines()
        last_pick = picks[len(picks)-1].split("|")
        if ((self.total_pick-1) != int(last_pick[0],10)):
            str =  "Bad error on revert pick..."
            self.logger.logg(str, 1)
            sys.exit(2)
        self.total_pick -= 1
        rank = int(last_pick[2], 10)
        roster_idx = int(last_pick[1], 10)
        self.selections.pop()
        for i in range(0, len(self.players)):
            if rank < self.players[i].rank:
                self.players.insert(i, self.allplayers[rank-1])
                break
        self.sync_draft(self.selections)

    def check_starred(self):
        if (len(self.starred_players) == 0):
            self.logger.logg("No stared players", 1)
            return
        count = 0
        risk_list = []
        next_pick = self.total_pick
        remaining_picks = self.remaining_picks

        rd_pick = self.rd_pick
        rd = self.round

        roster_idx = rd_pick
        user_picks = []
        while True:
            if remaining_picks == 0:
                break
            if self.user_pos == roster_idx:
                user_picks.append(next_pick)
            next_pick += 1
            remaining_picks -= 1
            rd_pick += 1
            if (rd_pick == self.n_rosters):
                rd_pick = 0
                rd += 1
            roster_idx = rd_pick
            if rd % 2 != 0:
                #going down the snake. or should i say snek
                roster_idx = ((self.n_rosters-1) - rd_pick)
        if len(user_picks) == 0:
            self.logger.logg("You have no picks remaining", 1)
            return
        self.logger.logg("Your picks are:{0}".format(user_picks), 1)

        output = "Player"
        while (len(output) < self.maxnamelen):
            output += " "
        output += " | Message"
        for player in self.starred_players:
            output += " \n"
            msg = ""
            if (len(user_picks) < 2):
                msg = "We are near the end of the draft so the risk is high"
            elif (player.adp < user_picks[0]):
                msg = "This Players Average draft position is before your next pick So the risk is high"
            elif (player.rank < user_picks[0]):
                msg = "This Players rank is lower than your next pick So the risk is high"
            elif (player.adp < user_picks[1]):
                msg = "This Players Average draft position is in between your next two picks so the risk is fairly high"
            elif (player.rank < user_picks[1]):
                msg = "This Players rank is in between your next two picks so the risk is fairly high"
            else:
                msg = "This players rank and ADP is not lower than your next two picks so the risk is fairly low"
            player_str = player.name
            while (len(player_str) < self.maxnamelen):
                player_str += " "
            #don't know why this is needed
            player_str += " "
            player_str += "| {0}".format(msg)
            output += player_str
        self.logger.logg(output, 1)
        return

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
        out_strin += " | Pos | Rank | Team | Pick | Ovrall | ADP | Bye  |" 
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

    def draft_player(self, player_idx, is_server):
        with open(self.picklogger, 'a+') as f:
            #pick | roster_idx | player rank
            f.write("%d|%d|%d\n"%(self.total_pick, self.current_roster.position - 1, self.players[player_idx].rank))
        self.logger.logg("%s selected %s"%(self.current_roster.name, self.players[player_idx].name), 1)
        self.players[player_idx].pick = self.rd_pick + 1
        self.players[player_idx].overallpick = self.total_pick
        self.selections.append(self.players[player_idx].rank)
        self.current_roster.player_list.append(self.players[player_idx])
        for i in range(0, len(self.starred_players)):
            if (self.players[player_idx].rank == self.starred_players[i].rank):
                del self.starred_players[i]
                break
        del self.players[player_idx]
        self.total_pick += 1
        self.remaining_picks -= 1
        self.rd_pick += 1
        if (self.rd_pick == self.n_rosters):
            self.rd_pick = 0
            self.round += 1
        self.current_roster.fill_in(is_server)
        if (self.remaining_picks == 0):
            self.done = 1

        roster_idx = self.rd_pick
        if self.round % 2 != 0:
            #going down the snake. or should i say snek
            roster_idx = ((self.n_rosters-1) - self.rd_pick)
        self.current_roster = self.roster[roster_idx]
        self.logger.logg("Round:{0}, Pick:{1}, Team:{2}, Total_Picks:{3}, Remaining_Picks:{4}(per team:{5})".format(self.round, self.rd_pick, self.current_roster.name, self.total_pick, self.remaining_picks, round(self.remaining_picks/self.n_rosters)), 1)
        if (is_server == 1) and self.my_turn():
            self.logger.logg("Your are on the Clock!!!!", 1)

    def confirm_selection(self, selections, uIn):
        if selections == None:
            return None,None
        if not uIn.startswith("y"):
            return None,None
        try:
            player_idx =  int(uIn.split(":", 10)[1])
            if ((player_idx <= len(selections)) and (player_idx > 0)):
                return self.players[player_idx-1].name, selections[player_idx-1]
            else:
                self.logger.logg("confirm_select fail. player_idx:{0}, len:{1}".format(player_idx, len(selections)), 1)
                return None,None
        except:
            self.logger.logg("An exception occured. please try again with the forma y:<index>", 1)
            return None,None


    def sync_draft(self, selections):
        self.players = copy.copy(self.allplayers)
        self.round = 0
        self.rd_pick = 0
        self.total_pick = 1
        self.selections = []
        self.current_roster = self.roster[0]
        for roster in self.roster:
            roster.player_list = []
            for i in range(0, roster.max_players):
                roster.sorted_playerlist[i] = "Empty"
        while (self.total_pick < (len(selections)) + 1):
            self.logger.logg("round:{0} roster:{1} self.rd_pick:{2}".format(self.round, self.current_roster.name, self.rd_pick), 1)
            player_idx = len(self.players)
            for i in range(0, len(self.players)):
                if self.players[i].rank == selections[self.total_pick-1]:
                    player_idx = i
                    break;
            if (player_idx == len(self.players)):
                self.logger.logg("invalid player selection", 1)
                sys.exit(2)

            self.draft_player(player_idx, 0)

        self.logger.logg("total_pick:{0} len:{1}".format(self.total_pick, len(selections)), 1)
        if self.my_turn():
            self.logger.logg("Your are on the Clock!!!!", 1)
        return True

    def player_fzf(self, string):
        test_list = []
        return_list = []
        i = 0
        for player in self.players:
            test_list.append(player.name.lower())
        string = string.lower()
        for i in range(0, len(test_list)):
            name = test_list[i]
            if is_fzfmatch(string, name) == True:
                #append the player index
                return_list.append(i)
        out_strin = "#  | "

        name_str = "Name"
        while (len(name_str) < self.maxnamelen):
            name_str += " "
        out_strin += name_str
        out_strin += " | Pos | Rank | Team | Pick | Ovrall | ADP |" 
        self.logger.logg(out_strin, 1)
        count = 0
        printer = ''
        player_idx = 0
        for i in range(0, len(return_list)):
            if count >= 20:
                break
            count += 1
            player_idx = return_list[i]
            printer += self.players[player_idx].print_info(self.maxnamelen, "%02d | "%(count))
            printer += "\n"

        if (len(return_list) > 0):
            self.logger.logg(printer, 1)
        else:
            self.logger.logg("Sorry, could not find that pattern in any player's names.", 1)
            self.logger.logg("Please Try again", 1)

        return return_list

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


def is_fzfmatch(match_str, check_str):
    for match_char in range(0, len(match_str)):
        found = 0
        for check_char in range(0, len(check_str)):
            if match_str[match_char] == check_str[check_char]:
                #we found this char trucate string and move to next match char
                found = 1
                if check_char != len(check_str):
                    check_str = check_str[check_char::]
                break
        if found == 0:
            return False
    return True
if __name__ == '__main__':
    main()
