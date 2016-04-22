#!/usr/bin/env python
# coding: utf-8

"""
Description:
A python script to backup and restore files from the working directory 
to an Amazon AWS S3 backup. While designed for the iOS Pythonista application, 
the script supports usage on a linux/mac os environment to share code between 
the iOS Pythonista app and a regular laptop/server.

License:
The MIT License (MIT)
Copyright (c) 2016 Nik Khilnani

Github:
https://github.com/khilnani/s3sync.py

Configuration:
- Setup ~/.aws/ AWS Credentials/Config, or boto.cfg, OR
- Rename 's3sync.sample.conf' to 's3sync.conf' and update values
"""

import platform
import os
import sys
import shutil
import tarfile
import logging
import datetime
import json
import urllib2

###########################################
############################################

__version__ = '0.3.3'
print 'Version: ' + __version__

if os.environ.get('LC_CTYPE', '') == 'UTF-8':
    os.environ['LC_CTYPE'] = 'en_US.UTF-8'

machine = platform.machine()
print 'Platform: ' + machine

###########################################
############################################

if 'iP' in machine:
    import console
    import ui

    BASE_DIR = os.path.expanduser('~/Documents')
   
    class OptionsTableView(object):
        def __init__(self, title='Options', data=None, callback=None):
            self.view = ui.TableView(frame=(0, 0, 640, 640))
            self.view.name = title
            self.data_list = None
            self.callback = callback
            self.load(data)
    
        def load(self, data=None):
            self.data_list = ui.ListDataSource(data)
            self.data_list.move_enabled = False
            self.data_list.delete_enabled = False
            self.view.data_source = self.data_list
            self.view.delegate = self
            self.view.reload()
            self.view.present('fullscreen', animated=False)

        @ui.in_background
        def tableview_did_select(self, tableview, section, row):
            # Called when a row was selected.
            sel = self.data_list.items[row]
            if sel:
                console.alert('Confirm action: \n%s' % sel, button1='Yes')
                self.view.close()
                self.callback(sel)
    
        def tableview_did_deselect(self, tableview, section, row):
            # Called when a row was de-selected (in multiple selection mode).
            pass
    
        def tableview_title_for_delete_button(self, tableview, section, row):
            # Return the title for the 'swipe-to-***' button.
            return 'Delete'
else:
    BASE_DIR = os.getcwd()

    class console (object):
        @staticmethod
        def hud_alert(message, icon=None, duration=None):
            print message

        @staticmethod
        def input_alert(title, message=None, input=None, ok_button_title=None, hide_cancel_button=False):
            message = '' if message == None else message
            ret = input
            try:
                ret = raw_input(title + '' + message + ': ')
            except Exception as e:
                print e
            return ret

############################################
############################################

def install_stash():
    try:
        from stash import stash
        return True
    except ImportError:
        import requests as r
        print 'Downloading Stash ...'
        exec r.get('http://bit.ly/get-stash').text
    try:
        from stash import stash
        return True
    except ImportError:
        return False
    
    return False

def install_boto():
    try:
        import boto
        from boto.s3.key import Key
        from boto.s3.bucket import Bucket
        return True
    except ImportError:
        if install_stash():
            from stash import stash
            _stash = stash.StaSh()
            print('StaSh version: ' + str(stash.__version__))
            print('Installing AWS boto library ...')
            _stash('pip install boto')
            print('AWS boto library installed.')
            print('Please restart Pythonista and re-run this script') 
    try:
        import boto
        from boto.s3.key import Key
        from boto.s3.bucket import Bucket
        return True
    except ImportError:
        return False

def install_awscli():
    try:
        import awscli.clidriver
        return True
    except ImportError:
        if install_stash():
            from stash import stash
            _stash = stash.StaSh()
            print('StaSh version: ' + str(stash.__version__))
            print('Installing AWS CLI library ...')
            _stash('pip install awscli')
            print('AWS CLI installed.')
            print('Please restart Pythonista and re-run this script')
    try:
        import awscli.clidriver
        return True
    except ImportError:
        return False        

try:
    import boto
    from boto.s3.key import Key
    from boto.s3.bucket import Bucket
except ImportError as ie:
    if 'iP' in machine:
        install_boto()
    elif 'x86_64' in machine:
        print('Please run: pip install boto awscli')
    sys.exit()

############################################
############################################

print('BASE_DIR: %s' % BASE_DIR)

BACKUP_EXT = '.tar.bz2'
DEFAULT_BACKUP_NAME = 's3sync_backup'

