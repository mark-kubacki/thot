#!/usr/bin/env python
#
# Copyright 2011-2012 W-Mark Kubacki
#
# Licensed under the Reciprocal Public License, Version 1.5 (the "License");
# you may not use this file except in compliance with the License. You may
# obtain a copy of the License at
#
#     http://www.opensource.org/licenses/rpl1.5
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from codecs import open
from imp import load_source
from os import walk
from os.path import join, dirname, abspath
from setuptools import setup, find_packages

thot_mod = load_source('thot', join(dirname(abspath(__file__)),
                                    'src', 'thot', '__init__.py'))

def find_data_files(path, prefix):
    lst = []
    for dirpath, dirnames, filenames in walk(path):
        lst.append((prefix + dirpath.replace(path, ''),
                    [dirpath+'/'+f for f in filenames]))
    return lst

def one_supported_templating_engine():
    always_want = ['Mako >= 0.4.0']
    try:
        import jinja2
        return always_want + ['Jinja2']
    except ImportError:
        pass
    return always_want

def one_hyphenation_module():
    try: # from SF
        import wordaxe
        return ['wordaxe >= 1.0.1']
    except ImportError:
        pass
    return ['pyphen >= 0.7']

classifiers = [
    'Development Status :: 5 - Production/Stable',
    'Environment :: Console',
    'Environment :: Web Environment',
    'License :: OSI Approved :: Reciprocal Public License',
    'Programming Language :: Python :: 2.5',
    'Programming Language :: Python :: 2.6',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: Implementation :: CPython',
    'Programming Language :: Python :: Implementation :: Stackless',
    'Topic :: Internet :: WWW/HTTP',
    'Topic :: Text Processing',
    'Topic :: Text Processing :: Markup :: HTML',
    'Topic :: Text Processing :: Markup :: LaTeX',
    'Topic :: Text Processing :: Markup :: XML',
]

setup(
    name = 'thot',
    version = thot_mod.__version__,
    url = 'http://github.com/wmark/thot',
    download_url = 'http://binhost.ossdl.de/distfiles/thot-%s.tar.gz' % thot_mod.__version__,
    license = 'http://www.opensource.org/licenses/rpl1.5',
    description = 'A Python-Powered Static Site Generator',
    author = 'W-Mark Kubacki, Arthur Koziel',
    author_email = 'wmark+thot@hurrikane.de',
    long_description=open(
        join(dirname(__file__), 'README.rst'),
        'r', encoding='utf-8',
    ).read(),

    packages = find_packages('src'),
    package_dir = {'': 'src'},
    data_files = find_data_files('src/quickstart', 'share/thot/quickstart'),
    zip_safe = False,

    test_suite = 'nose.collector',

    entry_points = {
        # install the thot executable
        'console_scripts': [
            'thot = thot.app:main'
        ],
        # now come the shipped plugins
        'thot.templating_engines': [
            'mako = thot.plugins.MakoTemplating:MakoTemplate',
            'jinja2 = thot.plugins.Jinja2Templating:Jinja2Template',
        ],
        'thot.renderer': [
            'trivial = thot.parser:Parser',
            'markdown = thot.plugins.MarkdownParser:MarkdownParser',
            'rst = thot.plugins.RstParser:RstParser',
            'creole = thot.plugins.CreoleParser:CreoleParser',
            'trac = thot.plugins.TracParser:TracParser',
        ],
        'thot.processors': [
            'tags = thot.plugins.Tagging:PageTags',
            'category = thot.plugins.Tagging:PageCategory',
            'comments_from_files = thot.plugins.Comments:CommentsFromFile',
            'html = thot.plugins.HtmlPostProcessing:HtmlPostProcessor',
        ],
        'thot.sources': [
            'filesystem = thot.core:FilesystemSource',
        ],
    },
    install_requires = [
        'markdown',
        'docutils',
        'python-dateutil',
        'pytz',
        'PyYAML',
        'lxml >= 3.1.0',
    ] + one_supported_templating_engine() \
    + one_hyphenation_module(),
    classifiers=classifiers,
)
