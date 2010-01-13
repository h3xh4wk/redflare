
from cement import namespaces
from cement.helpers.cache.simple_cache import SimpleCache
from cement.core.log import get_logger

import sys, os
from pkg_resources import get_distribution
import xmlrpclib

from redflare import user_cache
from redflare.appmain import KNOWN_COMPAT

log = get_logger(__name__)

class RHNSatelliteProxy(object):
    token = None
    server = 'rhn.example.com'
    port = '443'
    use_ssl = True
    session = None
    config = {}
    
    def __init__(self):
        global namespaces, user_cache, proxy
        self.config = namespaces['global'].config
        self.get_session()
        
    def get_session(self, use_cache=True):
        global user_cache
        if self.config['use_ssl']:
            uri = "https://%s:%s/rpc/api" % (self.config['server'], 
                                             self.config['port'])
        else:
            uri = "http://%s:%s/rpc/api" % (self.config['server'], 
                                            self.config['port'])
            
        self.session = xmlrpclib.ServerProxy(uri, allow_none=True)

        #user_cache = SimpleCache(os.path.join(os.environ['HOME'], 
        #                         '.redflare.cache'))

        if use_cache and user_cache.get('rhn_session_key'):
            # token is cached, lets validate it
            self.token = user_cache.get('rhn_session_key')
            try:
                res = self.call('user.listUsers')
            except xmlrpclib.Fault, e:
                self.token = None
                user_cache.drop('rhn_session_key')
        else:
            user_cache.drop('rhn_session_key')
            
        if not self.token:    
            # user
            if not self.config.has_key('user') or self.config['user'] == '':
                self.config['user'] = raw_input('RHN Username: ')
    
            # password
            if not self.config.has_key('password') or self.config['password'] == '':
                try:
                    os.system('stty -echo')
                    self.config['password'] = raw_input('RHN Password: ')
                    os.system('stty echo')
                    print
                except:
                    os.system('stty echo')
                    print
            
            try:
                self.token = self.session.auth.login(self.config['user'], 
                                                    self.config['password'])
            except xmlrpclib.Fault, e:
                print "xmlrpclib.Fault => %s" % e
                sys.exit(1)
                
            if self.token:
                user_cache.store('rhn_session_key', self.token)
        
        self.verify_compatibility()
    
    def verify_compatibility(self):
        res = self.session.api.getVersion()
        if res not in KNOWN_COMPAT:
            log.warn(
                "Proxy API v%s has unknown compatibility with Redflare v%s" \
                    % (res, get_distribution('redflare').version)
                )
        
    def call(self, path, *args, **kwargs):
        res = eval("self.session.%s(self.token, *args)" % path)
        return res

    def noauth_call(self, path, *args, **kwargs):
        res = eval("self.session.%s(*args)" % path)
        return res
