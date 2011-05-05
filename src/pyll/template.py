
class TemplateException(Exception):
    pass

# maps templating engine classes (value) to their shortnames (key)
templating_map = dict()

def register_templating_engine(shortname):
    "Decorator to templating classes, registers them."
    def add_to_map(_renderer):
        if shortname in templating_map:
            logging.info('Renderer with shortname "%s" already exists ("%s"), and will be overwritten by "%s".',
                         shortname, templating_map[shortname], _renderer)
        templating_map[shortname] = _renderer
        return _renderer
    return add_to_map

def get_templating_cls(shortname):
    return templating_map[shortname]
