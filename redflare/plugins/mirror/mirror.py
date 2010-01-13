"""This is the mirror plugin for redflare."""

import sys, os
import re
import xmlrpclib
import urllib2
import hashlib

from cement import namespaces
from cement.core.exc import CementConfigError, CementArgumentError
from cement.core.log import get_logger
from cement.core.opt import init_parser
from cement.core.hook import define_hook, register_hook
from cement.core.command import CementCommand, register_command
from cement.core.plugin import CementPlugin, register_plugin
from cement.helpers.cache.simple_cache import SimpleCache

from redflare.appmain import VERSION, BANNER
from redflare.plugins.redflare_core.proxy import RHNSatelliteProxy

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
        else:
            self.proxy.get_session()    
        
    def fetch_file(self, channel, package_id, local_path):
        log.info("fetching %s/%s ...." % (channel, p['file']))
        url = self.proxy.call('packages.getPackageUrl', package_id)
        f = open(local_path, 'w')
        data = urllib2.urlopen(url).read()
        f.write(data)
        f.close()
        
    def _slow_mirror(self, package, channel, local_chan_dir):
        # this is significantly slower
        p = self.proxy.call('packages.getDetails', package['id'])
        p_full_path = os.path.join(local_chan_dir, p['file'])
        log.debug('processing %s/%s' % (channel, p['file']))
        
        if os.path.exists(p_full_path):
            log.info('verifying %s/%s' % (channel, p['file']))
            # fetch the file if md5 mismatch, and then re-verify
            count = 0
            while count < 3:
                md5 = hashlib.md5(open(p_full_path).read()).hexdigest()
                if md5 == p['md5sum']:
                    break
                else:
                    self.fetch_file(channel, p['id'], p_full_path)
                    count += 1
                if count >= 3:
                    log.error('failed to download %s/%s' % \
                        (channel, p['file']))   
        else:
            # fetch the file cause it doesn't exist
            self.fetch_file(channel, p['id'], p_full_path)
                    
            count = 0
            while count < 3:
                md5 = hashlib.md5(open(p_full_path).read()).hexdigest()
                if md5 == p['md5sum']:
                    break
                else:
                    self.fetch_file(channel, p['id'], p_full_path)
                    count += 1
                if count >= 3:
                    log.error('failed to download %s/%s' % \
                        (channel, p['file']))
    
    
    def _fast_mirror(self, package, channel, local_chan_dir):
        # this is significantly faster
        p_full_name = "%s-%s-%s.%s.rpm" % (
            package['name'], 
            package['version'], package['release'], 
            package['arch_label']
            )
        p_full_path = os.path.join(local_chan_dir, p_full_name)
        log.debug('processing %s/%s' % (channel, p_full_name))
        
        if not os.path.exists(p_full_path):
            log.info("fetching %s/%s ...." % (channel, p_full_name))
            url = self.proxy.call('packages.getPackageUrl', package['id'])
            f = open(p_full_path, 'w')
            data = urllib2.urlopen(url).read()
            f.write(data)
            f.close()
    
        
    def mirror_channel(self, channel, path):
        run_createrepo = True
        run_yumarch = False
        only_latest = True
        downloaded_files = []
        
        # base mirror config
        if self.config.has_key('run_createrepo'):
            run_createrepo = self.config['run_createrepo']
        if self.config.has_key('run_yumarch'):
            run_yumarch = self.config['run_yumarch']
        if self.config.has_key('only_latest'):
            only_latest = self.config['only_latest']
        
        # per channel config
        if self.config['channels'][channel].has_key('run_createrepo'):
            run_createrepo = self.config['channels'][channel]['run_createrepo']
        if self.config['channels'][channel].has_key('run_yumarch'):
            run_yumarch = self.config['channels'][channel]['run_yumarch']
        if self.config['channels'][channel].has_key('only_latest'):
            only_latest = self.config['channels'][channel]['only_latest']
        
        # only download the latest package, not all
        if only_latest:
            packages = self.proxy.call(
                'channel.software.listLatestPackages', channel)
        else:
            packages = self.proxy.call(\
                'channel.software.listAllPackages', channel)
                    
        local_chan_dir = re.sub('\%\(mirror_dir\)', 
                                self.config['mirror_dir'], path)
        
        log.info("mirroring %s to %s" % (channel, local_chan_dir))
        
        if not os.path.exists(local_chan_dir):
            os.makedirs(local_chan_dir)
            
        for package in packages:
            if self.cli_opts.verify:
                self._slow_mirror(package, channel, local_chan_dir)                                         
            else:
                self._fast_mirror(package, channel, local_chan_dir)
                    
        # finally, create the repo
        if run_createrepo:
            log.info("running createrepo: %s" % local_chan_dir)
            os.system("%s %s" % (self.config['createrepo_path'], local_chan_dir))
        if run_yumarch:
            log.info("running yum-arch: %s" % local_chan_dir)
            os.system("%s %s" % (self.config['yumarch_path'], local_chan_dir))
            
        # clean up files that aren't in packages
        for file in os.listdir(local_chan_dir):
            if file not in downloaded_files:
                log.debug("cleanup: os.remove('%s')" % file)
                os.remove(os.path.join(local_chan_dir, file))
        
    def run(self):
        if len(self.cli_args) >= 3:
            channel = self.cli_args[2] 
        else:
            raise CementArgumentError, "Must pass a channel label (or 'all')"
        
        if channel == 'all':
            for c in self.config['channels']:
                self.mirror_channel(c, self.config['channels'][c]['path'])
        else:
            self.mirror_channel(channel, self.config['channels'][channel]['path'])
