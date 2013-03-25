====================================
Thot - the static site generator
====================================
:Info: See `github <http://github.com/wmark/thot>`_ for the latest source.
:Author: W-Mark Kubacki <wmark@hurrikane.de>

Derived from Arthur Koziel’s `pyll <http://github.com/arthurk/pyll>`_.

About
=====
With **Thot** you can write your sites, documentation or even your blog with
your favourite text editor and then have everything rendered to static files.

*Thot* understands Markdown_, RST_, Creole_ and Trac_’s markup for your content.
You can still write everything as plaintext or HTML as well if you like.
For templating (embedding your content into a design) you can chose between Mako_ and Jinja2_.

.. _Markdown: http://daringfireball.net/projects/markdown/syntax
.. _RST:      http://docutils.sourceforge.net/docs/user/rst/quickref.html
.. _Creole:   http://www.wikicreole.org/wiki/Creole1.0
.. _Trac:     http://trac.edgewall.org/wiki/WikiFormatting
.. _Mako:     http://www.makotemplates.org/
.. _Jinja2:   http://jinja.pocoo.org/

The nice thing about *Thot* is that you can replace almost everything by your own
plugins easily.

Some blogs powered by Thot:

- `Tsu’s blog on EVE Online <http://tsu.eve-connect.com/2011/12/15-durchs-Lowsec-fliegen-oder-per-Blackops-Portal-springen.html>`_

License
========
Licensed under the Reciprocal Public License, Version 1.5
(http://www.opensource.org/licenses/rpl1.5).

… which means you can use it as-is even for commercial purposes, free of charge, as long
as you notify me about any modifications you’ve made along with a patch with them.
And yes, of course, your templates are not covered by that — though I hereby kindly ask
you to add/leave the “`meta-generator: Thot`” entry in your HTML’s HEAD for statistical purposes.

Usage
========

Quickstart
------------
Run ``thot --quickstart mysite`` to have directory “`mysite`” created with a basic site
skeleton. You will be asked a series of questions regarding default values for author’s name
and such by that script. Your answers will result in file ``_lib/settings.cfg``.

``quickstart`` obeys the optional parameter `-t <shortname>`, with “shortname” being
the shortname for a recognized templating engine: `mako` or `jinja2`, Mako being preferred.

Run ``thot`` to generate a site. The command looks for files with extensions .htm/.html,
.xml, .rst and .md/.markdown; parses them and passes the results to your template(s).
— “Parsing” means transforming the markup (for example Markdown or RST) to HTML. —
Directories and files that start with a dot or an underscore will be ignored,
everything else (i.e. images) will be copied. The the results will be available
in “`_output`”.

Basics
--------
Your templates go into the “`_templates`” directory of your site.
Every page has a template, either “`self`” (thus none, i.e. for XML, RSS or Atom feeds)
or any of your own liking determined by “`template:`” keyword.

Every page consists of one “header” (with keywords) and one “content” section, in that order.
It looks like this:

::

    title: Hello World
    template: post.mak
    category: article
    tags: [static blog, CDN, like Jekyll]

    This is the content. Hello World!

The **header** is formatted in YAML_. You can access it from within the content by
variable “`page`”. With *Mako* by `${ page['title'] }` or *Jinja2* by `{{ page.title }}` for
example.

**Content** can be anything, from plaintext over html to markup, which is determined by
the file extension. Although the content will be subject to rendering by the templating
engine of your choice, you are free to abstain from using it.

Default settings can be found in “`_lib/settings.cfg`”, which is parsed as *YAML*.

.. _YAML: http://yaml.org/spec/1.1/

Reference
===========

Headers
----------
This list is not complete, but you can use the following keywords. At least “`title`” has to be set:

title
  The page’s title. Used within HTML’s `<title>`.

status
  Recognized are “hidden”, “draft” and “live”. The latter being assumed if you didn’t set anything.
  Status “hidden” prevents pages from being listed in index-pages - which makes sense
  for the index pages (contents, archive…) itself.

date
  Creation date — and optionally time — of the page. If missing, the “`ctime`” of the page’s file is used.
  If the date is in the future, the page won’t be published [1]_ before that (say “scheduled”),
  sparing you the embarrassment of leaking something prematurely. (Like a Fortune 500
  company once did, announcing a product on their homepage before their CEO held the presentation. Ouch.)
  Your (default) timezone is taken into account.
  Format is ISO-8691, ``yyyy-MM-dd`` such as in ``2011-09-07`` or ``yyyy-MM-dd HH:mm:ss``.

timezone
  Set this if you want to overwrite your default timezone for that page.
  Must be anything pytz_ recognizes, for example “UTC” or “Europe/Berlin”.
  Makes only sense if `date` header is set, though, and has an effect on the
  publishing date and RSS/Atom feed, where timezones are added to date-times.
  Globetrotters will like it — but if in doubt skip this entry.

expires
  If set, *Thot* will skip that page after the given date (and optionally, time)
  excluding it from being published [1]_.

Headers overwrite settings found in “`_lib/settings.cfg`”. You can access everything, including
the header(s), using “`page`” and the vanilla settings using “`settings`” (following is Mako and HTML5):

::

    <article>
      <hgroup>
        <h1>${ page['title'] }</h1>
        <h2>how ${ settings['author']['name'] } sees it</h2>
      </hgroup>
      <time pubdate="pubdate" datetime="${ page['date'] | n,datetimeformat("%Y-%m-%dT%H:%M:%S") }">
        ${ page['date'] | n,datetimeformat("%b %d") }
      </time>
      <p>${ page['content'] }</p>
    </article>

.. _pytz: http://pytz.sourceforge.net/

Category and Tags
-------------------
*Thot* comes with two sample plugins, both in `Tagging.py`. They introduce some more headers:

index
  Can be a word or list of words. If set marks an index-page for tags or categories.
  Don’t forget to set “`status: hidden`”, too.
  For every tag or category as “`field`”: the page will be copied, and rendered
  with variable “`collection`” holding an ordered list of *pages* having the given
  “`field_value`” — which is the actual category or tag.

tags
  String or list of strings. *Tags* of the page.

category
  String or list of strings. The page’s *category*.
  If not set the page will be filed under “uncategorized”.

Plugins
---------
Please see `setup.py` for all available **entry points**. I have made sure to include at least
one plugin for every *entry point* as implementation example for you.

If you have a good idea for new plugins and need additional hooks for it, let me know!

Thot can take advantage of...
------------------------------

- LaTeX for math rendering. Needs **dvipng** and “`utf8x`”
  (from *dev-texlive/texlive-latexextra* in Gentoo and ChromeOS).
  Enables RST directives “`math`” for formulas (with optional attribute “`label`”)
  and “`eq`” for linking to labelled formulas.
- **Pyphen** and **Wordaxe** for server-side hyphenation.

— Mark

.. [1] ‘Published’ means being written to “`_output`” directory.
