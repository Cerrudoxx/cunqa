import logging
import sys

# ANSI color codes
RESET = "\033[0m"       # Reset color to default
RED = "\033[31m"        # Red for ERROR
YELLOW = "\033[33m"     # Yellow for WARNING
BLUE = "\033[34m"       # Blue for DEBUG
GREEN = "\033[32m"      # Green for INFO
BRIGHT_RED = "\033[31m\033[1m" # Bright red for CRITICAL

class ColoredFormatter(logging.Formatter):
    """A logging formatter that adds colors, converts levels to lowercase, and
    includes the full file path and line number for errors.

    Attributes:
        LEVEL_COLOR (dict): A mapping of logging levels to ANSI color codes.
    """

    LEVEL_COLOR = {
        logging.DEBUG: BLUE,
        logging.INFO: GREEN,
        logging.WARNING: YELLOW,
        logging.ERROR: BRIGHT_RED,
        logging.CRITICAL: RED,
    }

    def format(self, record):
        """Formats the log record with colors and additional information.

        Args:
            record (logging.LogRecord): The log record to format.

        Returns:
            str: The formatted log message.
        """
        color = self.LEVEL_COLOR.get(record.levelno, RESET)
        levelname_lower = record.levelname.lower()

        original_levelname = record.levelname
        record.levelname = levelname_lower

        message = super().format(record)

        record.levelname = original_levelname

        if record.levelno >= logging.ERROR:
            file_info = f"{record.pathname}:{record.lineno}\n"
            colored_message = f"{color}{message}{RESET}"
            message = f"{file_info}{colored_message}"
        else:
            if color:
                message = f"{color}{message}{RESET}"

        return message

logger = logging.getLogger('colored_logger')
logger.setLevel(logging.WARN)
logger.propagate = False
logger.handlers.clear()

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.WARN)

formatter = ColoredFormatter('\t%(levelname)s: [%(filename)s] %(message)s\n')
console_handler.setFormatter(formatter)

logger.addHandler(console_handler)

logger.info('Logger created.')
