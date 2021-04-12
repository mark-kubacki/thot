# Copyright 2011-2021 Mark Kubacki
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
"""Setup script for Thot."""

import codecs
import importlib
import os

import setuptools

spec = importlib.util.spec_from_file_location('thot',
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'src', 'thot', '__init__.py'
    )
)
thot_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(thot_mod)

def find_data_files(path, prefix):
    lst = []
    for dirpath, _, filenames in os.walk(path):
        lst.append((prefix + dirpath.replace(path, ''),
                    [dirpath+'/'+f for f in filenames]))
    return lst

classifiers = [
    'Development Status :: 5 - Production/Stable',
    'Environment :: Console',
    'Environment :: Web Environment',
    'License :: OSI Approved :: Reciprocal Public License',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.9',
    'Programming Language :: Python :: Implementation :: CPython',
    'Programming Language :: Python :: Implementation :: Stackless',
    'Topic :: Internet :: WWW/HTTP',
    'Topic :: Text Processing',
    'Topic :: Text Processing :: Markup :: HTML',
    'Topic :: Text Processing :: Markup :: LaTeX',
    'Topic :: Text Processing :: Markup :: XML',
]

setuptools.setup(
    name = 'thot',
    version = thot_mod.__version__,
    url = 'http://github.com/wmark/thot',
    download_url = \
        'https://github.com/wmark/thot/releases/download/v{0}/thot-{0}.tar.gz' \
        .format(thot_mod.__version__),
    license = 'http://www.opensource.org/licenses/rpl1.5',
    description = 'A Python-Powered Static Site Generator',
    author = 'W-Mark Kubacki, Arthur Koziel',
    author_email = 'wmark+thot@hurrikane.de',
    long_description=codecs.open(
        os.path.join(os.path.dirname(__file__), 'README.rst'),
        'r', encoding='utf-8',
    ).read(),

    packages = setuptools.find_packages('src'),
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
        'pyphen >= 0.7',
        'wordaxe >= 1.0.1',
        'wordaxe >= 1.1.0 ; python_version>="3"',
        'Mako >= 0.4.0',
    ],
    tests_require=[
        'nose',
    ],
    extras_require={
        'creole': ['creole'],
        'trac':   ['trac'],
        'code':   ['pygments'],
        'jinja':  ['Jinja2'],
    },
    classifiers=classifiers,
)
