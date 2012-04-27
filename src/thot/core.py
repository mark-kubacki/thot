import codecs
from datetime import datetime
import imp
import logging
import types
from os import makedirs, utime
from os.path import splitext, join, dirname, split, getmtime, \
                    basename, exists, relpath, isabs, isfile
from shutil import rmtree, copytree, copystat
import sys
import time
import pytz
import pkg_resources
import weakref
import gzip

from thot import parser, version as thot_version
from thot.url import get_url
from thot.utils import copy_file, walk_ignore, OrderedDict
from thot.template import TemplateException, get_templating_cls

class Page(dict):

    def __init__(self, db, get_url, **kwargs):
        super(Page, self).__init__(self, **kwargs)
        self.db = db
        self.get_url = get_url
        self.parser_cls = None

    @property
    def is_public(self):
        "Return True if page is public"
        return self['status'] != 'hidden'

    @property
    def is_parsed(self):
        return 'content' in self

    def dont_render(self, now):
        "True if the page shall be excluded from being rendered."
        # skip drafts
        if self['status'] == 'draft' \
           or ('published' in self and not self['published']):
            logging.debug('skipping %s (draft)', self)
            return True
        # skip pages with a date that is in the future
        elif self['date'] > now:
            logging.debug('skipping %s (future-dated)', self)
            return True
        # skip expired pages; i.e. with a passed expiry set
        elif 'expires' in self and self['expires'] < now:
            logging.debug('skipping %s (expired)', page)
            return True
        return False

    def get_parser_class(self):
        if not self.parser_cls:
            self.parser_cls = parser.get_parser_for_filename(self['path'])
        return self.parser_cls

    def load(self, site_settings):
        raw = self.db.read(self['path'])
        parser_cls = self.get_parser_class()
        self.parser_inst = parser_cls(site_settings, raw, self['path'])
        if parser_cls.output_ext:
            self['output_ext'] = parser_cls.output_ext

    def parse_headers(self):
        self.update(**self.parser_inst.parse_headers())
        # update the url
        self['url'] = self.get_url(self)

    def parse(self): # throws parser.ParserException
        headers, content = self.parser_inst.parse()
        # update the values in the page dict
        self['content'] = content

    def copy(self):
        clone = Page(self.db, self.get_url, **dict(self))
        return clone

    def __str__(self):
        if 'url' in self:
            return "Page(path=%s, url=%s)" % (self['path'] if 'path' in self else 'undefined', self['url'])
        else:
            return "Page(path=%s)" % (self['path'] if 'path' in self else 'undefined')

    def __repr__(self):
        return str(self)


class Site(object):
    def __init__(self, settings, data_source):
        self.settings = settings
        self.data_source = data_source
        self.pages = []
        self.static_files = []

        # import custom urls
        try:
            imp.load_source('urls', self.settings['url_path'])
        except IOError as e:
            logging.debug('couldn\'t load urls from "%s": %s',
                          self.settings['url_path'], e)
        self.data_source.set_urlfunc(get_url)

        # maps list of Processors to steps
        self.processor_map = {}
        self._init_processors()

    def _init_processors(self):
        """
        Loads and initalizes all available processors.
        """
        for entrypoint in pkg_resources.iter_entry_points('thot.processors'):
            try:
                cls = entrypoint.load()
                cls_instance = cls(weakref.ref(self), self.settings)
                for step in cls.run_at:
                    if step in self.processor_map:
                        self.processor_map[step].append(cls_instance)
                    else:
                        self.processor_map[step] = [cls_instance, ]
            except Exception, e:
                logging.debug('Processor "%s" has not been loaded due to: %s',
                              entrypoint, e)

    def processors_for(self, step):
        "Gets a list of processors for the given step."
        if step in self.processor_map:
            return self.processor_map[step]
        else:
            return []

    def _parse(self, input_data):
        "Parses the input data"
        now = self.settings['build_time']
        for input_dir in input_data:
            pages, static_files = input_data[input_dir]

            # special case: static files at the top level of the project dir
            # are not associated with any pages
            if input_dir == self.settings['project_dir']:
                self.static_files = static_files

            for page in pages:
                page.load(self.settings)
                page.parse_headers()

                if page.dont_render(now):
                    continue

                # for example, load comments from a webservice or different file
                for proc in self.processors_for('before_page_parsing'):
                    proc.before_page_parsing(page)

                # rendering of the actual content
                try:
                    page.parse()
                except parser.ParserException as parser_error:
                    logging.error(parser_error)
                    logging.error('skipping article "%s"', page)
                    continue

                # for example, collect tags and categories
                for proc in self.processors_for('after_page_parsed'):
                    proc.after_page_parsed(page)

                self.pages.append(page)
                sys.stdout.write('.')
        sys.stdout.write('\n')

        for proc in self.processors_for('after_parsing'):
            proc.after_parsing(self.pages)

    def _sort(self):
        "Sort pages by date (newest first)"
        self.pages.sort(key=lambda p: p['date'], reverse=True)

    def _delete_output_dir(self):
        "Deletes the output directory"
        if exists(self.settings['output_dir']):
            rmtree(self.settings['output_dir'])

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
        public_pages = [page for page in self.pages if page.is_public]
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
                logging.debug('About to render "%s".', output_path.decode('utf-8'))
                params = page['params'] if 'params' in page else {}
                rendered = render_func(template,
                                       page=page,
                                       pages=public_pages,
                                       settings=self.settings,
                                       thot_version=thot_version,
                                       **params)
                assert type(rendered) == types.UnicodeType
            except TemplateException as error:
                logging.error(error)
                logging.error('skipping article "%s"', page['path'])
                continue

            # write to filesystem
            logging.debug("writing %s to %s", page['path'], output_path.decode('utf-8'))
            with codecs.open(output_path, 'w', 'utf-8') as f:
                f.write(rendered)
            page_dt_for_fs = page['mtime'].astimezone(self.settings['build_tz'])
            atime = mtime = int(time.mktime(page_dt_for_fs.timetuple()))
            utime(output_path, (atime, mtime))

            # GZIP output for webservers which support pre-compressed files
            if self.settings['make_compressed_copy']:
                gz_output_path = output_path+'.gz'
                with gzip.GzipFile(gz_output_path, 'w', mtime=mtime) as f:
                    f.write(rendered.encode('utf-8'))
                utime(gz_output_path, (atime, mtime))

    def _copy_static_file(self, static_file, dst):
        logging.debug('copying %s to %s', static_file.decode('utf-8'), dst.decode('utf-8'))
        if copy_file(static_file, dst, self.settings['hardlinks']) \
           and self.settings['make_compressed_copy']:
            for ending in self.settings['compress_if_ending']:
                if static_file.endswith(ending):
                    if not isfile(static_file+'.gz'):
                        with open(static_file, 'rb') as fin, gzip.open(dst+'.gz', 'wb') as fout:
                            fout.writelines(fin)
                        copystat(static_file, dst+'.gz')
                    break

    def _copy_static_files(self):
        "Copies static files to output directory"
        # static files that aren't associated with pages
        for static_file in self.static_files:
            dst = join(self.settings['output_dir'],
                       relpath(static_file, self.settings['project_dir']))
            self._copy_static_file(static_file, dst)

        # static files that are associated with pages
        page_files = []
        for page in self.pages:
            for static_file in page['static_files']:
                dst = join(self.settings['output_dir'],
                           dirname(self._get_output_path(page['url'])),
                           relpath(static_file, dirname(page['path'])))
                page_files.append((static_file, dst))
        for static_file, dst in frozenset(page_files):
            self._copy_static_file(static_file, dst)

    def run(self):
        start_time = time.time()
        input_data = self.data_source.read_files()
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


