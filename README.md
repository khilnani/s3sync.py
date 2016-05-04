## s3sync.py

Backup and restore files from the working directory to an Amazon AWS S3 bucket. 

Supports both, iOS [Pythonista](http://omz-software.com/pythonista/) and Desktop Linux/Mac OS

> For example, I use this to share/sync code between my iPhone, iPad, and Mac laptop.

By default, the script backups the following locations:

- Pythonista:
  - Files downloaded to and restored from the `~/Documents` directory.
- Linux/mac os:
  - Files downloaded to and restored from the working directory, not the directory containing the script.
  - Example: Run `python s3sync.py [ACTION]`
    - `ACTION`: Optional, any of the commands displayed when the script is run.

### Configuration

- A JSON configuration file `s3sync.conf` can be used to store configurations.
- If missing, the script will prompt for information each time it is run.
- See `s3sync.sample.conf` for a full list of options. [JSON Schema](http://json-schema.org/) is used for its schema documentation.

### Usage

- Copy `s3sync.sample.conf` to the same directory as the `s3sync.py` script and rename to `s3sync.conf`
- Update config file as appropriate.

### AWS Authentication

- Since the script uses the AWS boto library, it supports all of the authentication methods boto does:
  - Environment variables, AWS Credentials, AWS Config, boto2 or boto3 configuration.
  - See [AWS boto3 Credentials Docs](http://boto3.readthedocs.org/en/latest/guide/configuration.html) for more details
- If you would like to manage the authentication configuration separately, you can add AWS credentials to  `s3sync.conf`.


## Installation

- Download or clone the github repo, or:
  - Pythonista console: `import urllib2; exec urllib2.urlopen('http://khl.io/s3sync-py').read()`
  - Linux/Mac OS Terminal: `python -c "import urllib2; exec urllib2.urlopen('http://khl.io/s3sync-py').read()"`
