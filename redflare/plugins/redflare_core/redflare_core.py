"""This is the core plugin for redflare."""

import sys, os
import xmlrpclib

from cement import namespaces
from cement.core.exc import CementConfigError
from cement.core.log import get_logger
from cement.core.opt import init_parser
from cement.core.hook import define_hook, register_hook
from cement.core.command import CementCommand, register_command
from cement.core.plugin import CementPlugin, register_plugin

from redflare import user_cache
from redflare.appmain import VERSION, BANNER
from redflare.plugins.redflare_core.proxy import RHNSatelliteProxy

log = get_logger(__name__)

REQUIRED_CEMENT_ABI = '20091211'
        
@register_plugin() 
class redflarePlugin(CementPlugin):
    def __init__(self):
        CementPlugin.__init__(self,
            label = 'redflare',
            version = VERSION,
            description = 'Core plugin for redflare',
            required_abi = REQUIRED_CEMENT_ABI,
            version_banner = BANNER,
            )

@register_hook()
def validate_config_hook(*args, **kwargs):
    config = kwargs.get('config', None)
    if not config:
        print("WARNING: broken hook.  missing 'config' keyword argument.")
    else:
        required_settings = ['user', 'password', 'server', 'port', 'use_ssl']
        for s in required_settings:
            if not config.has_key(s):
                raise CementConfigError, "config['%s'] value missing!" % s
            
@register_hook()
def options_hook(*args, **kwargs):
    """
    Pass back an OptParse object, options will be merged into the global
    options.
    """
    global_options = init_parser()
    global_options.add_option('--user', action ='store', 
        dest='user', default=None, help='RHN user name'
        ) 
    global_options.add_option('--pass', action='store', 
        dest='password', default=None, help='RHN user password'
        ) 
    global_options.add_option('--server', action ='store', 
        dest='server', default=None, help='RHN server hostname'
        ) 
    global_options.add_option('--port', action ='store', 
        dest='port', default=None, help='RHN server port'
        )    
    return ('global', global_options)
    

@register_command(name='clearcache', namespace='global')
class clearcacheCommand(CementCommand):
    def run(self):
        log.debug('clearing cache')
        user_cache.clear_cache()
        
@register_command(name='freeform', namespace='global')
class freeformCommand(CementCommand):
    def run(self):
        """
        Takes an API path (i.e. auth.login) and args (i.e username) and
        attempts to make a call to the RHN Proxy.  Useful for development.
        """
        cmd = self.cli_args.pop(0)
        path = self.cli_args.pop(0)
        args = self.cli_args

        proxy = RHNSatelliteProxy()
        
        if self.cli_opts.user:
            proxy.get_session(use_cache=False)
        else:
            proxy.get_session()    
            
        try:
            res = proxy.call(path, *args)
        except xmlrpclib.Fault, e:
            res = proxy.noauth_call(path, *args)
        
        print
        print "Freeform API Call Output"
        print "-" * 77
        print res
        print
        
    def help(self):
        print
        print "Attempt to make an API call to the RHN Proxy:"
        print
        print "$ redflare freeform 'user.getLoggedInTime' 'johndoe'"
        print
