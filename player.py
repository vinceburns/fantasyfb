
import sys
import time
from os import fsync,system,_exit
import draftlogging
from defines import Defines as defs

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
        self.status = defs.PLAYERSTATUS_BENCH

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

if __name__ == '__main__':
    main()
