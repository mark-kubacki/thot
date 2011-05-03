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

    # install the pyll executable
    entry_points = {
        'console_scripts': [
            'pyll = pyll.app:main'
        ]
    },
    install_requires = [
        'markdown',
        'docutils',
        'Jinja2',
        'python-dateutil==1.5',
        'pytz',
        'PyYAML',
    ],
)

