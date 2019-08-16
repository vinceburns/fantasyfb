
import sys
import copy
import time
from os import fsync,system,_exit
import draftlogging
from defines import Defines as defs
from roster import Roster
from player import Player

class Draft():
    def __init__(self, position, name, players, n_players, load=None):
        self.roster = []
        self.players = players
        self.allplayers = copy.copy(players)
        max_name = 10
        for player in players:
            if len(player.name) > max_name:
                max_name = len(player.name)
        self.maxnamelen = max_name
        self.user_pos = position
        self.round = 0
        self.rd_pick = 0
        self.total_pick = 1
        self.n_rosters = n_players
        filname = 'Draft_' + time.strftime('%m_%d') + '.log'
        self.logger = draftlogging.Logger(filname)
        filname = 'Draft_picks' + time.strftime('%m_%d_%H') + '.log'
        self.picklogger = filname
        for i in range(1, (self.n_rosters+1)):
            if i == self.user_pos:
                ros_str = name
            else:
                ros_str = "comp%d"%(i)
            roster = Roster(i, ros_str, self.logger)
            self.roster.append(roster)
        if load != None:
            str =  "loading draft"
            self.logger.logg(str, 1)

    def draft(self):
        while (1):
            #this will need some refactoring with the threading
            if (self.round > self.roster[0].max_players):
                #print summary? do something?
                self.logger.logg("draft complete", 1)
                return
            while (self.rd_pick < self.n_rosters):
                index = self.rd_pick
                if self.round % 2 != 0:
                    #odd round go down the snake
                    index = ((self.n_rosters-1) - self.rd_pick)
                if self.player_select(index) != None:
                    continue
                self.rd_pick += 1
            self.round += 1
            self.rd_pick = 0
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
        for i in range(0, len(self.players)):
            if count >= 20:
                return return_list
            if len(filterlist):
                if self.players[i].position not in filterlist:
                    continue
            count += 1
            printer = self.players[i].print_info(self.maxnamelen, "%02d | "%(count))
            self.logger.logg(printer, 1)
            return_list.append(i)
        return return_list

    def player_select(self, idx):
        outstr = "Round:%d Pick:%d Total Pick: %d"\
                %((self.round+1), (self.rd_pick+1), (self.total_pick))
        self.logger.logg(outstr, 1)
        """if (self.roster[idx].position) != self.user_pos:
            #user input not needed. Assume players are ordered by ecr
            @todo (vburns) we got to here to get the frame work set up. Now
            we want to create our algorithm that will select players smartly.
            if this ever became anything it would be because we did this @todo
            well....
            self.draft_player(idx, 0)
            return"""
        self.logger.logg("Your Turn!", 1)
        while (1):
            #todo keyboard thread... So we can set a max timer. 
            uIn = raw_input("Please search for your selection or type 'h' for more options:\n")
            if uIn == "h":
                self.logger.logg("help menu\nInput | Function|", 1)
                self.logger.logg("1  | Print Best available", 1)
                self.logger.logg("2  | Print Current Roster", 1)
                self.logger.logg("3  | Revert Pick", 1)
                self.logger.logg("99 | Resume draft (server side only)", 1)
                self.logger.logg("start fuzzy finding any name to search for a player you would like. See creator for what fuzzy finding means:) (he stole the idea from a vim plugin he uses", 1)
                continue
            elif uIn.startswith("1:"):
                try:
                    position = uIn.split(':')[1]
                except:
                    position = None
                selections = self.show_topavail(position)
                if self.confirm_selection(selections, idx) == True:
                    return 
            elif uIn.startswith("1"):
                selections = self.show_topavail(None)
                if self.confirm_selection(selections, idx) == True:
                    return 
            elif uIn.startswith("2"):
                try:
                    position = uIn.split(':')[1]
                except:
                    self.roster[idx].print_roster()
                    continue
                if position == "all":
                    for roster in self.roster:
                        roster.print_roster()
                    continue
                else:
                    try:
                        position = int(position, 10)
                        if position <= self.n_rosters:
                            self.roster[position-1].print_roster()
                            continue
                    except:
                        pass
                    self.logger.logg("Sorry, Invalid roster", 1)
                    continue
            elif uIn == "3":
                self.revert_pick()
                return True
            elif uIn.startswith("99"):
                try:
                    fil = uIn.split(':')[1]
                    with open(fil, 'r') as f:
                        picks = f.readlines()
                        ret = self.resume_draft(f)
                    if ret:
                        out_strin += "Updated draft logger to: %s"%(fil) 
                        self.logger.logg(out_strin, 1)
                        self.picklogger = fil
                        return True
                    else:
                        continue
                except IndexError:
                    out_strin += "invalid file" 
                    self.logger.logg(out_strin, 1)
                    continue
            else:
                selections = self.player_fzf(uIn)
                if len(selections) == 0:
                    self.logger.logg("Sorry, could not find that pattern in any player's names.", 1)
                    self.logger.logg("Please Try again", 1)
                    continue

                self.logger.logg("Please Enter correct number for the player you would like to draft", 1)

                out_strin = "#  | "

                name_str = "Name"
                while (len(name_str) < self.maxnamelen):
                    name_str += " "
                out_strin += name_str
                out_strin += " | Pos | Rank | Team | Pick | Ovrall | ADP |" 
                self.logger.logg(out_strin, 1)
                count = 0
                for selection_idx in selections:
                    count += 1
                    printer = self.players[selection_idx].print_info( \
                            self.maxnamelen, "%02d | "%(count))
                    self.logger.logg(printer, 1)
                if self.confirm_selection(selections, idx) == True:
                    return 



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
        return return_list

    def draft_player(self, roster_idx, player_idx):
        with open(self.picklogger, 'a') as f:
            self.players[player_idx].rank
            #pick | roster_idx | player rank
            f.write("%d|%d|%d\n"%(self.total_pick, roster_idx, self.players[player_idx].rank))
        self.logger.logg("%s selected %s"%(self.roster[roster_idx].name, self.players[player_idx].name), 1)
        self.players[player_idx].pick = self.rd_pick + 1
        self.players[player_idx].overallpick = self.total_pick
        self.roster[roster_idx].player_list.append(self.players[player_idx])
        del self.players[player_idx]
        self.total_pick += 1
        self.roster[roster_idx].fill_in()
        # time.sleep(1)

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
        for i in range(0, len(self.players)):
            if rank < self.players[i].rank:
                self.players.insert(i, self.allplayers[rank-1])
                break

        idx = 0
        while (idx < len(self.roster[roster_idx].player_list)):
            if self.roster[roster_idx].player_list[idx].rank == rank:
                del self.roster[roster_idx].player_list[idx]
                self.roster[roster_idx].fill_in()
                if self.rd_pick == 0:
                    self.round -= 1
                    self.rd_pick = self.n_rosters-1
                else:
                    self.rd_pick -= 1
                break
            idx += 1

    def resume_draft(self, fil):
        picks = f.readlines()
        overall = []
        rank = []
        roster_idx = []
        for pick in picks:
            overall.append(int(pick.split("|")[0], 10))
            rank.append(int(pick.split("|")[2], 10))
            roster_idx.append(int(pick.split("|")[1], 10))
        check_overall = 1
        check_roster = 0
        inc = inc
        #integrity check
        for i in range(0, (len(overall)-1)):
            if overall[i] != check_overall:
                self.logger.logg("bad overall. got:%d expected:%d"%(overall[i], check_overall), 1)
                return False
            if check_roster != roster_idx[i]:
                self.logger.logg("bad overall. got:%d expected:%d"%(overall[i], check_overall), 1)
                return False
            if (check_overall % 8):
                #we at top or botom of snake
                if inc < 0:
                    inc = 1
                    #decrease roster so when we increment we end up at last roster
                    check_roster
                else:
                    inc = -1
                    #increase roster so when we decrement we end up at last roster
                    check_roster += 1
            check_roster += inc
            check_overall += 1
            

        self.players = copy.copy(self.allplayers)
        for roster in self.roster:
            roster.n_rosters = 0
            roster.sorted_playerlist = []
        self.round = 0
        self.rd_pick = 0
        self.total_pick = len(rank)
        for i in range(0, len(rank)):
            self.draft_player(roster_idx[i], rank[i]-1)
            self.roster[roster_idx[i]].fill_in()
        self.round = total_pick/self.total_pick
        self.rd_pick = total_pick%self.total_pick
        return True

    def confirm_selection(self, selections, roster_idx):
        if selections == None:
            return None
        selection = raw_input("Would you like to select one of those players? if so please send y<selection> for example if you want #10 from that list please send 'y10'\n")
        if not selection.startswith("y"):
            return None
        try:
            player_idx =  int(selection.split("y", 10)[1])
        except:
            print "error"
            return None
        if ((player_idx <= len(selections)) and (player_idx > 0)):
            self.draft_player(roster_idx, selections[player_idx-1])
            return True
        else:
            print player_idx, len(selections)
            return None

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
