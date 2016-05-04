#!/usr/bin/env python

import os
import platform
import sys
import logging
import urllib2

############################################

INSTALL_DIR = os.getcwd()

REPO_NAME = 's3sync.py'
GITHUB_MASTER = 'https://raw.githubusercontent.com/khilnani/%s/master/' % REPO_NAME
SCRIPT_NAME = 's3sync.py'

############################################

machine = platform.machine()
print 'Platform system:' + machine

print('Installing to: %s' % INSTALL_DIR)

if 'iP' in machine:
    BASE_DIR = os.path.expanduser('~/Documents')
else:
    BASE_DIR = os.getcwd()

############################################

try:
    import console
except ImportError:
    class console (object):
        @staticmethod
        def hud_alert(message, icon=None, duration=None):
            print message

        @staticmethod
        def input_alert(title, message=None, input=None, ok_button_title=None, hide_cancel_button=False):
            message = '' if message == None else message
            ret = input
            try:
                ret = raw_input(title + '' + message + ' :')
            except Exception as e:
                print e
            return ret

############################################

def setup_logging(log_level='INFO'):
    log_format = "%(message)s"
    logging.addLevelName(15, 'FINE')
    logging.basicConfig(format=log_format, level=log_level)

def download_file(src, dest):
    logging.info('Downloading %s' % (src))
    file_content = urllib2.urlopen(src).read()
    logging.info('Writing %s' % dest)
    f = open(dest, 'w')
    f.write(file_content)
    f.close()

############################################

def download():
    download_file(GITHUB_MASTER+SCRIPT_NAME, os.path.join(INSTALL_DIR, SCRIPT_NAME))
    logging.info('Done.')

############################################

def main():
    setup_logging()
    download()

############################################

if __name__ == '__main__':
    main()