class FilesystemSource(object):
    """
    Source of pages which are read from filesystem.

    ... and not a database, for example.
    """

    def __init__(self, project_dir, build_time, build_tz, default_template):
        self.project_dir = project_dir
        self.build_time = build_time
        self.build_tz = build_tz
        self.default_template = default_template

    def set_urlfunc(self, urlfunc):
        self.get_url = urlfunc

    def read_files(self):
        """
        Walks through the project directory and separates files into
        parseable files (file extensions for which a parser exists)
        and static files (file extensions for which no parser exists)
        """
        data = OrderedDict()
        for root, dirs, files in walk_ignore(self.project_dir):
            pages = []
            parseables = [] # parseable files; rename to (pages)
            static = [] # rename to (static)

            # check if a parser exists and append to corresponding list
            for file in files:
                path = join(root, file)
                if parser.get_parser_for_filename(path):
                    parseables.append(path)
                else:
                    static.append(path)

            # create pages from parseables
            for path in parseables:
                static_files = static if root != self.project_dir else []
                pages.append(self._create_page(path, static_files))

            # assign static files with pages
            if pages:
                data[root] = (pages, static)
            elif static:
                # dir has static file(s) but no pages. check if one of
                # the parent dirs has a page and associate the static files
                # with it
                has_parent = False
                if root != self.project_dir:
                    parent_dir = dirname(root)
                    while parent_dir != self.project_dir:
                        if parent_dir in data:
                            data.setdefault(parent_dir, ([], []))[1].\
                                    extend(static)
                            has_parent = True
                        parent_dir = dirname(parent_dir)
                # if no parent dir could be found, or the file is in the
                # root dir associate the files with the root of the project dir
                if not has_parent:
                    data.setdefault(self.project_dir,
                                    ([], []))[1].extend(static)
        return data

    def _create_page(self, path, static_files):
        page = Page(db=self, get_url=self.get_url, static_files=static_files)
        page.update(self._get_default_headers(path))
        return page

    def read(self, path):
        with codecs.open(join(self.project_dir, path), 'r', encoding='utf-8') as f:
            return f.read()

    def _get_default_headers(self, path):
        """
        Returns a dict with the default headers for `path`.

        `path` - the relative path from the project dir to the file
        `title` - titleized version of the filename
        `date` - set to mtime. This is the time of the most recent
                 content change. If mtime cannot be accessed (due
                 to permissions), the current time is used.
        `mdate` - same as `date`, only that it should not be overwritten
        `status` - set to 'live'
        `template` - set to 'default.html'
        `url` - set to "default" rule
        `slug` - filename or, if the filename is "index", the dirname
               of the parent directory unless its the top level dir.
        `output_ext` - the extension of the parsed file
        """
        output_ext = splitext(path)[1][1:]
        root, filename = split(splitext(path)[0])
        if filename == 'index' and root != self.project_dir:
            slug = basename(root)
        else:
            slug = filename
        title = filename.title()
        try:
            date = pytz.utc.localize(datetime.utcfromtimestamp(getmtime(path)))
        except OSError:
            # use the current date if the ctime cannot be accessed
            date = self.build_time
        date = date.astimezone(self.build_tz)
        template = self.default_template
        return dict(path=relpath(path, self.project_dir),
                    title=title, date=date, mtime=date, status='live',
                    slug=slug, template=template, url='default',
                    output_ext=output_ext)
