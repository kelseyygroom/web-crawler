from configparser import ConfigParser
from argparse import ArgumentParser

from utils.server_registration import get_cache_server
from utils.config import Config
from crawler import Crawler
from scraper import create_report
import sys
import signal

def main(config_file, restart):
    cparser = ConfigParser()
    cparser.read(config_file)
    config = Config(cparser)
    config.cache_server = get_cache_server(config, restart)
    crawler = Crawler(config, restart)
    crawler.start()

def create_report_on_exit(signal, frame):
    print("Ctrl+C: killed program. Saving scraper data and creating report")
    create_report()
    sys.exit(0)

signal.signal(signal.SIGINT, create_report_on_exit)   # save report data even on Ctrl+C when caught in trap. so atleast i can have partial data

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--restart", action="store_true", default=False)
    parser.add_argument("--config_file", type=str, default="config.ini")
    args = parser.parse_args()
    main(args.config_file, args.restart)
    create_report()
