"""Jinja2 templating plugin.
"""
# pylint: disable=invalid-name

from jinja2 import Environment, ChoiceLoader, FileSystemLoader, PackageLoader
from jinja2 import TemplateNotFound

from thot.template import TemplateException
from thot.utils import datetimeformat, ordinal_suffix

__all__ = [
    'Jinja2Template',
]

class Jinja2Template(object):
    """
    Jinja2Template implements thot.templating_engines by
    providing render_string and render_file.
    """
    default_template = 'default.html'

    def __init__(self, settings):
        self.settings = settings
        self.env = Environment(loader=ChoiceLoader([
            FileSystemLoader(self.settings['template_dir']),
            PackageLoader('thot')]))
        self.env.filters['datetimeformat'] = datetimeformat
        self.env.filters['ordinalsuffix'] = ordinal_suffix

    def render_string(self, template_str, **kwargs):
        """Use `template_str` as a template"""
        template = self.env.from_string(template_str)
        try:
            return template.render(**kwargs)
        except TemplateNotFound as err:
            raise TemplateException("Template '%s' not found" % err) from err

    def render_file(self, template_name, **kwargs):
        """Use `template_name` as a template"""
        try:
            template = self.env.get_template(template_name)
        except TemplateNotFound as err:
            raise TemplateException from err
        try:
            return template.render(**kwargs)
        except TemplateNotFound as err:
            raise TemplateException("Template '%s' not found" % err) from err