BACKUP_NAME = None
BACKUP_COPY = None
BACKUP_FILE = None

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
CONF_SAMPLE_NAME = 's3sync.sample.conf'
CONF_NAME = 's3sync.conf'
CONF_FILE = os.path.join(SCRIPT_DIR, CONF_NAME)
TEST_NAME = '.s3test'
TEST_ARCHIVE_NAME = TEST_NAME+'.tar.bz2'
TEST_ARCHIVE = os.path.join(BASE_DIR, TEST_ARCHIVE_NAME)

GITHUB_MASTER = 'https://raw.githubusercontent.com/khilnani/s3sync.py/master/'
SCRIPT_NAME = 's3sync.py'

############################################
############################################

def setup_logging(log_level='INFO'):
    log_format = "%(message)s"
    logging.addLevelName(15, 'FINE')
    logging.basicConfig(format=log_format, level=log_level)

def setup_backup_file_config(conf):
    global BACKUP_NAME, BACKUP_COPY, BACKUP_FILE
    name = DEFAULT_BACKUP_NAME
    if conf != None and conf['S3SYNC_BACKUP']:
        name = conf['S3SYNC_BACKUP']
    BACKUP_NAME = name + BACKUP_EXT
    BACKUP_COPY = name + '.{:%Y%m%d_%H%M%S}'.format(datetime.datetime.now()) + BACKUP_EXT
    BACKUP_FILE = os.path.join(BASE_DIR, BACKUP_NAME)

def get_bucket_name(conf):
    if conf['S3SYNC_AWS_S3_BUCKET']:
        return conf['S3SYNC_AWS_S3_BUCKET']
    else:
        bucket_name = console.input_alert('S3 bucket name: ', '', '')
        return bucket_name

def load_config():
    try:
        with open(CONF_FILE, 'r') as conf_file:
            conf = json.load(conf_file)
            for key in conf:
                os.environ[key] = conf[key]
            logging.info('%s loaded.' % CONF_NAME)
            return conf
    except Exception as e:
        logging.warning('No %s, using AWS Credentials/Config' % CONF_NAME)
    return None

def friendly_path(name):
    friendly = name
    if BASE_DIR in name:
        friendly = name.split(BASE_DIR)[-1]
    if friendly == '':
        friendly = '/'
    return friendly

def show_progress(num, total):
    per = int(num * 100/total)
    logging.info('  {}% completed'.format(per))

def exclude_from_remove(full_path):
    # match name and path
    exact_list = ['/.Trash', '/Examples', '/.git']
    # match name, in any path
    any_list = [SCRIPT_NAME, CONF_NAME]
    
    if friendly_path(full_path) in exact_list:
        return True
    for p in any_list:
        if p in friendly_path(full_path):
            return True
    return False

# evaluates only top level against exclude
def delete_dir_content(from_dir, exclude=None, dry_run=False):
    pre_msg = 'DRY RUN: ' if dry_run else ''
    logging.info('%sDeleting files from %s' % (pre_msg, friendly_path(from_dir)))
    try:
        for f in os.listdir(from_dir):
            full_path = os.path.join(from_dir,f)
            if exclude and exclude(full_path):
                logging.info('%sSkipping %s' % (pre_msg, friendly_path(full_path)))
            elif not dry_run:
                if os.path.isdir(full_path):
                    shutil.rmtree(full_path)
                else:
                    os.remove(full_path)
    except Exception as e:
        logging.error('Error deleting directory content: %s' % from_dir)
        logging.error(e)

# assume dir is already empty, delete if not in exclude
def remove_path(full_path, rel_path=None, exclude=None, dry_run=False):
    pre_msg = 'DRY RUN: ' if dry_run else ''
    if rel_path:
        full_path = os.path.join(full_path, rel_path)
    if exclude and exclude(full_path):
        logging.info('  %sSkipping %s' % (pre_msg, friendly_path(full_path)))
    else:
        #logging.info('  %sRemoving %s' % (pre_msg, friendly_path(full_path)))
        try:
            if not dry_run:
                if os.path.isdir(full_path):
                    os.rmdir(full_path)
                else:
                    os.remove(full_path)
        except Exception as e:
            logging.error(e)

