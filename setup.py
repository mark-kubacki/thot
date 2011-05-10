from imp import load_source
from os import walk
from os.path import join, dirname, abspath
from setuptools import setup, find_packages

pyll_mod = load_source('pyll', join(dirname(abspath(__file__)),
                                    'src', 'pyll', '__init__.py'))

def find_data_files(path, prefix):
    lst = []
    for dirpath, dirnames, filenames in walk(path):
        lst.append((prefix + dirpath.replace(path, ''),
                    [dirpath+'/'+f for f in filenames]))
    return lst

def one_supported_templating_engine():
    try:
        import mako
        return []
    except ImportError:
        pass
    try:
        import jinja2
        return []
    except ImportError:
        pass
    return ['Jinja2']

setup(
    name = 'pyll',
    version = pyll_mod.__version__,
    url = pyll_mod.__url__,
    license = 'BSD',
    description = 'A Python-Powered Static Site Generator',
    author = 'Arthur Koziel',

    packages = find_packages('src'),
    package_dir = {'': 'src'},
    package_data={
        'pyll': ['templates/default.html',
                 ],
    },
    data_files = find_data_files('src/quickstart', 'quickstart'),
    zip_safe = False,

    test_suite = 'nose.collector',

    entry_points = {
        # install the pyll executable
        'console_scripts': [
            'pyll = pyll.app:main'
        ],
        # now come the shipped plugins
        'pyll.templating_engines': [
            'mako = pyll.plugins.MakoTemplating:MakoTemplate',
            'jinja2 = pyll.plugins.Jinja2Templating:Jinja2Template',
        ],
        'pyll.renderer': [
            'trivial = pyll.parser:Parser',
            'markdown = pyll.plugins.MarkdownParser:MarkdownParser',
            'rst = pyll.plugins.RstParser:RstParser',
            'creole = pyll.plugins.CreoleParser:CreoleParser',
            'trac = pyll.plugins.TracParser:TracParser',
        ]
    },
    install_requires = [
        'markdown',
        'docutils',
        'python-dateutil==1.5',
        'pytz',
        'PyYAML',
    ] + one_supported_templating_engine(),
)

