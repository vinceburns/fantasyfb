
import sys
import time
from os import fsync,system,_exit
import draftlogging

PLAYERTYPE_QB = "QB "
PLAYERTYPE_RB = "RB "
PLAYERTYPE_WR = "WR "
PLAYERTYPE_TE = "TE "
PLAYERTYPE_DST = "DST"
PLAYERTYPE_KICKER = "K  "

PLAYERSTATUS_QB     = 0
PLAYERSTATUS_RB1    = 1
PLAYERSTATUS_RB2    = 2
PLAYERSTATUS_WR1    = 3
PLAYERSTATUS_WR2    = 4
PLAYERSTATUS_TE     = 5
PLAYERSTATUS_FLEX   = 6
PLAYERSTATUS_DST    = 7
PLAYERSTATUS_KICKER = 8
PLAYERSTATUS_BENCH  = 9

prepend_printlist = ["QB:    | ", "RB1:   | ", "RB2:   | ", "WR1:   | ",\
        "WR2:   | ", "TE:    | ", "FLEX:  | ", "DST:   | ", "K:     | ",\
        "BENCH: | "]

class Player():
    def __init__(self, position, rank, name, team, bye, adp):
        self.position = position
        self.rank = rank
        self.name = name
        self.team = team
        self.bye = bye
        self.pick = 0
        self.overallpick = 0
        self.adp = adp
        self.status = PLAYERSTATUS_BENCH

    def print_info(self, name_len, prepend):
        #name_len 
        out_strin = ""
        out_strin += "%s"%(self.name)
        while (len(out_strin) < name_len):
            out_strin += " "
        if prepend != None:
            out_strin = prepend + out_strin
        out_strin += " | %s | "%(self.position)
        out_strin += "%03d  | "%(self.rank)
        out_strin += "%s  | "%(self.team)
        out_strin += "%03d  | "%(self.pick)
        out_strin += "%03d    |"%(self.overallpick)
        return out_strin


class Roster():
    def __init__(self, position, name, logger):
        self.position = position
        self.name = name
        self.max_bench = 7
        self.bench = []
        self.player_list = []
        #see enum at top of file.
        self.sorted_playerlist = []
        self.max_players = 16
        self.logger = logger
        dummy = "Empty"
        for i in range(0, self.max_players):
            self.sorted_playerlist.append(dummy)
    def fill_in(self):
        #finish me
        self.logger.logg("fill_in", 0)
        b_idx = PLAYERSTATUS_BENCH
        dummy = "Empty"
        for i in range(0, self.max_players):
            self.sorted_playerlist[i] = dummy
        i = 0
        for player in self.player_list:
            if player.position == PLAYERTYPE_QB:
                self.logger.logg("found qb at%d"%(i), 0)
                if self.sorted_playerlist[PLAYERSTATUS_QB] == None:
                    self.logger.logg("starting qb at%d"%(i), 0)
                    self.sorted_playerlist[PLAYERSTATUS_QB] = player
                    player.status = PLAYERSTATUS_QB
                else:
                    self.logger.logg("bench qb at%d"%(i), 0)
                    self.sorted_playerlist[b_idx] = player
                    b_idx += 1
                    player.status = PLAYERSTATUS_BENCH
            elif player.position == PLAYERTYPE_RB:
                self.logger.logg("found rb at%d"%(i), 0)
                if self.sorted_playerlist[PLAYERSTATUS_RB1] == "Empty":
                    self.sorted_playerlist[PLAYERSTATUS_RB1] = player
                    player.status = PLAYERSTATUS_RB1
                    self.logger.logg("starting rb1 at%d"%(i), 0)
                elif self.sorted_playerlist[PLAYERSTATUS_RB2] == "Empty":
                    self.sorted_playerlist[PLAYERSTATUS_RB2] = player
                    player.status = PLAYERSTATUS_RB2
                    self.logger.logg("starting rb2 at%d"%(i), 0)
                elif self.sorted_playerlist[PLAYERSTATUS_FLEX] == "Empty":
                    self.sorted_playerlist[PLAYERSTATUS_FLEX] = player
                    player.status = PLAYERSTATUS_FLEX
                    self.logger.logg("starting flex at%d"%(i), 0)
                else:
                    self.logger.logg("bench rb at%d"%(i), 0)
                    self.sorted_playerlist[b_idx] = player
                    b_idx += 1
                    player.status = PLAYERSTATUS_BENCH
            elif player.position == PLAYERTYPE_WR:
                self.logger.logg("found wr at%d"%(i), 0)
                if self.sorted_playerlist[PLAYERSTATUS_WR1] == "Empty":
                    self.sorted_playerlist[PLAYERSTATUS_WR1] = player
                    player.status = PLAYERSTATUS_WR1
                    self.logger.logg("starting wr1 at%d"%(i), 0)
                elif self.sorted_playerlist[PLAYERSTATUS_WR2] == "Empty":
                    self.sorted_playerlist[PLAYERSTATUS_WR2] = player
                    player.status = PLAYERSTATUS_WR2
                    self.logger.logg("starting wr2 at%d"%(i), 0)
                elif self.sorted_playerlist[PLAYERSTATUS_FLEX] == "Empty":
                    self.sorted_playerlist[PLAYERSTATUS_FLEX] = player
                    player.status = PLAYERSTATUS_FLEX
                    self.logger.logg("starting flex at%d"%(i), 0)
                else:
                    self.logger.logg("bench wr at%d"%(i), 0)
                    self.sorted_playerlist[b_idx] = player
                    b_idx += 1
                    player.status = PLAYERSTATUS_BENCH
            elif player.position == PLAYERTYPE_TE:
                self.logger.logg("found te at%d"%(i), 0)
                if self.sorted_playerlist[PLAYERSTATUS_TE] == "Empty":
                    self.logger.logg("starting te at%d"%(i), 0)
                    self.sorted_playerlist[PLAYERSTATUS_TE] = player
                    player.status = PLAYERSTATUS_TE
                elif self.sorted_playerlist[PLAYERSTATUS_FLEX] == "Empty":
                    self.sorted_playerlist[PLAYERSTATUS_FLEX] = player
                    player.status = PLAYERSTATUS_FLEX
                    self.logger.logg("starting flex at%d"%(i), 0)
                else:
                    self.logger.logg("bench te at%d"%(i), 0)
                    self.sorted_playerlist[b_idx] = player
                    b_idx += 1
                    player.status = PLAYERSTATUS_BENCH
            elif player.position == PLAYERTYPE_DST:
                self.logger.logg("found dst at%d"%(i), 0)
                if self.sorted_playerlist[PLAYERSTATUS_DST] == "Empty":
                    self.logger.logg("starting dst at%d"%(i), 0)
                    self.sorted_playerlist[PLAYERSTATUS_DST] = player
                    player.status = PLAYERSTATUS_DST
                else:
                    self.logger.logg("bench dst at%d"%(i), 0)
                    self.sorted_playerlist[b_idx] = player
                    b_idx += 1
                    player.status = PLAYERSTATUS_BENCH
            elif player.position == PLAYERTYPE_KICKER:
                self.logger.logg("kicker found at%d"%(i), 0)
                if self.sorted_playerlist[PLAYERSTATUS_KICKER] == "Empty":
                    self.logger.logg("starting kicker at%d"%(i), 0)
                    self.sorted_playerlist[PLAYERSTATUS_KICKER] = player
                    player.status = PLAYERSTATUS_KICKER
                else:
                    self.logger.logg("bench kicker at%d"%(i), 0)
                    self.sorted_playerlist[b_idx] = player
                    b_idx += 1
                    player.status = PLAYERSTATUS_BENCH
            else:
                self.logger.logg("unknown found at%d"%(i), 1)
            i += 1
        self.print_roster()

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
        out_strin += " | Pos | Rank | Team | Pick | Ovrall |" 
        self.logger.logg(out_strin, 1)

        i = 0
        for player in self.sorted_playerlist:
            if i < PLAYERSTATUS_BENCH:
                prepend = prepend_printlist[i]
            else:
                prepend = prepend_printlist[PLAYERSTATUS_BENCH]
            try:
                out_strin = player.print_info(max_name_len, prepend)
                self.logger.logg(out_strin, 1)
            except AttributeError:
                self.logger.logg(prepend+"empty", 1)
            i += 1

