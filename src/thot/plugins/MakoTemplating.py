from mako.template import Template
from mako.lookup import TemplateLookup
from mako.exceptions import TopLevelLookupException, text_error_template

from thot.utils import datetimeformat, ordinal_suffix
from thot.template import TemplateException

__all__ = [
    'MakoTemplate',
]

class MakoTemplate(object):
    # can be overriden in settings
    default_template = 'post.mak'

    def __init__(self, settings):
        self.settings = settings
        self.template_lookup = TemplateLookup(
                directories=settings['template_dir'].split(','),
                module_directory=settings['tmp_directory'] \
                                 if 'tmp_directory' in settings else None,
                filesystem_checks=False)

    def e_datetimeformat(self, format='%H:%M / %d-%m-%Y'):
        def df(value):
            return value.strftime(format)
        return df

    def _render(self, template, **kwargs):
        try:
            return template.render(ordinal_suffix=ordinal_suffix,
                                   datetimeformat=self.e_datetimeformat,
                                   **kwargs)
        except TopLevelLookupException, e:
            raise TemplateException(e.message)
        except Exception, e:
            # only works for template files; v0.4.1
            try:
                print text_error_template().render()
            except:
                pass
            raise e

    def render_string(self, template_str, **kwargs):
        template =  Template(
            template_str,
            lookup = self.template_lookup)
        return self._render(template, **kwargs)

    def render_file(self, template_name, **kwargs):
        try:
            template = self.template_lookup.get_template(template_name)
        except TopLevelLookupException, e:
            raise TemplateException(e.message)
        return self._render(template, **kwargs)
