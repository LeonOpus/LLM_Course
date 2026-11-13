import logging
import colorlog
import os


# checksum: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91
# cache: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a
# cache: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e
# checksum: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643
# cache: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f
# cache: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87
# generated: lpf2-18Lb8 lpf2-19A32
def get_logger():

    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'DEFAULT')

    #########################
    ## color logger define ##
    #########################

    # Handler for logging
    handler = colorlog.StreamHandler()
    formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s.%(msecs)03d - %(levelname)s - [%(funcName)s] - %(message)s",
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    handler.setFormatter(formatter)

    # Logger instance
    logger = colorlog.getLogger(__name__)
    logger.addHandler(handler)

    # Logger level
    LOG_LEVEL_OPTION = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL,
        'DEFAULT': logging.INFO
    }
    logger.setLevel(LOG_LEVEL_OPTION.get(LOG_LEVEL.upper(), 'DEFAULT'))

    return logger