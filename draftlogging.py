import time

class Logger():
    def __init__(self, filename):
        self.wrfile = open(filename, 'a')
        self.header = time.strftime("%H:%M:%S | ",time.localtime())
    def logg(self, outstr, toconsole):
        if toconsole == 1:
            print outstr
        self.wrfile.write(self.header+outstr+'\n')

if __name__ == '__main__':
    main()
