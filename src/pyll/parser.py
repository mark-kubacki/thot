import yaml
from os.path import splitext


class ParserException(Exception):
    """Exception raised for errors during the parsing."""
    pass

class Parser(object):
    output_ext = None

    def __init__(self, settings, source):
        self.settings = settings
        self.source = source
        self.headers = {}
        self.text = ''

    def _parse_headers(self):
        """
        Parses the headers from the source.
        """
        self.headers = yaml.safe_load(self.header_raw) if self.header_raw != '' else {}
        if not 'status' in self.headers \
           or self.headers['status'] not in ('live', 'hidden', 'draft'):
            self.headers['status'] = 'live'

    def _parse_text(self):
        """
        Returns the raw input text. Override this method to process
        text in another markup language such as Markdown.
        """
        return self.text

    def _split_input(self):
        """
        Segregates header from actual text.
        Used to later parse these parts a different way.
        """
        parts = self.source.split("\n\n", 1)
        if len(parts) < 2:
            parts = self.source.split("---\n", 1)
        if len(parts) >= 2:
            self.header_raw = parts[0]
            self.text = parts[-1]
        else:
            self.header_raw = ''
            self.text = self.source

    def parse(self):
        self._split_input()
        self._parse_headers()
        self._parse_text()
        return (self.headers, self.text)


class RstParser(Parser):
    """ReStructuredText Parser"""
    output_ext = 'html'

    def pygments_directive(self, name, arguments, options, content, lineno,
                           content_offset, block_text, state, state_machine):
        """
        Parse sourcecode using Pygments

        From http://bitbucket.org/birkenfeld/pygments-main/src/tip/external/rst-directive-old.py
        """
        from pygments import highlight
        from pygments.formatters import HtmlFormatter
        from pygments.lexers import get_lexer_by_name, TextLexer
        from docutils import nodes

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
        try:
            from docutils.core import publish_parts
            from docutils.parsers.rst import directives
        except ImportError:
            raise Exception("The Python docutils library isn't installed. " +
                            "Install with `pip install docutils`")
        else:
            # if pygments is installed, register the "sourcecode" directive
            try:
                import pygments
            except ImportError:
                pass
            else:
                directives.register_directive('sourcecode',
                                              self.pygments_directive)
            self.text = publish_parts(source=self.text,
                                      settings_overrides={
                                            "doctitle_xform": False,
                                            "initial_header_level": 2
                                      },
                                      writer_name='html4css1')['fragment']


class MarkdownParser(Parser):
    """Markdown Parser"""
    output_ext = 'html'

    def _parse_text(self):
        try:
            import markdown
        except ImportError:
            raise Exception("The Python markdown library isn't installed. " +
                            "Install with `pip install markdown`")
        else:
            self.text = markdown.markdown(self.text,
                                          ['codehilite(css_class=highlight)'])


# a mapping of file extensions to the corresponding parser class
parser_map = (
    (('html', 'htm', 'xml', 'txt'), Parser),
    (('rst',), RstParser),
    (('md', 'markdown'), MarkdownParser),
)


def get_parser_for_filename(filename):
    """
    Factory function returning a parser class based on the file extension.
    """
    ext = splitext(filename)[1][1:]
    try:
        return [pair[1] for pair in parser_map if ext in pair[0]][0]
    except IndexError:
        return
