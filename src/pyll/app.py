import BaseHTTPServer
from codecs import open
from datetime import datetime
import imp
import logging
import warnings
import yaml
from optparse import OptionParser
from os import makedirs, getcwd, getlogin, listdir, sep as dirsep
from os.path import join, dirname, abspath, \
                    exists, normpath
from shutil import copytree
import sys
import pytz

from pyll import __version__, autoreload
from pyll.core import Site
from pyll.server import LanyonHTTPRequestHandler

LOGGING_LEVELS = {'info': logging.INFO, 'debug': logging.DEBUG}

def quickstart(settings):
    login = getlogin()

    author_name = raw_input("Author Name [%s]: " % login) or login
    author_email_default = '%s@example.org' % login
    author_email = raw_input("Author Email [%s]: " % author_email_default) or author_email_default
    website_url_default = 'http://www.example.org'
    website_url = raw_input("Website URL [%s]: " % website_url_default) or website_url_default
    timezone = 'tbd'
    while not timezone in pytz.all_timezones_set:
        if timezone != 'tbd': print "Sorry, '%s' is unknown. Try again." % timezone
        timezone = raw_input("Your timezone, e.g. 'Europe/Berlin', 'US/Eastern', 'US/Pacific', \n"
                             + "'UTC' or something other: ")
    config = {'pyll': {
        'author_name': author_name,
        'author_email': author_email,
        'website_url': website_url,
        'timezone': timezone,
        'templating_engine': settings['templating_engine'],
    }}

    # copy quickstart template
    tmpl_path = normpath(join(dirname(abspath(__file__)), '..', 'quickstart', settings['templating_engine']))
    copytree(tmpl_path, settings['project_dir'])

    # before writing the settings file, make sure the _lib dir exists
    if not exists(settings['lib_dir']):
        makedirs(settings['lib_dir'])
    
    with open(settings['settings_path'], 'wb', encoding='utf-8') as configfile:
        configfile.write(yaml.dump(config, default_flow_style=False))

    return config['pyll']

def load_plugins_from(path):
    # the following or glob.glob(path+'/*.py')
    mods = [f for f in listdir(path) if f.endswith('.py')]
    for mod in mods:
        try:
            imp.load_source('plugin%s' % mod, path+dirsep+mod)
        except IOError as e:
            logging.debug('couldn\'t load from "%s"->%s', path, mod)
        except ImportError as e:
            logging.debug('couldn\'t load from "%s"->%s due to %s', path, mod, e.message)

def main():
    parser = OptionParser(version="%prog " + __version__)
    parser.add_option('--quickstart',
                      help="quickstart a pyll site", action="store_true",
                      dest="quickstart")
    parser.add_option('--logging',
                      help="sets the logging level. 'info' (default) or 'debug'")
    parser.add_option('--server', help='start a local webserver',
                      action="store_true", dest="server")
    parser.add_option('--hardlinks', action="store_true",
                      help="instead of copying static files, creates hardlinks" \
                           + " - which is faster and saves space")
    parser.add_option('-t', '--templating', default='jinja2',
                      dest='templating_engine',
                      help="templating engine (e.g. jinja2, mako) for output")
    options, args = parser.parse_args()

    try:
        project_dir = abspath(args[0])
    except IndexError:
        project_dir = abspath(getcwd())
    
    settings = {'project_dir': project_dir,
                'output_dir': join(project_dir, '_output'),
                'template_dir': join(project_dir, '_templates'),
                'lib_dir': join(project_dir, '_lib'),
                'url_path': join(project_dir, '_lib', 'urls.py'),
                'settings_path': join(project_dir, '_lib', 'settings.cfg'),
                'hardlinks': options.hardlinks,
                'templating_engine': options.templating_engine,
                'build_time': pytz.utc.localize(datetime.utcnow())}

    # configure logging
    logging_level = LOGGING_LEVELS.get(options.logging, logging.INFO)
    logging.basicConfig(level=logging_level,
                        format='%(asctime)s %(levelname)s: %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    
    # quickstart
    if options.quickstart:
        quickstart(settings)
        settings['build_time'] = pytz.utc.localize(datetime.utcnow())
        print '\nYour website will be available at %s' % settings['output_dir']

    # read settings file
    if exists(settings['settings_path']):
        with open(settings['settings_path'], 'rb', encoding='utf-8') as configfile:
            config = yaml.safe_load(configfile.read())
        settings.update(config['pyll'])
    logging.debug('settings %s', settings)
    # check and find the user's timezone
    if not 'timezone' in settings:
        settings['timezone'] = 'UTC'
        logging.warn('No timezone has been set. Assuming all dates are in "%s".',
                     settings['timezone'])
    elif settings['timezone'] not in pytz.all_timezones_set:
        logging.error('Timezone "%s" is unknown (not in pytz.all_timezones_set).'
                      + ' Try "Europe/Berlin", "UTC" or "US/Pacific" for example.',
                      settings['timezone'])
        sys.exit(1)
    settings['timezone'] = pytz.timezone(settings['timezone'])

    # read in all available plugins
    warnings.filterwarnings("ignore", r"Parent module .* absolute import",
                            RuntimeWarning)
    load_plugins_from(normpath(join(dirname(abspath(__file__)), 'plugins')))

    # initialize site
    site = Site(settings)

    def runserver(server_class=BaseHTTPServer.HTTPServer,
                  handler_class=LanyonHTTPRequestHandler,
                  *args, **kwargs):
        site.run()
        handler_class.rootpath = settings['output_dir']
        server_address = ('', 8000)
        httpd = server_class(server_address, handler_class)
        logging.info("serving at port %s", server_address[1])
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            sys.exit(0)

    if options.server:
        autoreload.main(runserver, (), {'paths': (
            settings['project_dir'],
            settings['template_dir'],
            settings['lib_dir'])})
    else:
        site.run()
        if options.hardlinks:
            print "Keep in mind: Output directory contains hardlinks."

if __name__ == '__main__':
    main()
