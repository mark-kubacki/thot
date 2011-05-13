from trac.core import *
from trac.mimeview import Context
from trac.test import Mock, MockPerm, EnvironmentStub
from trac.web.href import Href
from trac.wiki.formatter import HtmlFormatter

# importing from trac.wiki.macros registers all macros contained in that module
from trac.wiki.macros import WikiMacroBase

from thot.parser import Parser

__all__ = [
    'TracParser',
]

class TracParser(Parser):
    """
    Parser of Trac wiki pages into HTML.
    
    Does not support processors (syntax highlighting) and only a limited set
    of macros.
    """
    output_ext = 'html'
    parses = ['trac']

    def create_trac_ctx(self, website_url, author_name, timezone_str, uri):
        req = Mock(href=Href(uri),
                   abs_href=Href(website_url),
                   authname=author_name,
                   perm=MockPerm(),
                   tz=timezone_str,
                   args={})
        context = Context.from_request(req, 'wiki', 'WikiStart')

        env = EnvironmentStub(enable=['trac.*']) # + additional components
        # -- macros support
        env.path = ''
        # -- intertrac support
        env.config.set('intertrac', 'trac.title', "Trac's Trac")
        env.config.set('intertrac', 'trac.url',
                       website_url)
        env.config.set('intertrac', 't', 'trac')
        env.config.set('intertrac', 'th.title', "Trac Hacks")
        env.config.set('intertrac', 'th.url',
                       "http://trac-hacks.org")
        env.config.set('intertrac', 'th.compat', 'false')
        # -- safe schemes
        env.config.set('wiki', 'safe_schemes',
                       'file,ftp,http,https,svn,svn+ssh,git,'
                       'rfc-2396.compatible,rfc-2396+under_score')

        env.href = req.href
        env.abs_href = req.abs_href
        return (env, context)

    def _parse_text(self):
        env, context = self.create_trac_ctx(
            self.settings['website_url'],
            self.headers['author']['name'] if ('author' in self.headers and 'name' in self.headers['author']) else self.settings['author']['name'],
            str(self.headers['timezone']) if 'timezone' in self.headers else str(self.settings['timezone']),
            self.filename if self.filename.startswith('/') else '/'+self.filename)
        formatter = HtmlFormatter(env, context, self.text)
        self.text = formatter.generate()

