
import sys
import time
from os import fsync,system,_exit
import draftlogging
from defines import Defines as defs

class Player():
    def __init__(self, position, rank, name, team, bye, adp, stared, posrank, tier, sos):
        self.position = position
        self.rank = rank
        self.posrank = posrank
        self.tier = tier
        self.sos = sos
        self.tier = tier
        self.name = name
        self.team = team
        self.bye = bye
        self.pick = 0
        self.overallpick = 0
        self.adp = adp
        self.stared = stared
        self.status = defs.PLAYERSTATUS_BENCH

    def print_info(self, name_len, prepend):
        #name_len 
        out_strin = ""
        out_strin += "%s"%(self.name)
        if name_len != None:
            while (len(out_strin) < name_len):
                out_strin += " "
        if prepend != None:
            out_strin = prepend + out_strin
        out_strin += " | %s | "%(self.position)
        out_strin += "%03d  | "%(self.rank)
        out_strin += "%s  | "%(self.team)
        try: 
            out_strin += "%03d | "%(self.adp)
        except:
            out_strin += "err |"
        out_strin += "%02d  | "%(self.bye)
        out_strin += "%02d   | "%(self.tier)
        out_strin += "%d/5  |"%(self.sos)
        out_strin += "%s"%(self.posrank)
        return out_strin

if __name__ == '__main__':
    main()
