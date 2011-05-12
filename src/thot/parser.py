import logging
import yaml
import pytz
from datetime import datetime, date, time
from os.path import splitext
import pkg_resources

__all__ = [
    'ParserException', 'Parser', 'get_parser_for_filename',
]

class ParserException(Exception):
    """Exception raised for errors during the parsing."""
    pass

# a mapping of file extensions to the corresponding parser class
parser_map = dict()


class Parser(object):
    output_ext = None
    parses = ['html', 'htm', 'xml', 'txt']

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


def get_parser_for_filename(filename):
    """
    Factory function returning a parser class based on the file extension.
    """
    if len(parser_map) <= 0:
        for entrypoint in pkg_resources.iter_entry_points('thot.renderer'):
            try:
                cls = entrypoint.load()
                for e in cls.parses:
                    parser_map[e] = cls
            except Exception, e:
                logging.debug('Parser "%s" has not been loaded due to: %s',
                              entrypoint, e)

    ext = splitext(filename)[1][1:]
    try:
        return parser_map[ext]
    except KeyError:
        return
