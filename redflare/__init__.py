__import__('pkg_resources').declare_namespace(__name__)

import os
from cement.helpers.cache.simple_cache import SimpleCache
from redflare.config import default_config

user_cache = SimpleCache(
    os.path.join(os.environ['HOME'], '.redflare.cache'),
    mode=0640
    )