"""This is an example plugin for redflare."""

"""
This is a simple plugin to add some basic functionality.
"""

import sys, os
from pkg_resources import get_distribution
import logging

from cement import namespaces
from cement.core.log import get_logger
from cement.core.opt import init_parser
from cement.core.hook import define_hook, register_hook
from cement.core.command import CementCommand, register_command
from cement.core.plugin import CementPlugin, register_plugin

log = get_logger(__name__)

VERSION = '0.1'
REQUIRED_CEMENT_ABI = '20091211'

# Optional: Allows you to customize the output of --version
BANNER = """
redflare.plugins.example v%s 
""" % (VERSION)
 
        
@register_plugin() 
class ExamplePlugin(CementPlugin):
    def __init__(self):
        CementPlugin.__init__(self,
            label = 'example',
            version = VERSION,
            description = 'Example plugin for redflare',
            required_abi = REQUIRED_CEMENT_ABI,
            version_banner=BANNER,
            )
        
        # plugin configurations can be setup this way
        self.config['example_option'] = False
        
        # plugin cli options can be setup this way.  Generally, cli options
        # are used to set config options... so if you probably want to
        # add your options to both.
        self.options.add_option('-E', '--example', action='store',
            dest='example_option', default=None, help='Example Plugin Option'
            )
            
        
@register_hook()
def options_hook(*args, **kwargs):
    """
    Use this hook to add options to other namespaces.  An OptParse object is 
    expected on return, and any options will be merged into the global options.  
    Global options can also be used as local options by setting the config 
    option 'merge_global_options = true' in the plugin config.
    """
    global_options = init_parser()
    global_options.add_option('-G', '--global-option', action ='store_true', 
        dest='global_option', default=None, help='Example Global option'
    ) 
    
    # return the namespace and the global options to add.
    return ('global', global_options)

@register_hook()
def options_hook(*args, **kwargs):
    """
    We can also use the options hook to tie into other plugins, or even our
    own.  This is an alternateway of adding options for your [or other] 
    plugins.
    """
    my_options = init_parser()
    my_options.add_option('--new-local', action ='store', 
        dest='newlocal_option', default=None, help='Example Local option'
    ) 
    
    # return the namespace and the global options to add.
    return ('example', my_options)


@register_hook()
def post_options_hook(*args, **kwargs):
    """
    Use this hook if any operations need to be performed if a global
    option is passed.  Notice that we set a global option of -G in our
    global_options_hook above.  Here we can access that value from the 
    global namespace configuration.
    """
    cnf = namespaces['global'].config 
    if cnf.has_key('global_option'):
        print "global_option => %s", cnf['global_option']  
        # then do something with it  
        

@register_command(name='ex1', namespace='example')
class ex1Command(CementCommand):
    """
    This is how to add a local/plugin subcommand because it will be  
    under the 'example' namespace.  You would access this subcommand as:
    
        $ myapp example ex1
        
    """
    def run(self):
        print "This is Example1Command.run()"
        
    def help(self):
        print "This is Example1Command.help()"        
                
        
@register_command(name='ex2', namespace='global')
class ex2Command(CementCommand):
    def run(self):
        """
        This is an example global command.  See --help.  When commands are
        called, they are passed the cli options and args passed after it.
        These are then forwarded onto the command class where they can be 
        called as self.cli_args, and self.cli_opts.
        
        Notice that you can specify the namespace via the decorator parameters.
        If a plugin has any non-global commands they are grouped under a 
        single command to the base cli application.  For example, you will 
        see global commands and namespaces* when you execute:
        
            myapp --help
            
            
        For example, if 'myplugin' has local commands, you will
        see 'myplugin*' show up in the global commands list, and then the 
        plugin subcommands will be seen under:
        
            myapp myplugin --help
            
        
        This is done to give different options in how your application works.
        """
        print "This is Example2Command.run()."
        
        # you can then see if options where passed:
        if self.cli_opts.global_option:
            print "You passed --global-options!"
            
    def help(self):
        """
        All commands have a hidden -help option as well.  Here you can 
        provide examples or other helpful information.
        """
        print "This is Example2Command.help()"


@register_command(name='ex3', namespace='redflare_core')
class ex3Command(CementCommand):
    """
    This is how to add a local/plugin subcommand to another namespace.  It
    is possible to use this in conjunction with the options_hook() to add 
    additional functionality to a completely other namespace:
    
        $ myapp redflare ex3
        
    """
    def run(self):
        print "This is Example3Command.run()"
        
    def help(self):
        print "This is Example3Command.help()"        
