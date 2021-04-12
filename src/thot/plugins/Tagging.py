"""Plugin for maintaining 'tags' and 'categories'.

These are actually mappings from (a) keyword to a set of pages.
They become known after parsing of all eligible page files.
"""
# pylint: disable=invalid-name

from collections.abc import Iterable
from operator import itemgetter
import logging
from typing import Dict, List

from thot.core import Page

__all__ = [
    'PageTags', 'PageCategory',
]

def append_to_collection(
    keywords_from_field: str,
    collection: Dict[str, List[Page]],
    page: Page, none_is_key=None,
) -> None:
    if keywords_from_field in page:
        if isinstance(page[keywords_from_field], list):
            keywords = page[keywords_from_field]
        else:
            keywords = [page[keywords_from_field], ]
    elif none_is_key:
        keywords = [none_is_key, ]
    else:
        return

    for word in keywords:
        if word in collection:
            collection[word].append(page)
        else:
            collection[word] = [page, ]


class PageTags(object):
    """
    Mapper of pages to tags.

    This plugin does two things:
     1. reads the tags from the pages
     2. injects new parametrized output pages
    The beforementioned collection mediates between the steps.
    """
    run_at = ['after_page_parsed', 'after_parsing', ]
    field = 'tags'
    none_is_key = False

    def __init__(self, site, settings):
        self.site = site
        self.site_settings = settings
        self.collection = {} # tag -> list of pages
        logging.debug('Plugin "%s" has been initalized.', self)

    def after_page_parsed(self, page: Page) -> None:
        """ Step 1: tags from page """
        if page.is_public:
            append_to_collection(self.field, self.collection,
                page, self.none_is_key)

    def _pop_index_page(self, pages: Iterable[Page]) -> Page:
        """
        Gets the page that servers as template for the field's index,
        removes it from the stack of pages if necessary.
        """
        for page in pages:
            if 'index' not in page:
                continue

            if isinstance(page['index'], list) \
               and self.field in page['index']:
                if len(page['index']) <= 1:
                    # exclude its common instance from usual parsing
                    pages.remove(page)
                else:
                    # just remove one function
                    page['index'].remove(self.field)
                return page
            elif page['index'] == self.field:
                # exclude its common instance from usual parsing
                pages.remove(page)
                return page
        return None

    def _get_url(self, page: Page) -> str:
        """
        Suggests a functional url.
        """
        url = self.field + '/'
        url += page['params']['field_value'].lower().replace(' ', '-')
        url += '/index.html'
        return url

    def after_parsing(self, pages: Iterable[Page]) -> None:
        """
        Step 2: inject new parametrized pages
        which will serve as archive, category or tag indices.
        """
        # find the page with "index: tag"
        index_page = self._pop_index_page(pages)
        if not index_page:
            # pylint: disable=logging-not-lazy
            logging.warning(
                'Index page for "%s" could not be found.' \
                + ' Please create one with "{status: hidden, index: \'%s\'}".',
                self.field, self.field)
            return

        # inject it multiple times, parametrized
        for field_value in self.collection:
            # sort the collection
            self.collection[field_value].sort(
                key=itemgetter('date', 'url'), reverse=True)
            # index pages
            p = index_page.copy()
            params = dict(field=self.field,
                          field_value=field_value,
                          collection=self.collection[field_value])
            p['params'] = params
            p['url'] = self._get_url(p)
            p['title'] = p['title'] % params
            pages.append(p)


class PageCategory(PageTags):
    """
    Mapper of pages to categories.
    """

    field = 'category'
    none_is_key = 'Uncategorized'
