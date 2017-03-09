from mongodb import StorableMixin
from util import DT


class LogEntry(StorableMixin):

    SEVERE = 1
    ERROR = 2
    INFO = 3

    def __init__(self, logger, title, message, level=INFO, objs=None):
        super(LogEntry, self).__init__()
        self.logger = logger
        self.title = title
        self.message = message
        self.level = level
        self.objs = objs

    def __str__(self):
        return '%s [%s:%s] %s\n%s' % (
            DT(self.__time__).time,
            self.logger,
            self.level,
            self.title,
            self.message
        )
