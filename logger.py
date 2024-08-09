#!/usr/bin/env python
#!encoding:UTF-8

import logging
import os
import re
import inspect
from rich.logging import RichHandler
from rich.text import Text
from rich.console import Console
console = Console()
from rich import traceback as rich_traceback
import shutil
rich_traceback.install(theme = 'fruity', max_frames = 30, width = shutil.get_terminal_size()[0])

class CustomFormatter(logging.Formatter):

    info = "\x1b[32;20m"
    debug = "\x1b[33;20m"
    fatal = "\x1b[44;97m"
    error = "\x1b[41;97m"
    warning = "\x1b[43;30m"
    critical = "\x1b[45;97m"
    reset = "\x1b[0m"
    format = "%(asctime)s - %(name)s - %(process)d - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: debug + format + reset,
        logging.INFO: info + format + reset,
        logging.WARNING: warning + format + reset,
        logging.ERROR: error + format + reset,
        logging.CRITICAL: critical + format + reset, 
        logging.FATAL: fatal + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def setup_logging_custom():
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger()

    # Update the handlers of the root logger
    for handler in logger.handlers:
        handler.setFormatter(CustomFormatter())


# Define EMERGENCY level
EMERGENCY_LEVEL = logging.CRITICAL + 10
FATAL_LEVEL = EMERGENCY_LEVEL + 1
CRITICAL_LEVEL = FATAL_LEVEL + 1
ALERT_LEVEL = CRITICAL_LEVEL + 1
NOTICE_LEVEL = ALERT_LEVEL + 1

logging.addLevelName(EMERGENCY_LEVEL, "EMERGENCY")
logging.addLevelName(FATAL_LEVEL, "FATAL")
logging.addLevelName(CRITICAL_LEVEL, "CRITICAL")
logging.addLevelName(ALERT_LEVEL, "ALERT")
logging.addLevelName(NOTICE_LEVEL, "NOTICE")

def emergency(self, message, *args, **kwargs):
    if self.isEnabledFor(EMERGENCY_LEVEL):
        self._log(EMERGENCY_LEVEL, message, args, **kwargs)

def fatal(self, message, *args, **kwargs):
    if self.isEnabledFor(FATAL_LEVEL):
        self._log(FATAL_LEVEL, message, args, **kwargs)

def critical(self, message, *args, **kwargs):
    if self.isEnabledFor(CRITICAL_LEVEL):
        self._log(CRITICAL_LEVEL, message, args, **kwargs)

def alert(self, message, *args, **kwargs):
    if self.isEnabledFor(ALERT_LEVEL):
        self._log(ALERT_LEVEL, message, args, **kwargs)

def notice(self, message, *args, **kwargs):
    if self.isEnabledFor(NOTICE_LEVEL):
        self._log(NOTICE_LEVEL, message, args, **kwargs)

logging.Logger.emergency = emergency
logging.Logger.fatal = fatal  
logging.Logger.critical = critical  
logging.Logger.alert = alert  
logging.Logger.notice = notice  

class CustomRichFormatter(logging.Formatter):
    
    LEVEL_STYLES = {
        logging.DEBUG: "#ff5500",
        logging.INFO: "bold #00ffff",
        logging.WARNING: "black on #ffff00",
        logging.ERROR: "bright_white on #ff0000",
        CRITICAL_LEVEL: "bright_white on #0055ff",
        FATAL_LEVEL: "black on #00ff00",
        EMERGENCY_LEVEL: "bright_white on #aa00ff",
        ALERT_LEVEL: "black on #aaaa00",    
        NOTICE_LEVEL: "black on #00ffff",    
    }   

    def format(self, record):
        log_fmt = f"{record.name} - {record.process} - {record.levelname} - {record.getMessage()} ({record.filename}:{record.lineno})"
        level_style = self.LEVEL_STYLES.get(record.levelno, "")
        styled_message = Text(log_fmt, style=level_style)
        if isinstance(record.msg, Text):
            return record.msg
        return styled_message    

def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(message)s",  # Use a simple format here
        datefmt="[%Y-%m-%d %H:%M:%S]",
        handlers=[RichHandler(rich_tracebacks=True, show_time=True, show_level = False, tracebacks_show_locals = True, tracebacks_theme = 'fruity', tracebacks_width = shutil.get_terminal_size()[0])] 
    )

    logger = logging.getLogger()
    for handler in logger.handlers:
        if isinstance(handler, RichHandler):
            # Remove control codes before rendering to prevent errors
            handler._log_render.emojis = False
            handler.setFormatter(CustomRichFormatter())

            # Override the default render_message method to avoid strip_control_codes on Text objects
            def custom_render_message(self, record, message):
                use_markup = getattr(record, "markup", self.markup)
                if isinstance(message, Text):  # Don't apply strip_control_codes to Text objects
                    message_text = message
                else:
                    message_text = Text.from_markup(message) if use_markup else Text(message)
                return message_text

            handler.render_message = custom_render_message.__get__(handler)

def get_def():
    name = ''
    try:
        name = str(inspect.stack()[1][3])
        console.log("name 1: ", name)
    except:
        pass
    if not name:
        try:
            name = str(inspect.stack()[2][3])
            console.log("name 2: ", name)
        except:
            pass
    if not name or name == "<module>":
        the_class = None
        try:
            the_class = re.split("'|>|<|\.", str(inspect.stack()[1][0].f_locals.get('self').__class__))[-3]
            console.log("the_class: ", the_class)
        except:
            pass
        if len(inspect.stack()) > 2:
            for h in inspect.stack()[3:]:
                if isinstance(h[2], int):
                    if not h[3] == '<module>':
                        #name1 += "[%s]" % (h[3]) + " --> "
                        name = "%s" % (h[3]) + "[%s]" % (str(h[2]))  + " --> "
                        console.log("name 3: ", name)
            #defname_parent = inspect.stack()[1][3]
        if the_class and not the_class == "NoneType":
            name = "(%s)" % (the_class) + " --> "
            console.log("name 3: ", name)
            
            #defname_parent1 += "(%s)" % (the_class) + " --> "
    
    if not name or name == "<module>":
        name = os.path.basename(inspect.stack()[0].filename)
    console.log("name: ",  name)
    return name
