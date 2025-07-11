# logging_config.py  ── drop this in a module that is imported first
import logging
import logging.config
import os

# Root level – default to INFO unless you really want something chattier
root_level = os.getenv("LOG_LEVEL", "INFO").upper()

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,   # keep uvicorn, etc. intact
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    # Root logger (everything that isn’t captured below)
    "root": {"handlers": ["console"], "level": root_level},

    # Third-party libraries that are too chatty at DEBUG
    "loggers": {
        "pymongo":             {"level": "WARNING", "handlers": ["console"], "propagate": False},
        "pymongo.monitoring":  {"level": "WARNING", "handlers": ["console"], "propagate": False},
        "apscheduler":         {"level": "INFO",    "handlers": ["console"], "propagate": False},
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
