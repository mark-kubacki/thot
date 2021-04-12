"""Commands understood by Thot.
"""

from datetime import datetime
from optparse import OptionParser
from os import makedirs, getcwd, getuid
from os.path import join, abspath, exists, realpath
from shutil import copytree
import codecs
import logging
import pwd
import sys
import time

import yaml
import pytz
import pkg_resources

from thot import version
from thot.core import Site
from thot.template import get_templating_cls

try:
    import curses
    from anzu.options import _LogFormatter
    has_logformatter = True
except ModuleNotFoundError:
    try:
        import curses
        from tornado.options import _LogFormatter
        has_logformatter = True
    except ModuleNotFoundError:
        has_logformatter = False

__all__ = [
    'quickstart', 'main',
]

LOGGING_LEVELS = {'info': logging.INFO, 'debug': logging.DEBUG}
GZIP_ENDINGS = [
    '.css', '.js', '.xml', '.txt', '.sh', '.svg',
    '.xls', '.doc', '.xjs', '.psd', '.ppt',
    '.java', '.py', '.pyc', '.pyo', '.bat', '.dll', '.lib',
    '.cfg', '.ini', '.json',
    ]

def quickstart(settings):
    # determine the quickstart template's location in advance
    tmpl_relpath = [
        'share', 'thot', 'quickstart',
        settings['templating_engine'],
    ]
    tmpl_path = join(sys.prefix, *tmpl_relpath)
    if not exists(tmpl_path):
        tmpl_path = realpath(
            join(pkg_resources.resource_filename('thot', ''),
            '..', *tmpl_relpath)
        )
        if not exists(tmpl_path):
            print('Sorry, cannot find directory %s' % join(*tmpl_relpath))
            sys.exit(3)

    # get default configuration values
    author_name  = login = pwd.getpwuid(getuid())[0]
    author_email = author_email_default = '%s@localhost' % login
    website_url  = website_url_default = 'http://www.example.org'
    language     = language_default = 'de'
    timezone     = 'UTC'

    try:
        author_name  = input('Author Name [%s]:  ' % login) or login
        author_email = input('Author Email [%s]: ' % author_email_default) \
            or author_email_default
        website_url  = input('Website URL [%s]:  ' % website_url_default) \
            or website_url_default
        timezone = 'tbd'
        while timezone not in pytz.all_timezones_set:
            if timezone != 'tbd':
                print('Timezone "%s" is unknown. Try another.' % timezone)
            timezone = input(
                'Your timezone, e.g. Europe/Berlin, US/Pacific, \n'
                + 'UTC, or something other: ')
        language = input(
            'Default language tag (de, en_US, en_GB...) [%s]: ' \
            % language_default) or language_default
    except EOFError:
        # Absent a controlling terminal raw_input will throw EOFError.
        # Probably run by a script, go with predictable defaults.
        pass

    config = {'thot': {
        'website_url': website_url,
        'timezone': timezone,
        'templating_engine': settings['templating_engine'],
        'source': settings['source'],
        'author': {'name': author_name,
                   'email': author_email},
        'page_defaults': {'language': language},
    }}

    # copy quickstart template
    copytree(tmpl_path, settings['project_dir'])

    # before writing the settings file, make sure the _lib dir exists
    if not exists(settings['lib_dir']):
        makedirs(settings['lib_dir'])

    with codecs.open(settings['settings_path'],
                     'wb', encoding='utf-8') as configfile:
        configfile.write(yaml.dump(config, default_flow_style=False))

    return config['thot']