# evaluates each file in the directory tree against exclude
def deltree_dir_content(from_dir, exclude=None, dry_run=False):
    pre_msg = 'DRY RUN: ' if dry_run else ''
    logging.info('%sRemoving files from %s' % (pre_msg, friendly_path(from_dir)))
    try:
        for dirpath, dirnames, filenames in os.walk(from_dir, topdown=False):
            for f in filenames:
                remove_path(dirpath, f, exclude, dry_run)
            for d in dirnames:
                remove_path(dirpath, d, exclude, dry_run)
    except Exception as e:
        logging.error('Error removing directory content: %s' % from_dir)
        logging.error(e)

def download_file(src, dest):
    logging.info('Reading %s' % (src))
    file_content = urllib2.urlopen(src).read()
    logging.info('Writing %s' % dest)
    f = open(dest, 'w')
    f.write(file_content)
    f.close()
    logging.info('Done.')

def remove_archive(archive_file):
    try:
        os.remove(archive_file)
    except:
        logging.info('No local archive %s found.' % friendly_path(archive_file))
    else:
        logging.info('Local archive %s removed.' % friendly_path(archive_file))

def exclude_from_tar(file_path):
    excludes = ['/Icon', '/.DS_Store', '/.Trash', '/Examples', '/.git', '/'+TEST_NAME, '/'+TEST_ARCHIVE_NAME, '/'+BACKUP_NAME]
    friendly_file_path = friendly_path(file_path)
    for name in excludes:
        if (name == friendly_file_path):
            logging.info('Skipping %s' % friendly_file_path)
            return True
    return False

def make_tarfile(filename, source_dir):
    logging.info('Creating %s ...' % friendly_path(filename))
    with tarfile.open(filename, "w:bz2") as tar:
        tar.add(source_dir, arcname='.', exclude=exclude_from_tar)
    sz = os.path.getsize(filename) >> 20
    logging.info('Created %iMB %s' % (sz, friendly_path(filename) ))

def extract_tarfile(filename, dest_dir):
    logging.info('Extracting %s to %s ...' % (friendly_path(filename), friendly_path(dest_dir)))
    try:
        fl = tarfile.open(filename, "r:bz2")
        fl.extractall(dest_dir)
        logging.info('Archive extracted.')
    except IOError:
        logging.error('Archive extraction error.')
        logging.error(e)

def list_tarfile(filename, dest_dir):
    logging.info('Listing %s ...' % friendly_path(filename))
    try:
        fl = tarfile.open(filename, "r:bz2")
        fl.list(verbose=False)
        logging.info('Listing complete.')
    except IOError:
        logging.info('Archive not found.')

############################################

def bucket_exists(s3, bucket_name):
    logging.info("Connecting to S3: %s" % bucket_name)
    bucket_exists = s3.lookup(bucket_name)
    if bucket_exists is None:
        logging.error("Bucket %s does not exist.", bucket_name)
        logging.info("Following buckets found:")
        for b in s3.get_all_buckets():
            logging.info('  %s' % b.name)
        logging.info("Aborting sync.")
        return False
    return True

def test_upload(s3, bucket_name):
    logging.info('Testing upload of %s to S3 ...' % TEST_NAME)
    bucket = s3.get_bucket(bucket_name)
    k = bucket.get_key(TEST_NAME, validate=False)
    k.set_contents_from_string(TEST_NAME, replace=True, cb=show_progress, num_cb=200)
    logging.info('Upload test complete.')

def test_download(s3, bucket_name):
    logging.info('Testing download of %s from S3 ...' % TEST_NAME)
    bucket = s3.get_bucket(bucket_name)
    k = bucket.get_key(TEST_NAME, validate=True)
    content = k.get_contents_as_string(cb=show_progress, num_cb=200)
    if content != TEST_NAME:
        logging.error('Test file %s read from S3 is not the one created.' % TEST_NAME)
    logging.info('Download test complete.')

def upload_archive(s3, bucket_name, key, fl):
    logging.info('Uploading to S3 ...')
    bucket = s3.get_bucket(bucket_name)
    k = bucket.get_key(key , validate=False)
    k.set_contents_from_filename(fl, replace=True, cb=show_progress, num_cb=200)
    logging.info('Upload complete.')

def snapshot_archive(s3,bucket_name, key, dest_key):
    logging.info('Creating remote backup snapshot ...')
    bucket = s3.get_bucket(bucket_name)
    k = bucket.get_key(key, validate=True)
    if k:
        k.copy(bucket_name, dest_key)
        logging.info('Snapshot created.')
    else:
        logging.info('No remote backup found.')

def download_archive(s3, bucket_name, key, fl):
    logging.info('Downloading from S3 ...')
    bucket = s3.get_bucket(bucket_name)
    k = bucket.get_key(key , validate=True)
    k.get_contents_to_filename(fl, cb=show_progress, num_cb=200)
    logging.info('Download complete.')

