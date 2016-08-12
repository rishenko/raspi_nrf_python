import sys
from twisted.logger import (
	Logger, textFileLogObserver, FilteringLogObserver,
	LogLevel, LogLevelFilterPredicate
)

class Log(object):
    # quick twisted logger builder
    def buildLogger(self):
        LOG_LEVEL = LogLevel.debug
        observer = textFileLogObserver(sys.stdout)
        filteringObs = FilteringLogObserver(observer,
                                            [LogLevelFilterPredicate(defaultLogLevel=LOG_LEVEL)])
        return Logger(observer=filteringObs)

# iterate over a Queue.Queue
def iter_except(func, exception, first=None):
    """ Call a function repeatedly until an exception is raised.

    Converts a call-until-exception interface to an iterator interface.
    Like builtins.iter(func, sentinel) but uses an exception instead
    of a sentinel to end the loop.

    Examples:
        iter_except(functools.partial(heappop, h), IndexError)   # priority queue iterator
        iter_except(d.popitem, KeyError)                         # non-blocking dict iterator
        iter_except(d.popleft, IndexError)                       # non-blocking deque iterator
        iter_except(q.get_nowait, Queue.Empty)                   # loop over a producer Queue
        iter_except(s.pop, KeyError)                             # non-blocking set iterator

    """
    try:
        if first is not None:
            yield first()            # For database APIs needing an initial cast to db.first()
        while 1:
            yield func()
    except exception:
        pass

def convertToDict(obj):
    d = {}
    d.update(obj.__dict__)
    return d
