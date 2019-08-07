
import sys
import time
from os import fsync,system,_exit
import draftlogging
from defines import Defines as defs
from roster import Roster
from player import Player

class Draft():
    def __init__(self, position, name, players, n_players):
        self.roster = []
        self.players = players
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
        for i in range(1, (self.n_rosters+1)):
            if i == self.user_pos:
                ros_str = name
            else:
                ros_str = "comp%d"%(i)
            roster = Roster(i, ros_str, self.logger)
            self.roster.append(roster)

    def draft(self):
        while (1):
            if (self.round > self.roster[0].max_players):
                #print summary? do something?
                self.logger.logg("draft complete", 1)
                return
            while (self.rd_pick < self.n_rosters):
                index = self.rd_pick
                if self.round % 2 != 0:
                    #odd round go down the snake
                    index = ((self.n_rosters-1) - self.rd_pick)
                self.player_select(index)
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
        if (self.roster[idx].position) != self.user_pos:
            #user input not needed. Assume players are ordered by ecr
            """@todo (vburns) we got to here to get the frame work set up. Now
            we want to create our algorithm that will select players smartly.
            if this ever became anything it would be because we did this @todo
            well...."""
            self.draft_player(idx, 0)
            return
        self.logger.logg("Your Turn!", 1)
        while (1):
            #todo keyboard thread... So we can set a max timer. 
            uIn = raw_input("Please search for your selection or type 'h' for more options:\n")
            if uIn == "h":
                self.logger.logg("help menu\nInput | Function|", 1)
                self.logger.logg("1 | Print Best available", 1)
                self.logger.logg("2 | Print Current Roster", 1)
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
            elif uIn == "2":
                self.roster[idx].print_roster()
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
        self.logger.logg("%s selected %s"%(self.roster[roster_idx].name, self.players[player_idx].name), 1)
        self.players[player_idx].pick = self.round + 1
        self.players[player_idx].overallpick = self.total_pick
        self.roster[roster_idx].player_list.append(self.players[player_idx])
        del self.players[player_idx]
        self.total_pick += 1
        if self.roster[roster_idx].position == self.user_pos:
            self.roster[roster_idx].fill_in()
        # time.sleep(1)

    def confirm_selection(self, selections, roster_idx):
        if selections == None:
            return None
        selection = raw_input("Would you like to select one of those players? if so please send y:<selection> for example if you want #10 from that list please send 'y:10'\n")
        if not selection.startswith("y:"):
            return None
        try:
            player_idx =  int(selection.split(":", 10)[1])
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
