"""This is the mirror plugin for redflare."""

import sys, os
import re
import xmlrpclib

from cement import namespaces
from cement.core.exc import CementConfigError, CementArgumentError
from cement.core.log import get_logger
from cement.core.opt import init_parser
from cement.core.hook import define_hook, register_hook
from cement.core.command import CementCommand, register_command
from cement.core.plugin import CementPlugin, register_plugin
from cement.helpers.cache.simple_cache import SimpleCache

from redflare import user_cache
from redflare.appmain import VERSION, BANNER
from redflare.plugins.redflare_core.proxy import RHNSatelliteProxy
from redflare.plugins.mirror.channel import RHNSatelliteChannel

log = get_logger(__name__)

REQUIRED_CEMENT_ABI = '20091211'

@register_plugin() 
class mirrorPlugin(CementPlugin):
    def __init__(self):
        CementPlugin.__init__(self,
            label = 'mirror',
            version = VERSION,
            description = 'Mirror plugin for redflare',
            required_abi = REQUIRED_CEMENT_ABI,
            version_banner = BANNER,
            config = {'merge_global_options' : True}
            )
    
@register_hook()
def options_hook(*args, **kwargs):
    """
    Pass back an OptParse object, options will be merged into mirror
    namespace.
    """
    options = init_parser()
    options.add_option('--verify', action ='store_true', 
        dest='verify', default=None, help='Verify MD5 of files (costly)'
        ) 
    return ('mirror', options)
    
@register_hook()
def validate_config_hook(*args, **kwargs):
    config = namespaces['mirror'].config
    if not config:
        print("WARNING: broken hook.  missing 'config' keyword argument.")
    else:
        required_settings = ['mirror_dir']
        for s in required_settings:
            if not config.has_key(s):
                raise CementConfigError, "config['%s'] value missing!" % s
        
        if not os.path.exists(config['mirror_dir']):
            os.makedirs(config['mirror_dir'])
           

@register_command(name='sync', namespace='mirror')
class syncCommand(CementCommand):
    config = namespaces['mirror'].config
    
    def __init__(self, *args):
        CementCommand.__init__(self, *args)
        self.proxy = RHNSatelliteProxy()
        
        if self.cli_opts.user:
            self.proxy.get_session(use_cache=False)  
    
    def mirror_channel(self, channel, path):
        local_dir = re.sub('\%\(mirror_dir\)', self.config['mirror_dir'], path)
        chan = RHNSatelliteChannel(label=channel, local_dir=local_dir) 
        log.info("mirroring of %s started" % chan.label)
        try:
            chan.sync(verify=self.cli_opts.verify)
        except KeyboardInterrupt, e:
            log.warn('Caught KeyboardInterrupt => Attempting to exit clean...')
            # remove the last file attempted
            last_path = os.path.join(chan.local_dir, chan.attempted_files[-1])
            if os.path.exists(last_path):
                log.debug('cleanup: removing last attempted file %s' % last_path)
                os.remove(last_path)
            sys.exit(1)
        log.info("mirroring of %s complete." % chan.label)
        
    def run(self):
        if len(self.cli_args) >= 3:
            channel = self.cli_args[2] 
        else:
            raise CementArgumentError, "Must pass a channel label (or 'all')"
        
        if channel == 'all':
            for c in self.config['channels']:
                self.mirror_channel(c, self.config['channels'][c]['path'])
        else:
            if self.config['channels'].has_key(channel):
                path = self.config['channels'][channel]['path']
                self.mirror_channel(channel, path)
            else:
                print "ArgumentError => channel %s doesn't exist in the config." % channel
                sys.exit(1)
