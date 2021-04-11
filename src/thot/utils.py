import os
import shutil
import hashlib
import base64
import errno
import logging
import mimetypes

from fnmatch import fnmatch
from weakref import proxy as _proxy
from glob import glob
from tempfile import mkstemp, gettempdir
from subprocess import Popen, PIPE

try:
    import murmur
    has_murmur = True
except:
    has_murmur = False

__all__ = [
    'ordinal_suffix', 'datetimeformat', 'walk_ignore', 'get_hash_from_path',
    'equivalent_files', 'copy_file', 'partition',
    'supported_image_formats', 'default_image_format', 'render_latex_to_image', 'embed_image',
]

def ordinal_suffix(day):
    """
    Return the day with the ordinal suffix appended.

    Example: 1st, 2nd, 3rd, 4th, ...
    """
    day = int(day)
    if 4 <= day <= 20 or 24 <= day <= 30:
        suffix = "th"
    else:
        suffix = ["st", "nd", "rd"][day % 10 - 1]
    return "%s%s" % (day, suffix)

def datetimeformat(value, format='%H:%M / %d-%m-%Y'):
    """
    Return a formatted time string.

    Keyword arguments:
    value -- tuple or struct_time representing a time
    format -- the desired format
    """
    return value.strftime(format)

# monkeypatching for hardlinks; suggested by Dieter Deyke '2006
if os.name == 'nt':
    import ctypes
    def CreateHardLinkWin(src, dst):
        if not ctypes.windll.kernel32.CreateHardLinkA(dst, src, 0):
            raise OSError
    os.link = CreateHardLinkWin


def walk_ignore(path):
    "Custom walker that ignores specific filenames"
    ignores = ('.*', '*~', '#*', '_*',)
    for dirpath, dirnames, filenames in os.walk(path):
        for pattern in ignores:
            filenames[:] = [n for n in filenames if not fnmatch(n, pattern)]
            dirnames[:] = [n for n in dirnames if not fnmatch(n, pattern)]
        yield dirpath, dirnames, filenames

def get_hash_from_path(path, algorithm='sha1'):
    "Returns the hash of the file `path`."
    f = open(path)
    content = f.read()
    f.close()
    m = hashlib.new(algorithm)
    m.update(content)
    return m.hexdigest()

def equivalent_files(src, dst):
    "True if `src` and `dst` are the equivalent."
    # Same inode on same device <=> thus identical?
    src_stat, dst_stat = os.stat(src), os.stat(dst)
    if src_stat.st_dev == dst_stat.st_dev and src_stat.st_ino == dst_stat.st_ino:
        return True
    # Else, same file content?
    else:
        file_hash = murmur.file_hash if has_murmur else get_hash_from_path
        return file_hash(src) == file_hash(dst)

def copy_file(src, dst, hardlinks=False):
    """
    Copy `src` to `dst`.

    The parent directories for `dst` are created.

    To increase performance, this function will check if the file `dst`
    exists and compare the hash of `src` and `dst`. The file will
    only be copied if the hashes differ.

    If `hardlinks` is true, instead of copying hardlinks will be created
    if possible.
    """
    try:
        os.makedirs(os.path.dirname(dst))
    except OSError:
        pass

    if os.path.isfile(dst):
        if equivalent_files(src, dst):
            return False
    try:
        if hardlinks:
            try:
                os.link(src, dst)
                return True
            except OSError:
                logging.debug("Could not create hardlink for '%s'->'%s'.",
                              src, dst)
        shutil.copy2(src, dst)
        return True
    except IOError:
        logging.debug("Caught IOError when copying '%s'->'%s'.", src, dst)
        pass

def partition(alist, indices):
    """Splits at the given indices.

    >>> partition('crocodile', [4, 5])
    ['croc', 'o', 'dile']
    """
    return [alist[i:j] for i, j in zip([0]+indices, indices+[None])]


################################################################################
### output- and format-related helper
################################################################################

DOC_HEAD = r'''
\documentclass[12pt]{article}
\usepackage[utf8x]{inputenc}
\usepackage{amsmath}
\usepackage{amsthm}
\usepackage{amssymb}
\usepackage{amsfonts}
\usepackage{bm}
\pagestyle{empty}
'''

DOC_BODY = r'''
\begin{document}
%s
\end{document}
'''

supported_image_formats = ('svg', 'png')
default_image_format = 'png'
def render_latex_to_image(math, image_format='png'):
    """
    Renders the given formula (in LaTeX markup) to an image.

    - format png requires dvipng
    - format svg needs dvisvgm

    @param image_format can be any of: svg, png
    """
    # generate an input file
    latex = DOC_HEAD + DOC_BODY % math
    latex_fd, latex_filename = mkstemp(suffix='.tex')
    with open(latex_filename, 'wb') as latex_file:
        latex_file.write(latex)

    # call latex and friends
    latex_cmdline = [
        'latex', '--interaction=nonstopmode', latex_filename
    ]
    dvi_converter_cmdline = {
        'png': ['dvipng',
                '-o', latex_filename.replace('.tex', '.png'),
                '-T', 'tight',
                '-bg', 'Transparent',
                '-z9',
                latex_filename.replace('.tex', '.dvi'),
               ],
        'svg': ['dvisvgm',
                '--no-styles', '--no-fonts', # or what IE 10 will display is a mess
                latex_filename.replace('.tex', '.dvi'),
                ],
    }

    curdir = os.getcwd()
    os.chdir(gettempdir())

    try:
        for cmdline, cmdref in [(latex_cmdline, 'LaTeX'), (dvi_converter_cmdline[image_format], 'dvipng')]:
            try:
                p = Popen(cmdline, stdout=PIPE, stderr=PIPE)
            except OSError as err:
                if err.errno != errno.ENOENT: # no such file or directory
                    raise
                logging.error('%s command cannot be run, but is needed for math markup.', cmdref)
                return None

            stdout, stderr = p.communicate()
            if p.returncode != 0:
                logging.error('%s command exited with error: \n[stderr]\n%s\n[stdout]\n%s',
                              cmdref, stderr, stdout)
                return None
    finally:
        # now we have a bunch of files, of which we have to delete all but the PNG
        for filename in glob(latex_filename[0:-4] + '*'):
            if not filename.endswith('.'+image_format):
                os.remove(filename)
        os.chdir(curdir)

    # return the path of the PNG
    return latex_filename.replace('.tex', '.'+image_format)

def embed_image(image_path):
    """
    Returns a Data URI string of the image for embedding in HTML or CSS.
    """
    mimetype = mimetypes.guess_type(image_path)[0]
    b64img = base64.encodestring(open(image_path, 'rb').read()).replace("\n", "")
    return "".join(['data:', mimetype, ';base64,', b64img])
