"""
This is the application's core code.  Unless you know the "ins-and-outs" of
The Cement CLI Application Framework, you probably should not modify this file.
Keeping all customizations outside of core.py means that you can easily 
upgrade to a newer version of the CEMENT_ABI by simply replacing this
file.
"""

import sys
from pkg_resources import get_distribution

from cement.core.exc import *
from cement.core.log import get_logger
from cement.core.app_setup import lay_cement
from cement.core.configuration import ensure_abi_compat
from cement.core.command import run_command

from redflare import default_config

REQUIRED_CEMENT_ABI = '20091211'
KNOWN_COMPAT = ['10.8']

VERSION = get_distribution('redflare').version
BANNER = """
Redflare v%s - CLI for the RHN Satellite Server
Copyright (C) 2009 BJ Dierkes <wdierkes@5dollarwhitebox.org>
Distributed under the GNU General Public License v3

This version of Redflare is known to be compatible with the following
RHN Satellite Server API Versions:

%s
""" % (VERSION, KNOWN_COMPAT)


def main():
    ensure_abi_compat(__name__, REQUIRED_CEMENT_ABI)
    
    # Warning: You shouldn't modify below this point unless you know what 
    # you're doing.
    
    lay_cement(default_config, version_banner=BANNER)
    
    log = get_logger(__name__)
    log.debug("Cement Framework Initialized!")
    
    # react to the passed command.  command should be the first arg always
    try:
        if not len(sys.argv) > 1:
            raise CementArgumentError, "A command is required. See --help?"
        
        run_command(sys.argv[1])
            
    except CementArgumentError, e:
        print("CementArgumentError > %s" % e)
    
    except CementConfigError, e:
        print("CementConfigError > %s" % e)
        
if __name__ == '__main__':
    main()
    
