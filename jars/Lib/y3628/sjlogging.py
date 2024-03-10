'''

Logging with [scijava/LogService used by ImageJ2/Fiji][ij_logging]. Allows logging 
information to the Console/Log dialog of ImageJ2.

[SciJava LOGLEVEL (value)][sj_logging]
    ----------
    ERROR (1)
    WARN (2)
    INFO (3)
    DEBUG (4)
    TRACE (5)

# Example usage

```python

import y3628.sjlogging as sjlog

# Initialize SJLogger
#@ LogService sjlogservice
sjlog.init(sjlogservice)

log_main = SJLogger("main")
log_sub = SJLogger("main:sub")
log2 = SJLogger("secondary")

# Logging in different ways for level 'ERROR'
log_main.log(1, record)
log_main.log('ERROR', record)
log_main.log('E', record)
log_main.error(record)
#   other levels:
#       2/'WARN'/'W' or log_main.warn
#       3/'INFO'/'I' or log_main.info
#       4/'DEBUG'/'D' or log_main.debug
#       5/'TRACE'/'T' or log_main.trace

# Logging in different sources
log_sub.log(1, "error from sublogger of main")
log2.log(1, "error from logger2")

```

# Known limitation

Log level cannot be adjusted at runtime. Call `sjLogService.setLevel()` is not functional.

[ij_logging]: https://imagej.net/Logging
[sj_logging]: https://github.com/scijava/scijava-common/tree/master/src/main/java/org/scijava/log

'''

sjLogService = None

def init(sjLogServ):
    global sjLogService
    if sjLogService is None:
        sjLogService = sjLogServ
        sjLogService.setLevel(3) # Log INFO and above
    else:
        raise Exception("SciJava LogService is already initialized")

def init_check():
    global sjLogService
    if sjLogService is None:
        raise Exception("SciJava LogService is not initialized")

def subLogger(name):
    global sjLogService
    init_check()
    return sjLogService.subLogger(name)

def setLevel(level):
    global sjLogService
    sjLogService.setLevel(level)

logLevelMap = {
    "ERROR": 1, "E": 1, 1:1,
    "WARN": 2, "W": 2, 2:2,
    "INFO": 3, "I": 3, 3:3,
    "DEBUG": 4, "D": 4, 4:4,
    "TRACE": 5, "T": 5, 5:5
}

class SJLogger:
    def __init__(this, name):
        global subLogger
        this.logger = subLogger(name)
    def log(this, level, record):
        global logLevelMap
        try:
            ll = logLevelMap[level]
        except KeyError:
            raise Exception("Unsupported log level")
        this.logger.log(ll, record)
    
    def tempDebug(this,record):
        #temporarily enable debug log level
        global setLevel
        global sjLogService
        currLevel = sjLogService.getLevel()
        setLevel(4)
        this.logger.log(4, record)
        setLevel(currLevel)
    def error(this,record):
        this.logger.log(1, record)
    def warn(this,record):
        this.logger.log(2, record)
    def info(this,record):
        this.logger.log(3, record)
    def debug(this,record):
        this.logger.log(4, record)
    def trace(this,record):
        this.logger.log(5, record)
