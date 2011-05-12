import pkg_resources

__all__ = [
    'TemplateException', 'get_templating_cls',
]

class TemplateException(Exception):
    pass

# maps templating engine classes (value) to their shortnames (key)
templating_map = dict()

def get_templating_cls(shortname):
    if shortname in templating_map:
        return templating_map[shortname]
    for entrypoint in pkg_resources.iter_entry_points('thot.templating_engines'):
        if entrypoint.name == shortname:
            cls = entrypoint.load()
            templating_map[shortname] = cls
            return cls
