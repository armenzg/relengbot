_config = None
def load_config(configfile):
    from ConfigParser import RawConfigParser
    config = RawConfigParser()
    if config.read([configfile]) != [configfile]:
        raise IOError("Error parsing %s" % configfile)
    global _config
    _config = config
    return config

def get_bugzillaAPI(config=None):
    from relengbot.lib import bzapi
    if not config:
        config = _config
    return bzapi.BzAPI(
            config.get('bugzilla', 'api'),
            config.get('bugzilla', 'username'),
            config.get('bugzilla', 'password'),
            )

def get_slaveallocAPI(config=None):
    from relengbot.lib import slavealloc
    if not config:
        config = _config
    return slavealloc.SlaveAllocAPI(
            config.get('slavealloc', 'api')
            )
