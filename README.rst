====================================
Thot - the static site generator
====================================
:Info: See `github <http://github.com/wmark/thot>`_ for the latest source.
:Author: W-Mark Kubacki <wmark@hurrikane.de>

Derived from Arthur Koziel's `pyll <http://github.com/arthurk/pyll>`_.

About
=====
With **Thot** you can write your sites, documentation or even your blog with
your favourite text editor and then have everything rendered to static pages.

*Thot* understands Markdown_, RST_, Creole_ and Trac_'s
markup. You can still write everything as plaintext or HTML as well.
For templating you can resort to Mako_ or Jinja2_.

.. _Markdown: http://daringfireball.net/projects/markdown/syntax
.. _RST:      http://docutils.sourceforge.net/docs/user/rst/quickref.html
.. _Creole:   http://www.wikicreole.org/wiki/Creole1.0
.. _Trac:     http://trac.edgewall.org/wiki/WikiFormatting
.. _Mako:     http://www.makotemplates.org/
.. _Jinja2:   http://jinja.pocoo.org/

Still not what you're looking for? You can replace almost everything by your own
plugins. ;-)

License
========
Licensed under the Reciprocal Public License, Version 1.5
(http://www.opensource.org/licenses/rpl1.5).

Usage
========

Quickstart
------------
Run `thot --quickstart mysite` to have directory `mysite` created with a basic site
skeleton. You will be asked a series of questions regarding author's name and such by
that script.

`quickstart` obeys the optional parameter `-t <shortname>`, with "shortname" being
the shortname for a recognized templating engine. `mako` or `jinja2` without any
additional plugins.

Run the `thot` command to generate a site. The command looks for files with a .htm/.html,
.xml, .rst and .md/.markdown extension and parses them. Directories and files that start
with a dot or an underscore will be ignored. Everything else will be copied. The generated
site will be available in the `_output` directory.

Basics
--------
Place or edit your templates inside the `templates` directory of your site.
You can assign a page template `self` (thus none) or any other by "template: " keyword.

Every page consists of one header and one content section, in that order. It looks
like this:

::

    title: Hello World
    template: post.mak

    This is the content. Hello World!

The **header** is formatted in YAML_. You can access it from within the content by
variable `page`. With *Mako* by `${ page['title'] }` or *Jinja2* by `{{ page.title }}` for
example.

**Content** can be anything, from plaintext over html to markup, which is determined by
the file extension. Although the content will be subject to rendering by the templating
engine of your choice, you are free to abstain from using it.

You can find your default timezone and other settings in `_lib/settings.cfg`, which is
parsed as *YAML*.

.. _YAML: http://yaml.org/spec/1.1/

Reference
===========

Headers
----------
These headers currently have a function, and at least `title` has to be set:

title
  The page's title. Used within HTML's `<title />` tag.

status
  Recognized are "hidden", "draft" and "live". The latter being the fallback.
  Status "hidden" prevents pages from being listed in index pages - which makes sense
  for the index pages itself.

date
  Date and optionally time of the page. If missing, the "ctime" of the page's file is used.
  If the date is in the future, the page won't be published [1]_ before that date ("scheduled").
  Your (default) timezone is taken into consideration.
  The format is ISO-8691, ```yyyy-MM-dd``` such as in ```2011-09-07``` or ```yyyy-MM-dd HH:mm:ss```.

timezone
  Set this if you want to overwrite your default timezone for that page.
  Must be anything pytz_ recognizes, such as "UTC" or "Europe/Berlin".
  Makes only sense if `date` header is set, though.

expires
  If set, the page won't be published after that date (and optionally, time).

Headers overwrite global settings. That all is accessible under the variable `page`
to the templating engine.

.. _pytz: http://pytz.sourceforge.net/

Category and Tags
-------------------
*Thot* comes with two sample plugins, both in `Tagging.py`. They introduce some more headers:

index
  Can be a word or list of words. If set, makes the page an index for tags or categories.
  The page should have `status: hidden` set.
  For every tag or category as `field`: the page will be copied and rendered with variable
  `collection` being an ordered list of pages having that given
  `field_value`. The latter being the actual category or tag.

tags
  String or list of strings. *Tags* of the page.

category
  String or list of strings. The page's *category*.
  If not set the page will be filled under "uncategorized".

Plugins
---------
Please see `setup.py` for all available entry points. I have made sure there is at least
one plugin as implementation example for every entry point.

If you have a good idea for new plugins and need additional hooks for it, let me know!

Thot can take advantage of...
------------------------------

- LaTeX for math rendering. Needs `dvipng`.
  Enables RST directives `math` for formulas (with optional attribute `label`)
  and `eq` for linking to labelled formulas.

-- Mark

.. [1] A page is being "published" when it is written to `_output` directory.