############################################

def update_script():
    download_file(GITHUB_MASTER+SCRIPT_NAME, os.path.join(SCRIPT_DIR, SCRIPT_NAME))

def aws_configure():
    if install_awscli():
        import awscli.clidriver
        sys.argv.append('configure')
        return awscli.clidriver.main()

def setup_conf_file():
    download_file(GITHUB_MASTER+CONF_SAMPLE_NAME, os.path.join(SCRIPT_DIR, CONF_NAME))
    logging.info('Please edit %s with your AWS credentials.' % CONF_NAME)

def dry_run(s3, bucket_name):
    remove_archive(TEST_ARCHIVE)
    make_tarfile(TEST_ARCHIVE, BASE_DIR)
    extract_tarfile(TEST_ARCHIVE, os.path.join(BASE_DIR, TEST_NAME))
    test_upload(s3, bucket_name)
    test_download(s3, bucket_name)

def update(s3, bucket_name):
    remove_archive(BACKUP_FILE)
    download_archive(s3, bucket_name, BACKUP_NAME, BACKUP_FILE)
    extract_tarfile(BACKUP_FILE, BASE_DIR)
    #remove_archive(BACKUP_FILE)

def restore(s3, bucket_name):
    delete_dir_content(BASE_DIR, exclude=exclude_from_remove, dry_run=False)
    update(s3, bucket_name)

def backup(s3, bucket_name):
    remove_archive(BACKUP_FILE)
    make_tarfile(BACKUP_FILE, BASE_DIR)
    upload_archive(s3, bucket_name, BACKUP_NAME, BACKUP_FILE)
    #remove_archive(BACKUP_FILE)

def snapshot(s3, bucket_name):
    snapshot_archive(s3, bucket_name, BACKUP_NAME, BACKUP_COPY)

############################################
############################################

actions_list = [
    'backup: Copy/overwrite to S3',
    'snapshot: Create a copy of remote backup',
    'update: Update/overwrite local from S3',
    'restore: Delete local and update from S3',
    '',
    'dry run: Test setup',
    'setup aws: AWS credentials',
    'setup conf: Custom config file',
    '',
    'archive: Create a local backup', 
    'extract: Extract local backup',
    'list: List files in local backup',
    'update script: Get latest %s' % SCRIPT_NAME
    ]

def execute_action(action):
    action = action.split(':')[0] if action else None
    logging.info('Executing action: ' + str(action))
    
    cfg = load_config()
    setup_backup_file_config(cfg)

    if action == None or action.strip() == '':
        logging.warning('No action specified.')
    elif action == 'update script':
        update_script()
    elif action == 'list':
        list_tarfile(BACKUP_FILE, BASE_DIR)
    elif action == 'archive':
        remove_archive(BACKUP_FILE)
        make_tarfile(BACKUP_FILE, BASE_DIR)
    elif action == 'extract':
        extract_tarfile(BACKUP_FILE, BASE_DIR)
    elif action == 'setup aws':
        aws_configure()
    elif action == 'setup conf':
        setup_conf_file()
    else:
        bucket_name = get_bucket_name(cfg)
        s3 = boto.connect_s3()
        # check if bucket exists
        if not bucket_exists(s3, bucket_name):
            sys.exit()
        if action == 'dry run':
            dry_run(s3, bucket_name)
        elif action == 'update':
            update(s3, bucket_name)
        elif action == 'restore':
            restore(s3, bucket_name)
        elif action == 'backup':
            backup(s3, bucket_name)
        elif action == 'snapshot':
            snapshot(s3, bucket_name)
        else:
            logging.warning('No matching action found.')

def get_ios_user_selection():
    options = OptionsTableView(data=actions_list, title='Select an action', callback=execute_action)

def get_default_user_selection():
    mode = None
    if len(sys.argv) > 1:
        mode =sys.argv[1]
    else:
        selections = '\n'.join(actions_list) + '\n'
        mode = console.input_alert('\nPlease type an action:\n\n', selections)
    execute_action(mode)

def get_user_selection():
    sel = None
    if len(sys.argv) > 1:
        sel = sys.argv[1]
    elif 'iP' in machine:
        get_ios_user_selection()
    else:
        get_default_user_selection()

############################################

def main():
    setup_logging()
    get_user_selection()

############################################
############################################

if __name__ == '__main__':
    main()
