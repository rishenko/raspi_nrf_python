import sys, threading, os
from twisted.logger import (
    Logger, textFileLogObserver, FilteringLogObserver,
    LogLevel, LogLevelFilterPredicate
)

class Log(object):
    # quick twisted logger builder
    def buildLogger(self):
        LOG_LEVEL = LogLevel.debug
        observer = textFileLogObserver(sys.stdout)
        filteringObs = LowLevelFilteringLogObserver(observer,
                                            [LogLevelFilterPredicate(defaultLogLevel=LOG_LEVEL)])
        return Logger(observer=filteringObs)


class LowLevelFilteringLogObserver(FilteringLogObserver):
    """ A filtering log observer that tacks on pid/thread info. """
    def __init__(
                self, observer, predicates,
                        negativeObserver=lambda event: None
                ):
        super(LowLevelFilteringLogObserver, self).__init__(
                    observer, predicates, negativeObserver)

    def __call__(self, event):
        #if event['log_format'] and isinstance(event, dict):
        #    event['log_format'] = lowLevelDetailsStr() + event['log_format']
        #else:
        event.update(lowLevelDetails())

        super(LowLevelFilteringLogObserver, self).__call__(event)

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
    """ convert an object to a dict """
    d = {}
    d.update(obj.__dict__)
    return d

def lowLevelDetailsStr():
    """ convert lowLevelDetails into a simple string """
    detail = lowLevelDetails()
    return "pid/thread: " + detail["pid"] + "/" + detail["thread_id"] + " :: "

def lowLevelDetails():
    """ gather details about the process pid and thread of the calling operation """
    threadid = str(threading.current_thread().ident)
    pid = str(os.getpid())
    return {"thread_id":threadid, "pid":pid}
