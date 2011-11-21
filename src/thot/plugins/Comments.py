import codecs
import logging
import yaml

__all__ = ['CommentsFromFile']

class CommentsFromFile(object):
    """
    Reads comments stored in file(s) and injects them into the page's header.

    Operates under the assumption that some other utility has stored comments
    for a given page in a separate file. That latter file is named after the
    page except for its extensions, which is ".comments". For example:

    * /year/month/some-article.rst
    * /year/month/some-article.comments

    The plugin is run before the given page is parsed (or rendered) to enable
    Thot to insert them in one of these steps.
    """
    run_at = ['before_page_parsing', ]

    def __init__(self, site, settings):
        self.site = site
        self.site_settings = settings
        logging.debug('Plugin "%s" has been initalized.', self)

    def _find_comment_file(self, page):
        comment_suffix = page['slug'] + '.comments'
        for comment_file_path in page['static_files']:
            if comment_file_path.endswith(comment_suffix):
                logging.debug('Comment file for page "%s" has been found.', page)
                return comment_file_path
        else:
            logging.debug('No comment file for page "%s" has been found', page)
            return None

    def before_page_parsing(self, page):
        comment_file = self._find_comment_file(page)
        if not comment_file: return

        comments = self.parse(comment_file)
        if not comments: return

        if 'comments' in page:
            page['comments'] += comments
        else:
            page['comments'] = comments

    def parse(self, comment_file):
        try:
            with codecs.open(comment_file, 'r', encoding='utf-8') as f:
                comments = yaml.safe_load(f)
                return comments or []
        except Exception as exception:
            logging.error(exception)
            logging.error('skipping comments for page "%s"', page)
            return None

