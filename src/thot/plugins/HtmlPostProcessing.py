# -*- coding: utf-8 -*-
import logging
import re
from lxml import etree

from thot.utils import partition

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

class HtmlHyphenator(object):
    """Hyphenator of text nodes."""

    # maps language-code to hyphenation facility
    hyphenator = dict()
    hyphenator_f = dict()
    html_hypenation_mark = u'\xad' # chr(173), also known as &shy; - see http://www.w3.org/TR/html401/struct/text.html#h-9.3.3
    dont_hyphenate_if_in = set(['head', 'pre', 'code', 'script', 'style'])

    # subsequent functions are able to handle nubers and symbols
    word_detection_pattern = re.compile(r'\w{5,}', re.UNICODE)

    @classmethod
    def get_language(cls, element):
        if 'lang' in element.attrib:
            return element.attrib['lang']
        for ancestor in element.iterancestors():
            if 'lang' in ancestor.attrib:
                return ancestor.attrib['lang']

    @classmethod
    def transform(self, page, dom_tree):
        language_annotated_text = 'body//*[ancestor-or-self::*/@lang and string-length(text()) > 5]'
        for elem in dom_tree.xpath(language_annotated_text):
            tag_path = [ancestor.tag for ancestor in elem.iterancestors()]
            if not HtmlHyphenator.dont_hyphenate_if_in.intersection(tag_path):
                lang = HtmlHyphenator.get_language(elem)

                if elem.text and not elem.text.isspace():
                    elem.text = self._hyphenate(elem.text, lang)
                for child in elem.iterchildren():
                    if child.tail and not child.tail.isspace():
                        child.tail = self._hyphenate(child.tail, lang)

    @classmethod
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

    @classmethod
    def _hyphenate(self, text, language):
        hyphenator = self._get_hyphenator(language)
        return HtmlHyphenator.word_detection_pattern.sub(
            lambda matchobj: hyphenator(matchobj.group(0)),
            text,
        )


class HtmlPostProcessor(object):
    """Collector of HTML postprocessing functions."""

    run_at = ['after_rendering', ]

    def __init__(self, site, settings):
        self.site = site
        self.site_settings = settings
        logging.debug('Plugin "%s" has been initalized.', self)

    def after_rendering(self, page):
        """Entry point. Gets the rendered page as unicode string and breaks it down to DOM.
        """
        parser = etree.HTMLParser(encoding='utf-8')
        dom_tree = etree.fromstring(page['rendered'].encode('utf-8'), parser)

        HtmlHyphenator.transform(page, dom_tree)

        page['rendered'] = etree.tostring(dom_tree, xml_declaration=False, encoding="utf-8").decode('utf-8')
