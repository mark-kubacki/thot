# -*- coding: utf-8 -*-
import logging
import re
from HTMLParser import HTMLParser

from thot.utils import partition

try:
    from StringIO import StringIO # must support unicode, hence no cStringIO
except:
    from io import StringIO # we prefer StringIO.StringIO because Python's docs say it is faster

try:
    import pyphen
    has_pyphen = True
except:
    has_pyphen = False
    logging.warn("Pyphen has not been found and cannot be used for hyphenation.")

try:
    from wordaxe.DCWHyphenator import DCWHyphenator
    has_wordaxe = True
    wordaxe_languages = ['da', 'de', 'de_DE', 'en', 'en_GB', 'en_US', 'ru']
except:
    has_wordaxe = False
    logging.warn("Wordaxe has not been found and cannot be used for hyphenation.")

__all__ = [
    'HtmlPostProcessor',
]

def wordaxe_hyphenation_wrapper(hyphenator, word):
    word_obj = hyphenator.hyphenate(unicode(word))
    partitions = partition(word, [h.indx for h in word_obj.hyphenations])
    marked_word = HtmlHyphenator.html_hypenation_mark.join(partitions)
    return marked_word

class HtmlRebuilder(HTMLParser):
    """HtmlParser which breaks down HTML, reassembles it immediately
    and keeps track of the current position in DOM.

    Use this as your superclass to influence the HTML-output.
    """

    def __init__(self, page, buffer_size):
        assert buffer_size > 0
        HTMLParser.__init__(self) # because it is an old-style class
        self._modified_contents = StringIO(buffer_size)
        self.tag_path = []
        self._page = page
        self._warned_about_tag_mismatch = False

    def handle_starttag(self, tag, attrs):
        self.tag_path.append(tag)
        self._store_tag(tag, attrs)

    def handle_endtag(self, tag):
        got_tag = tag
        expected_tag = self.tag_path[-1]
        if got_tag == expected_tag:
            self.tag_path.pop()
        else:
            stripped_path = []
            if got_tag in self.tag_path:
                while True:
                    tmp = self.tag_path.pop()
                    if tmp != got_tag:
                        stripped_path.append(tmp)
                    else:
                        break
                stripped_path.reverse()

            if not self._warned_about_tag_mismatch:
                self._warned_about_tag_mismatch = True
                logging.warn('Got tail of tag "%s" but have been expecting end of "%s" in "%s"',
                             got_tag, expected_tag, self._page['output_path'].decode('utf-8'))
                logging.debug('"%s": starting from %r these tags have been stripped from stack: %r',
                              self._page['output_path'].decode('utf-8'),
                              self.tag_path, [got_tag] + stripped_path)
        self._store_tag(tag, None, prefix='</')

    def handle_startendtag(self, tag, attrs):
        self._store_tag(tag, attrs, suffix=' />')

    def handle_decl(self, raw):     self._store_tag(raw, None, '<!', '>')
    def handle_pi(self, raw):       self._store_tag(raw, None, '<?', '>')
    def unknown_decl(self, raw):    self._store_tag(raw, None, '<![', ']>')
    def handle_entityref(self, raw):self._store_tag(raw, None, '&', ';')
    def handle_charref(self, raw):  self._store_tag(raw, None, '&#', ';')

    def handle_comment(self, raw):
        self._store_tag(raw, None, '<!--', '-->')

    def _store_tag(self, tag, attrs, prefix='<', suffix='>'):
        self._modified_contents.write(prefix)
        self._modified_contents.write(tag)
        if attrs:
            for k,v in attrs:
                self._modified_contents.write(' ')
                self._modified_contents.write(k)
                self._modified_contents.write('="')
                self._modified_contents.write(v)
                self._modified_contents.write('"')
        self._modified_contents.write(suffix)

    def handle_data(self, data):
        self._modified_contents.write(data)


class HtmlHyphenator(HtmlRebuilder):
    """Hyphenator of text nodes."""

    # maps language-code to hyphenation facility
    hyphenator = dict()
    hyphenator_f = dict()
    html_hypenation_mark = u'\xad' # chr(173), also known as &shy; - see http://www.w3.org/TR/html401/struct/text.html#h-9.3.3
    dont_hyphenate_if_in = set(['head', 'pre', 'code', 'script', 'style'])

    # subsequent functions are able to handle nubers and symbols
    word_detection_pattern = re.compile(r'\w{5,}', re.UNICODE)

    def __init__(self, page, buffer_size):
        HtmlRebuilder.__init__(self, page, buffer_size)
        # list of tuples (length of tag_path, language tag)
        self._language = []

    def transform(self):
        self.feed(self._page['rendered'])
        return self._modified_contents.getvalue()

    def _get_hyphenator(self, lang):
        if not lang in HtmlHyphenator.hyphenator_f:
            if has_wordaxe and lang in wordaxe_languages:
                h = DCWHyphenator(lang, minWordLength=3)
                HtmlHyphenator.hyphenator[lang] = h
                HtmlHyphenator.hyphenator_f[lang] = \
                    lambda w: wordaxe_hyphenation_wrapper(h, w)
            elif has_pyphen and lang in pyphen.LANGUAGES:
                h = pyphen.Pyphen(lang=lang)
                HtmlHyphenator.hyphenator[lang] = h
                HtmlHyphenator.hyphenator_f[lang] = \
                    lambda w: h.inserted(w, hyphen=HtmlHyphenator.html_hypenation_mark)
            else:
                HtmlHyphenator.hyphenator_f[lang] = lambda x: x
        return HtmlHyphenator.hyphenator_f[lang]

    def _hyphenate(self, text):
        pathlength, lang = self._language[-1]
        hyphenator = self._get_hyphenator(lang)
        return HtmlHyphenator.word_detection_pattern.sub(
            lambda matchobj: hyphenator(matchobj.group(0)),
            text,
        )

    def handle_starttag(self, tag, attrs):
        HtmlRebuilder.handle_starttag(self, tag, attrs)

        if attrs:
            d = dict(attrs)
            if 'lang' in d or 'xml:lang' in d:
                position = len(self.tag_path) # we can do that because it is a stack!
                language_tag = d['lang'] if 'lang' in d else d['xml:lang']
                self._language.append((position, language_tag))

    def handle_endtag(self, tag):
        HtmlRebuilder.handle_endtag(self, tag)

        if self._language:
            while self._language:
                pathlength, lang = self._language[-1]
                if len(self.tag_path) < pathlength:
                    self._language.pop()
                else:
                    break

    def handle_data(self, data):
        if len(self._language) == 0 or HtmlHyphenator.dont_hyphenate_if_in.intersection(self.tag_path) \
           or not data.strip():
            HtmlRebuilder.handle_data(self, data)
        else:
            HtmlRebuilder.handle_data(self, self._hyphenate(data))


class HtmlPostProcessor(object):
    """Collector of HTML postprocessing functions."""

    run_at = ['after_rendering', ]

    def __init__(self, site, settings):
        self.site = site
        self.site_settings = settings
        logging.debug('Plugin "%s" has been initalized.', self)

    def after_rendering(self, page):
        "Entry point. Gets the rendered page as unicode string."
        # 1024 is just a rough guesstimate of how many hyphenation marks we will insert
        html_processor = HtmlHyphenator(
            page,
            buffer_size = len(page['rendered']) + 1024
        )
        page['rendered'] = html_processor.transform()