def main():
    parser = OptionParser(version='%prog ' + version)
    parser.add_option(
        '--quickstart',
        help='quickstart a thot site', action='store_true',
        dest='quickstart')
    parser.add_option(
        '--logging',
        help='sets the logging level. "info" (default) or "debug"')
    parser.add_option(
        '--hardlinks', action='store_true',
        help='instead of copying static files, creates hardlinks' \
             + ' - which is faster and saves space')
    parser.add_option(
        '-z', '--gzip', action='store_true',
        help='make a gzip-compressed copy of rendered files')
    parser.add_option(
        '-t', '--templating', default='mako',
        dest='templating_engine',
        help='templating engine (e.g. jinja2, mako) for output')
    parser.add_option(
        '-s', '--source', default='filesystem',
        help='data source, e.g. "filesystem" for files')
    options, args = parser.parse_args()

    try:
        project_dir = abspath(args[0])
    except IndexError:
        project_dir = abspath(getcwd())

    settings = {
        'project_dir': project_dir,
        'output_dir': join(project_dir, '_output'),
        'template_dir': join(project_dir, '_templates'),
        'lib_dir': join(project_dir, '_lib'),
        'url_path': join(project_dir, '_lib', 'urls.py'),
        'settings_path': join(project_dir, '_config.yml'),
        'hardlinks': options.hardlinks,
        'make_compressed_copy': options.gzip,
        'compress_if_ending': GZIP_ENDINGS,
        'templating_engine': options.templating_engine,
        'source': options.source,
        'build_tz': pytz.timezone(time.strftime('%Z', time.gmtime())),
        'build_time': pytz.utc.localize(datetime.utcnow()),
    }

    # configure logging
    logging_level = LOGGING_LEVELS.get(options.logging, logging.INFO)
    if has_logformatter:
        color = False
        if sys.stderr.isatty():
            try:
                curses.setupterm()
                if curses.tigetnum('colors') > 0:
                    color = True
            except: # pylint: disable=bare-except
                pass
        root_logger = logging.getLogger()
        root_logger.setLevel(logging_level)
        channel = logging.StreamHandler()
        channel.setFormatter(_LogFormatter(color=color))
        root_logger.addHandler(channel)
    else:
        logging.basicConfig(
            level=logging_level,
            format='%(asctime)s %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S')

    # quickstart
    if options.quickstart:
        u = quickstart(settings)
        settings.update(u)
        settings['build_time'] = pytz.utc.localize(datetime.utcnow())
        print('\nYour website will written to %s' % settings['output_dir'])
        sys.stdout.flush()

    # read settings file
    if exists(settings['settings_path']):
        with codecs.open(settings['settings_path'], 'rb',
                         encoding='utf-8') as configfile:
            config = yaml.safe_load(configfile.read())
        settings.update(config['pyll'] if 'pyll' in config else config['thot'])
    else:
        logging.error('Not found: %s', settings['settings_path'])
        sys.exit(1)
    logging.debug('settings %s', settings)

    # check and find the user's timezone
    if 'timezone' not in settings:
        settings['timezone'] = 'UTC'
        logging.warning(
            'No timezone has been set. Assuming all dates are in "%s".',
            settings['timezone'])
    elif settings['timezone'] not in pytz.all_timezones_set:
        logging.error(  # pylint: disable=logging-not-lazy
            'Timezone "%s" is absent from pytz.all_timezones_set.'
            + ' Try "Europe/Berlin", "UTC" or "US/Pacific".',
            settings['timezone'])
        sys.exit(1)
    settings['timezone'] = pytz.timezone(settings['timezone'])

    # find the data source
    for entrypoint in pkg_resources.iter_entry_points('thot.sources'):
        if entrypoint.name == settings['source']:
            source_cls = entrypoint.load()
            break
    else:
        logging.error('Data source "%s" could not be found.',
            settings['source'])
        sys.exit(1)
    # initialize site
    source = source_cls(
        settings['project_dir'], settings['build_time'],
        settings['timezone'],
        settings['default_template'] \
            if 'default_template' in settings \
            else get_templating_cls(settings['templating_engine'])\
                 .default_template,
        settings['page_defaults'] if 'page_defaults' in settings else dict(),
    )
    site = Site(settings, source)

    site.run()
    if options.hardlinks:
        print('Keep in mind: Output directory contains hardlinks.')

if __name__ == '__main__':
    main()
