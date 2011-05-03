import logging
import yaml
import pytz
from datetime import datetime, date, time
from os.path import splitext


class ParserException(Exception):
    """Exception raised for errors during the parsing."""
    pass

# a mapping of file extensions to the corresponding parser class
parser_map = dict()

def parses(*extensions):
    "Decorator to Parsers, registers them for input files of given file name extensions."
    def add_to_map(_parser):
        for ext in extensions:
            if ext in parser_map:
                logging.info('Extension "%s" is already registered with parser "%s" and will be redefined.',
                             ext, parser_map[ext])
            parser_map[ext] = _parser
        return _parser
    return add_to_map


@parses('html', 'htm', 'xml', 'txt')
class Parser(object):
    output_ext = None

    def __init__(self, settings, source, filename):
        self.settings = settings
        self.source = source
        self.headers = {}
        self.text = ''
        self.filename = filename

    def _parse_headers(self):
        """
        Parses the headers from the source.
        """
        self.headers = yaml.safe_load(self.header_raw) if self.header_raw != '' else {}
        for key in self.headers:
            value = self.headers[key]
            if value:
                # custom header transformation
                header_method = getattr(self, '_parse_%s_header' % key,
                                        None)
                if header_method:
                    self.headers[key] = header_method(value)

    def _parse_date_header(self, value):
        """
        Applies the user's timezone.
        """
        # if the date is localized - do nothing
        if hasattr(value, 'tzname') and value.tzname():
            return value
        if type(value) == date:
            value = datetime.combine(value, time(0, 0))
        user_tz = self.settings['timezone']
        # if the user specified a different timezone, use that
        if 'timezone' in self.headers:
            if self.headers['timezone'] in pytz.all_timezones_set:
                user_tz = pytz.timezone[self.headers['timezone']]
            else:
                logging.warn('Timezone "%s" specified in "%s" is unknown, "%s" will be used instead',
                             self.headers['timezone'], self.filename, user_tz)
        return user_tz.localize(value)
    _parse_expires_header = _parse_date_header

    def _parse_status_header(self, value):
        """
        Checks that the value of the 'status' header is 'live', 'hidden' or
        'draft'. If not 'live' is returned.
        """
        if value in ('live', 'hidden', 'draft'):
            return value
        return 'live'

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
            logging.warn("'%s' has no headers, only content - at least 'title' will be missing.", self.filename)
            self.header_raw = ''
            self.text = self.source

    def parse(self):
        self._split_input()
        self._parse_headers()
        self._parse_text()
        return (self.headers, self.text)


@parses('rst')
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


@parses('md', 'markdown')
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


def get_parser_for_filename(filename):
    """
    Factory function returning a parser class based on the file extension.
    """
    ext = splitext(filename)[1][1:]
    try:
        return parser_map[ext]
    except KeyError:
        return
