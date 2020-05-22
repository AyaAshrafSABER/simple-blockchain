from _datetime import datetime


class Logger:
    dir = ''
    port = 0
    type = ''

    def __init__(self, name):
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        file_name = '%s/%s-%d-%s-%s.log' % (Logger.dir, timestamp, Logger.port, Logger.type, name)
        self.file = open(file_name, 'w')

    def log(self, msg):
        self.file.write(str(msg) + '\n')
        self.file.flush()
