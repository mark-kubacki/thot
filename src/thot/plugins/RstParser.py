from docutils import nodes
from docutils.core import publish_parts
from docutils.parsers.rst import directives

try:
    import pygments
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import get_lexer_by_name, TextLexer
    has_pygments = True
except:
    has_pygments = False

from thot.parser import Parser

__all__ = [
    'RstParser',
]

class RstParser(Parser):
    """ReStructuredText Parser"""
    output_ext = 'html'
    parses = ['rst']

    def pygments_directive(self, name, arguments, options, content, lineno,
                           content_offset, block_text, state, state_machine):
        """
        Parse sourcecode using Pygments

        From http://bitbucket.org/birkenfeld/pygments-main/src/tip/external/rst-directive-old.py
        """
        try:
            lexer = get_lexer_by_name(arguments[0])
        except ValueError:
            # no lexer found - use the text one instead of an exception
            lexer = TextLexer()
        # take an arbitrary option if more than one is given
        formatter = HtmlFormatter(noclasses=False)
        parsed = highlight(u'\n'.join(content), lexer, formatter)
        return [nodes.raw('', parsed, format='html')]
    pygments_directive.arguments = (1, 0, 1)
    pygments_directive.content = 1

    def _parse_text(self):
        # if pygments is installed, register the "sourcecode" directive
        if has_pygments:
            directives.register_directive('sourcecode',
                                          self.pygments_directive)
        self.text = publish_parts(source=self.text,
                                  settings_overrides={
                                        "doctitle_xform": False,
                                        "initial_header_level": 2
                                  },
                                  writer_name='html4css1')['fragment']

