import time
import threading
import sys

class Logger():
    def __init__(self, filename):
        self.mutex = threading.Lock()
        self.wrfile = filename
        self.header = time.strftime("%H:%M:%S | ",time.localtime())
        self.buffer = ''
        self.ts = time.time()
        with open(self.wrfile, 'w+') as f:
            f.write(self.header+'Draft Starting\n')
    def logg(self, outstr, toconsole):
        if toconsole == 1:
            print(outstr)
            sys.stdout.flush()
        self.buffer += (self.header+outstr+'\n')
        if ((len(self.buffer) >= 4096) or (time.time() - self.ts >= 120)):
            with open(self.wrfile, 'a+') as f:
                f.write(self.buffer)
            self.buffer = ''
            self.ts = time.time()

if __name__ == '__main__':
    main()
