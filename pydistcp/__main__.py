#!/usr/bin/env python
# encoding: utf-8

"""pydistcp: A python Web HDFS based tool for inter/intra-cluster data copying.

Usage:
  pydistcp [-fp] [--files-only] [--no-checksum] [--silent] (-s CLUSTER -d CLUSTER) [-v...] [--part-size=PART_SIZE] [--include-pattern=PATTERN] [--threads=THREADS] SRC_PATH DEST_PATH
  pydistcp (--version | -h)

Options:
  --version                     Show version and exit.
  -h --help                     Show help and exit.
  -s CLUSTER --src=CLUSTER      Alias of source namenode to connect to (valid only with dist).
  -d CLUSTER --dest=CLUSTER     Alias of destination namenode to connect to (valid only with dist).
  -v --verbose                  Enable log output. Can be specified up to three
                                times (increasing verbosity each time).
  --no-checksum                 Disable checksum check prior to file transfer. This will force
                                overwrite.
  --files-only                  Do not create the same directory strecture at the destination and copy
                                files only under DEST_PATH.
  --silent                      Don't display progress status.
  -f --force                    Allow overwriting any existing files.
  -p --preserve                 Preserve file attributes.
  --threads=THREADS             Number of threads to use for parallelization.
                                0 allocates a thread per file. [default: 0]
  --include-pattern=PATTERN     Filter input files based on a pattern.
  --part-size=PART_SIZE         Interval in bytes by which the files will be copied
                                needs to be a Powers of 2. [default: 65536]     

Examples:
  pydistcp -s prod -d preprod -v /tmp/src /tmp/dest

"""

from . import __version__
from pywhdfs.config import WebHDFSConfig
from pywhdfs.utils.utils import *
from docopt import docopt
from .distclient import WebHDFSDistClient
from .utils import _Progress
import logging as lg
import requests as rq
import json
import sys

def configure(args):
  """Instantiate configuration from arguments dictionary.

  :param args: Arguments returned by `docopt`.
  :param config: CLI configuration, used for testing.

  If the `--log` argument is set, this method will print active file handler
  paths and exit the process.

  """
  # capture warnings issued by the warnings module  
  try:
    # This is not available in python 2.6
    lg.captureWarnings(True)
  except:
    # disable annoying url3lib warnings
    rq.packages.urllib3.disable_warnings()
    pass

  logger = lg.getLogger()
  logger.setLevel(lg.DEBUG)
  # lg.getLogger('requests_kerberos.kerberos_').setLevel(lg.INFO)
  # logger.addFilter(AnnoyingErrorsFilter())

  levels = {0: lg.CRITICAL, 1: lg.ERROR, 2: lg.WARNING, 3: lg.INFO}

  # Configure stream logging if applicable
  stream_handler = lg.StreamHandler()
  # This defaults to zero
  stream_log_level=levels.get(args['--verbose'], lg.DEBUG)
  stream_handler.setLevel(stream_log_level)

  fmt = '%(levelname)s\t%(message)s'
  stream_handler.setFormatter(lg.Formatter(fmt))
  logger.addHandler(stream_handler)

  config = WebHDFSConfig()

  # configure file logging if applicable
  handler = config.get_log_handler()
  logger.addHandler(handler)
  return config

def main(argv=None):
  """Entry point.
  :param argv: Arguments list.
  :param client: For testing.
  """

  args = docopt(__doc__, argv=argv, version=__version__)

  config = configure(args)

  n_threads = int(args['--threads'])
  part_size = int(args['--part-size'])
  include_pattern = args['--include-pattern']
  force = args['--force']
  silent = args['--silent']
  checksum = False if args['--no-checksum'] else True
  files_only = True if args['--files-only'] else False
  src_path = args['SRC_PATH']
  dest_path = args['DEST_PATH']

  if args["--src"] != 'local' and args["--dest"] != 'local':
    src_client = config.get_client(args["--src"])
    dest_client = config.get_client(args["--dest"])
    client = WebHDFSDistClient(src_client, dest_client)

    if sys.stderr.isatty() and not silent:
      progress = _Progress.from_hdfs(client.src,src_path)
    else:
      progress = None

    status = client.copy(
              src_path,
              dest_path,
              overwrite=force,
              checksum=checksum,
              chunk_size=part_size,
              n_threads=n_threads,
              progress=progress,
              preserve= True if args['--preserve'] else False,
            )

    print "Job Status:"
    print json.dumps(status, indent=2)

  elif args["--src"] == 'local' and args["--dest"] != 'local':
    client = config.get_client(args["--dest"])
    if sys.stderr.isatty() and not silent:
      progress = _Progress.from_local(src_path)
    else:
      progress = None

    client.upload(
      dest_path,
      src_path,
      overwrite=force,
      checksum=checksum,
      chunk_size=part_size,
      n_threads=n_threads,
      progress=progress,
      include_pattern=include_pattern,
      files_only=files_only,
      preserve= True if args['--preserve'] else False,
    )    

  elif args["--src"] != 'local' and args["--dest"] == 'local':
    client = config.get_client(args["--src"])
    if sys.stderr.isatty() and not silent:
      progress = _Progress.from_hdfs(client,src_path)
    else:
      progress = None

    client.download(
      src_path,
      dest_path,
      overwrite=force,
      chunk_size=part_size,
      n_threads=n_threads,
      progress=progress,
      preserve= True if args['--preserve'] else False,
    )
  else:
    print('copy from local to local is not supported, use cp command.')
    sys.exit(1)

  sys.exit(0)
  

if __name__ == '__main__':
  main()