class Draft():
    def __init__(self, position, name, players):
        self.roster = []
        self.players = players
        self.user_pos = position
        self.round = 0
        self.rd_pick = 0
        self.total_pick = 1
        filname = 'Draft_' + time.strftime('%m_%d') + '.txt'
        self.logger = draftlogging.Logger(filname)
        #bigfat@todo replace all of the 8's and 7's and 9's based on number of teams in the draft
        for i in range(1, 9):
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
            while (self.rd_pick < 8):
                index = self.rd_pick
                if self.round % 2 != 0:
                    #odd round go down the snake
                    index = (7 - self.rd_pick)
                self.player_select(index)
                self.rd_pick += 1
            self.round += 1
            self.rd_pick = 0
    def show_remaining(self):
        for i in range(0, 20):
            if (i > len(self.players)):
                return 
            self.logger.logg(self.players[i].name, 1)

    def player_select(self, idx):
        outstr = "Round:%d Pick:%d Total Pick: %d"\
                %((self.round+1), (self.rd_pick+1), (self.total_pick+1))
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
            elif uIn == "1":
                self.show_remaining()
            elif uIn == "2":
                self.roster[idx].print_roster()
            else:
                selections = self.player_fzf(uIn)
                if len(selections) == 0:
                    self.logger.logg("Sorry, could not find that pattern in any player's names.", 1)
                    self.logger.logg("Please Try again", 1)
                    continue
                self.logger.logg("Please Enter correct number for the player you would like to draft", 1)
                self.logger.logg("Number | Name |", 1)
                i = 1
                for selection_idx in selections:
                    self.logger.logg("%d: | %s"%(i, self.players[selection_idx].name), 1)
                    i += 1
                selection = raw_input("You may enter any number(or letter) that is not printed to search again\n")
                try:
                    player_idx =  int(selection, 10)
                except:
                    continue
                if ((player_idx <= len(selections)) and (player_idx > 0)):
                    self.draft_player(idx, selections[player_idx-1])
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
        if (len(position) < 3):
            position += " "
    except:
        return
    name = lis[3]
    team = lis[4]
    if (len(team) < 3):
        team += " "
    try:
        bye = int(lis[6], 10)
    except:
        bye = None
    adp = lis[11]
    player = Player(position, rank, name, team, bye, adp)
    return player


def main():
    players = []
    with open("FantasyPros_2019_Draft_Overall_Rankings.csv",'r') as f:
        f.next()
        for line in f:
            player = player_generate_fromcsv(line)
            if player != None:
                players.append(player)
    try:
        position = int(raw_input("Welcome to Vince's Mock Draft. Please Enter your position:"), 10)
        name = raw_input("Welcome to Vince's Mock Draft. Please Enter your team name:")
    except ValueError:
        print "Invalid position. Exiting..."
        sys.exit(2)
    if position > 8 or position < 0:
        print "Invalid position. Exiting..."
        sys.exit(2)
    draft = Draft(position, name, players)
    draft.draft()

if __name__ == '__main__':
    main()
