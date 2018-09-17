# from urllib.parse import urlparse
# from urllib.request import Request, urlopen
# from urllib.error import URLError, HTTPError
from urlparse import urlparse
from urllib2 import Request, urlopen
from urllib2 import URLError, HTTPError
import time
import random
import logging
import os.path
import shutil
import sys
import yaml

from datetime import datetime
from distutils import dir_util

"""
Author: Aaron O'Hehir
Date: 10/03/2017

This script tests that the ACTmapi services are up.

The script is run hourly as a job in Jenkins.
If any services are down Jenkins fires a warning email to ACTmapi admins. 

"""

def main():
    """Entry point to the porgram"""
    config = load_yml("config.yml")
    config["root_dir"] = "workspace"
    logger = init_logger(config)
    
    sanity_check = "pass"
    
    inRestDirList = config["rest_endpoints"]
    for inRestDir in inRestDirList:
        try:
            # Get domain
            parsed_uri = urlparse( inRestDir )
            domain = '{uri.scheme}://{uri.netloc}'.format(uri=parsed_uri)
            
            # Opens a request on the url and returns the html from it.
            req = Request(inRestDir)
            response = urlopen(req)
            
            # The returned information is in bytes and needs to be decoded to be interpreted.
            html_list = response.read().decode("utf-8").split('\n')
            
            links_list = []
            for link in html_list:
                if ('<li>' in link):
                    links_list.append(link)
            
            for link in links_list:
                url = link.split('href="')[1].split('">')[0]
                links_list[links_list.index(link)] = url
			
            for rest_service in links_list:
                response = urlopen(domain + rest_service)
                logging.info(response.code)
                print(response.code)
                html = response.read().decode("utf-8")
                
                try:
                    conn = urlopen(domain + rest_service)
                except HTTPError as e:
                    # Return code error (e.g. 404, 501, ...)
                    logging.info(e.code)
                    print(e.code)
                    sanity_check = "fail"
                except URLError as e:
                    # Not an HTTP-specific error (e.g. connection refused)
                    logging.info('URLError: ' + e.reason)
                    print('URLError: ' + e.reason)
                    sanity_check = "fail"
                else:
                    # Code = 200; client/server connection is ok
                    # Now test for errors in arcserver service
                    if ('errorLabel' in html):
                        logging.info('ERROR ArcServer service down: ' + domain + rest_service)
                        print('ERROR ArcServer service down: ' + domain + rest_service)
                        sanity_check = "fail"
                    else:
                        # Fixes url because web service is up.
                        logging.info('Service up: ' + domain + rest_service)
                        print('Service up: ' + domain + rest_service)
                time.sleep(random.uniform(0.75,1.25))
        except Exception as e:
            log_error(logger, e)
            raise e
    logger.info("Sanity check is %s", sanity_check)            
    return sanity_check

def log_error(logger, error):
    """Log exception"""
    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    logger.error("Exception at line:%s in %s", exc_tb.tb_lineno, fname)
    logger.error(error)

def load_yml(config_file):
    """Load the application conifguration file"""
    stream = open(config_file, 'r')
    return yaml.load(stream)

def init_logger(config):
    """ Initialize logger with a file and console output"""
    logger = logging.getLogger("Sanity Check")
    logger.setLevel(logging.INFO)
    
    # Create file handler which logs even debug messages
    log_dir = os.path.join(config["root_dir"], "logs")
    dir_util.mkpath(log_dir)
    log_name = time.strftime("%H%M%S") + "_" + time.strftime(
        "%Y%m%d") + "_sanityCheckLog.txt"
    file_handler = logging.FileHandler(os.path.join(log_dir, log_name))
    file_handler.setLevel(logging.INFO)
    
    # Create console handler with a higher log level
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create formatter and add it to the handlers
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # add the handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger

if __name__ == "__main__":
    sanity = main()
    if sanity.lower() != "pass":
        sys.exit(1)
