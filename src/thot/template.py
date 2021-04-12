"""Templating engines are collected here."""

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
    for e in pkg_resources.iter_entry_points('thot.templating_engines'):
        if e.name == shortname:
            cls = e.load()
            templating_map[shortname] = cls
            return cls
