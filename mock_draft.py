
import sys
import time
from os import fsync,system,_exit
import draftlogging
import defines
from roster import Roster
from player import Player
from draft import Draft

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
        n_rosters = int(raw_input("Welcome to Vince's Mock Draft. Please Enter the number of players in the draft: "), 10)
    except ValueError:
        print "Invalid position. Exiting..."
        sys.exit(2)
    if position > n_rosters or position < 0:
        print "Invalid position. Exiting..."
        sys.exit(2)
    draft = Draft(position, name, players, n_rosters)
    draft.draft()

if __name__ == '__main__':
    main()
