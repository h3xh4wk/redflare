
import sys, os
import urllib2
import hashlib

from cement import namespaces
from cement.core.log import get_logger

from redflare.plugins.redflare_core.proxy import RHNSatelliteProxy

log = get_logger(__name__)

class RHNPackage(object):
    def __init__(self, package_id, channel, **kw):
        self.config = namespaces['mirror'].config
        self.id = package_id
        self.channel = channel
        
        # get the proxy object
        if kw.get('proxy', None):
            self.proxy = kw['proxy']
        else:
            self.proxy = RHNSatelliteProxy()
        
        # if we didn't pass the file_name, we need to look it up.  but if we
        # do pass it, and lookup_details=False we safe an api call.
        if kw.get('file_name'):
            self.file = kw['file_name']
        else:
            kw['lookup_details'] = True
            
        if kw.get('lookup_details', None):
            details = self.proxy.call('packages.getDetails', package_id)
            for i in details:
                setattr(self, i, details[i])
        
        
    def fetch_file(self, local_path):
        log.info("fetching %s/%s ...." % (self.channel, self.file))
        url = self.proxy.call('packages.getPackageUrl', self.id)
        f = open(local_path, 'w')
        data = urllib2.urlopen(url).read()
        f.write(data)
        f.close()
        
class RHNSatelliteChannel(object):
    label = None
    local_dir = None
    
    def __init__(self, label=None, local_dir=None, **kw):
        self.config = namespaces['mirror'].config
        self.label = label
        self.local_dir = local_dir
        self.proxy = RHNSatelliteProxy()
        self.synced_files = []
        self.attempted_files = []
        self.modified = False
        
        # base mirror config
        self.run_createrepo = self.config.get('run_createrepo', None)
        self.run_yumarch = self.config.get('run_yumarch', None)
        self.only_latest = self.config.get('only_latest', None)
        
        # per channel config
        if self.config.has_key('channels'):
            if not self.run_createrepo:
                self.run_createrepo = self.config['channels'][self.label]\
                    .get('run_createrepo', None)
            if not self.run_yumarch:
                self.run_yumarch = self.config['channels'][self.label]\
                    .get('run_yumarch', None)
            if not self.only_latest:
                self.only_latest = self.config['channels'][self.label]\
                    .get('only_latest', None)
    
        # create out local dir if missing
        if not os.path.exists(self.local_dir):
            os.makedirs(self.local_dir)
            
    def get_packages(self):
        # only download the latest package, not all
        if self.only_latest:
            self.packages = self.proxy.call(
                'channel.software.listLatestPackages', self.label)
        else:
            self.packages = self.proxy.call(\
                'channel.software.listAllPackages', self.label)
        return self.packages
    
    def sync(self, verify=False):
        for package in self.get_packages():
            if verify:
                self._slow_sync_package(package)                                         
            else:
                self._fast_sync_package(package)
    
        # finally, create the repo
        if self.modified and self.run_createrepo:
            log.info("running createrepo: %s" % self.label)
            os.system("%s %s" % (self.config['createrepo_path'], self.local_dir))
        if self.modified and self.run_yumarch:
            log.info("running yum-arch: %s" % self.label)
            os.system("%s %s" % (self.config['yumarch_path'], self.local_dir))
            
        # clean up files that aren't in packages
        for file in os.listdir(self.local_dir):
            if file not in self.synced_files:
                if file == 'repodata' or file == 'headers':
                    pass
                log.debug("cleanup: %s" % file)
                os.remove(os.path.join(self.local_dir, file))
                
    def _fast_sync_package(self, package_dict):            
        # this is significantly faster
        file_name = "%s-%s-%s.%s.rpm" % (
            package_dict['name'], 
            package_dict['version'], 
            package_dict['release'], 
            package_dict['arch_label']
            )
        package = RHNPackage(package_dict['id'], self.label, 
                             proxy=self.proxy, file_name=file_name)
        
        self.attempted_files.append(package.file)
        full_path = os.path.join(self.local_dir, file_name)
        log.debug('processing %s/%s' % (self.label, file_name))
        
        if not os.path.exists(full_path):
            package.fetch_file(full_path)
            self.modified = True
        
        self.synced_files.append(package.file)
    
    def _slow_sync_package(self, package_dict):
        # this is significantly slower
        package = RHNPackage(package_dict['id'], self.label, 
                             lookup_details=True, proxy=self.proxy)
        self.attempted_files.append(package.file)     
        full_path = os.path.join(self.local_dir, package.file)
        log.debug('processing %s/%s' % (self.label, package.file))
        
        if os.path.exists(full_path):
            log.info('verifying %s/%s' % (self.label, package.file))
            # fetch the file if md5 mismatch, and then re-verify
            count = 0
            while count < 3:
                md5 = hashlib.md5(open(full_path).read()).hexdigest()
                if md5 == package.md5sum:
                    break
                else:
                    package.fetch_file(full_path)
                    self.modified = True
                    count += 1
                if count >= 3:
                    log.error('failed to download %s/%s' % \
                        (self.label, package.file))   
        else:
            # fetch the file cause it doesn't exist
            package.fetch_file(full_path)
            self.modified = True
                    
            count = 0
            while count < 3:
                md5 = hashlib.md5(open(full_path).read()).hexdigest()
                if md5 == package.md5sum:
                    break
                else:
                    package.fetch_file(full_path)
                    count += 1
                if count >= 3:
                    log.error('failed to download %s/%s' % \
                        (self.label, package.file))
                        
        self.synced_files.append(package.file)
