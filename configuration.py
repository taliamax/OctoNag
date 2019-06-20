import sys
from yaml import load
from functools import wraps
import pytest

def get_config_from_file(config_file='config.yaml'):
    """
    Grabs the configuration from YAML file
    """
    with open(config_file, 'r') as f:
        try:
            config = load(f.read())
        except Exception as e:
            sys.stderr.write(e)
            sys.stderr.write("Error reading configuration file {}".format(config_file))
            config = None
    return config


class _config:
    def __init__(self):
        configs = get_config_from_file()

        if configs['slack_token'] is None \
            or configs['github_token'] is None:
            sys.stderr.write('Please ensure that the github token and slack token are defined in the config file')
            sys.exit(1)


        self.map_users = configs['manually_resolve_users']
        self.github_token = configs['github_token']
        self.slack_token = configs['slack_token']
        self.repositories = configs['repositories']
        self.whitelist = configs['whitelist'] and set(configs['whitelist'])
        self.blacklist = configs['blacklist'] and set(configs['blacklist'])


Configuration = _config()
organizations = Configuration.repositories.keys()

def restrict(list_type):
    def restricting_decorator(func):
        @wraps(func)
        def wrapper(name, *args, **kwargs):
            if list_type == 'blacklist':
                collection = Configuration.blacklist
            elif list_type == 'whitelist':
                collection = Configuration.whitelist
            else:
                collection = None
            
            if collection and ((list_type == 'whitelist') ^ (name in collection)):
                print 'User %s %s in %s, blocking lookup' % (name, 'not' if list_type=='whitelist' else '', list_type)
                return None
            else:
                return func(name, *args, **kwargs)

        return wrapper
    return restricting_decorator

def with_token(service='Github'):
    def use_token(func):
        @wraps(func)
        def wrapper(*args, **kwargs): 
            if service == 'Github':
                token = Configuration.github_token
            else:
                token = Configuration.slack_token
            new_kwargs = kwargs.copy()
            new_kwargs['_token'] = token
            return func(*args, **new_kwargs)
        return wrapper
    return use_token

def repositories(func):
    @wraps(func)
    def wrapper(organization, *args, **kwargs):
        new_kwargs = kwargs.copy()
        new_kwargs['_repositories'] = Configuration.repositories[organization]
        return func(organization, *args, **new_kwargs)
    return wrapper
    
def manually_resolve(func):
    @wraps(func)
    def wrapper(name, *args, **kwargs):
        if Configuration.map_users and name in Configuration.map_users:
            print '%s in manual mapping configuration, doing lookup on %s' % (name, Configuration.map_users[name])
            return func(Configuration.map_users[name], *args, **kwargs)
        else:
            return func(name, *args, **kwargs)
    return wrapper