from codecs import open
from datetime import datetime
import imp
import logging
from os import makedirs
from os.path import splitext, join, dirname, split, getctime, \
                    basename, exists, relpath, isabs
from shutil import rmtree, copytree
import sys
import time
import pytz

from pyll import parser
from pyll.url import get_url
from pyll.utils import copy_file, walk_ignore, OrderedDict
from pyll.template import TemplateException, get_templating_cls

class Site(object):
    def __init__(self, settings):
        self.settings = settings
        self.pages = []
        self.static_files = []

        # import custom urls
        try:
            imp.load_source('urls', self.settings['url_path'])
        except IOError as e:
            logging.debug('couldn\'t load urls from "%s": %s',
                          self.settings['url_path'], e)

    def _read_files(self):
        """
        Walks through the project directory and separates files into 
        parseable files (file extensions for which a parser exists)
        and static files (file extensions for which no parser exists)
        """
        data = OrderedDict()
        for root, dirs, files in walk_ignore(self.settings['project_dir']):
            pages = [] # parseable files; rename to (pages)
            static = [] # rename to (static)

            # check if a parser exists and append to corresponding list
            for file in files:
                path = join(root, file)
                if parser.get_parser_for_filename(path):
                    pages.append(path)
                else:
                    static.append(path)

            # assign static files with pages
            if pages:
                data[root] = (pages, static)
            elif static:
                # dir has static file(s) but no pages. check if one of
                # the parent dirs has a page and associate the static files
                # with it
                has_parent = False
                if root != self.settings['project_dir']:
                    parent_dir = dirname(root)
                    while parent_dir != self.settings['project_dir']:
                        if parent_dir in data:
                            data.setdefault(parent_dir, ([], []))[1].\
                                    extend(static)
                            has_parent = True
                        parent_dir = dirname(parent_dir)
                # if no parent dir could be found, or the file is in the
                # root dir associate the files with the root of the project dir
                if not has_parent:
                    data.setdefault(self.settings['project_dir'],
                                    ([], []))[1].extend(static)
        return data

    def _get_default_headers(self, path):
        """
        Returns a dict with the default headers for `path`.

        `path` - the relative path from the project dir to the file
        `title` - titleized version of the filename
        `date` - set to ctime. On unix this is the time of the most recent
                 metadata change; on windows the creation time. If ctime
                 cannot be accessed (due to permissions), the current 
                 time is used.
        `status` - set to 'live'
        `template` - set to 'default.html'
        `url` - set to "default" rule
        `slug` - filename or, if the filename is "index", the dirname
               of the parent directory unless its the top level dir.
        `output_ext` - the extension of the parsed file
        """
        output_ext = splitext(path)[1][1:]
        root, filename = split(splitext(path)[0])
        if filename == 'index' and root != self.settings['project_dir']:
            slug = basename(root)
        else:
            slug = filename
        title = filename.title()
        try:
            date = pytz.utc.localize(datetime.utcfromtimestamp(getctime(path)))
        except OSError:
            # use the current date if the ctime cannot be accessed
            date = self.settings['build_time']
        template = self.settings['default_template'] if 'default_template' in self.settings \
                   else get_templating_cls(self.settings['templating_engine']).default_template
        return dict(path=relpath(path, self.settings['project_dir']),
                    title=title, date=date, status='live',
                    slug=slug, template=template, url='default',
                    output_ext=output_ext)

    def _parse(self, input_data):
        "Parses the input data"
        now = self.settings['build_time']
        for input_dir in input_data:
            pages, static_files = input_data[input_dir]

            # special case: static files at the top level of the project dir 
            # are not associated with any pages
            if input_dir == self.settings['project_dir']:
                self.static_files = static_files
                static_files = []

            for path in pages:
                page = dict(static_files=static_files)
                page.update(self._get_default_headers(path))

                # parse the page
                parser_cls = parser.get_parser_for_filename(page['path'])
                with open(path, 'r', encoding='utf-8') as f:
                    parser_inst = parser_cls(self.settings, f.read(), page['path'])

                try:
                    parsed = parser_inst.parse()
                except parser.ParserException as parser_error:
                    logging.error(parser_error)
                    logging.error('skipping article "%s"', path)
                    continue

                # update the values in the page dict
                page.update(content=parsed[1], **parsed[0])
                if parser_cls.output_ext:
                    page.update(output_ext=parser_cls.output_ext)

                # skip drafts
                if page['status'] == 'draft':
                    logging.debug('skipping %s (draft)', path)
                    continue
                # skip pages with a date that is in the future
                elif page['date'] > now:
                    logging.debug('skipping %s (future-dated)', path)
                    continue
                # skip expired pages; i.e. with a passed expiry set
                elif 'expires' in page and page['expires'] < now:
                    logging.debug('skipping %s (expired)', path)
                    continue
                
                # update the url
                page['url'] = get_url(page)

                self.pages.append(page)
                sys.stdout.write('.')
        sys.stdout.write('\n')

    def _sort(self):
        "Sort pages by date (newest first)"
        self.pages.sort(key=lambda p: p['date'], reverse=True)

    def _delete_output_dir(self):
        "Deletes the output directory"
        if exists(self.settings['output_dir']):
            rmtree(self.settings['output_dir'])

    def _is_public(self, page):
        "Return True if page is public"
        return page['status'] != 'hidden'

    def _get_output_path(self, url):
        "Returns the filesystem path for `url`"
        if isabs(url):
            # omit starting slash char; if we wouldn't do this, the
            # join() below would return a path that starts from 
            # the root of the filesystem instead of the output_dir.
            url = url[1:]
        if not basename(url):
            # url is a directory -> write to 'index.html'
            output_path = join(url, 'index.html')
        else:
            # url is a filename
            output_path = url
        return join(self.settings['output_dir'], output_path)

    def _write(self):
        "Writes the parsed data to the filesystem"
        public_pages = filter(self._is_public, self.pages)
        templating_engine = get_templating_cls(self.settings['templating_engine'])
        template_cls = templating_engine(self.settings)
        for page in self.pages:
            output_path = self._get_output_path(page['url'])

            # create the directories for the page
            try:
                makedirs(dirname(output_path))
            except OSError:
                pass

            # render template
            if page['template'] == 'self':
                render_func = template_cls.render_string
                template = page['content']
            else:
                render_func = template_cls.render_file
                template = page['template']

            try:
                logging.debug('About to render "%s".', output_path)
                rendered = render_func(template,
                                       page=page,
                                       pages=public_pages,
                                       settings=self.settings)
            except TemplateException as error:
                logging.error(error)
                logging.error('skipping article "%s"', page['path'])
                continue

            # write to filesystem
            logging.debug("writing %s to %s", page['path'], output_path)
            with open(output_path, 'w', 'utf-8') as f:
                f.write(rendered)

    def _copy_static_files(self):
        "Copies static files to output directory"
        # static files that aren't associated with pages
        for static_file in self.static_files:
            dst = join(self.settings['output_dir'],
                       relpath(static_file, self.settings['project_dir']))
            logging.debug('copying %s to %s', static_file, dst)
            copy_file(static_file, dst, self.settings['hardlinks'])

        # static files that are associated with pages
        for page in self.pages:
            for static_file in page['static_files']:
                dst = join(self.settings['output_dir'],
                           dirname(_get_output_path(page['url'])),
                           relpath(static_file, dirname(page['path'])))
                logging.debug('copying %s to %s', static_file, dst)
                copy_file(static_file, dst, self.settings['hardlinks'])

    def run(self):
        start_time = time.time()
        input_data = self._read_files()
        logging.debug("input data %s", input_data)
        self._parse(input_data)
        self._sort()
        self._delete_output_dir()
        self._write()
        self._copy_static_files()
        finish_time = time.time()
        count = len(self.pages)
        print("OK (%s %s; %s seconds)" % (
            count, 'page' if count == 1 else 'pages',
            round(finish_time - start_time, 2)))

