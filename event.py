
import sys
import time
from os import fsync,system,_exit
import draftlogging
from defines import Defines as defs

class Event():
    def __init__(self, e_type, user_str = None, selections = None, is_success = None):
        self.type = e_type
        self.selections = selections
        self.is_success = is_success
        self.user_str = user_str

if __name__ == '__main__':
    main()
