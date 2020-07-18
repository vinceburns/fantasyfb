
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
        adp = lis[11].split('.')[0]
    except IndexError:
        #unlucky see if it is not a float
        pass
    try:
        adp = int(adp, 10)
    except ValueError:
        adp = "No data"
    player = Player(position, rank, name, team, bye, adp)
    return player


def main():
    players = []
    player_csv = "FantasyPros_2020_Draft_Overall_Rankings.csv"
    with open(player_csv,'r') as f:
        f.__next__()
        for line in f:
            player = player_generate_fromcsv(line)
            if player != None:
                players.append(player)
    try:
        # position = int(input("Welcome to Vince's Mock Draft. Please Enter your position:"), 10)
        # name = input("Welcome to Vince's Mock Draft. Please Enter your team name:")
        # n_rosters = int(input("Welcome to Vince's Mock Draft. Please Enter the number of players in the draft: "), 10)
        position = 6
        name = "vinny"
        n_rosters = 8
    except ValueError:
        print("Invalid position. Exiting...")
        sys.exit(2)
    if position > n_rosters or position < 0:
        print("Invalid position. Exiting...")
        sys.exit(2)
    draft = Draft(position, name, players, n_rosters, player_csv)
    draft.draft()

if __name__ == '__main__':
    main()
