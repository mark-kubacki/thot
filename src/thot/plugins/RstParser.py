import os
import logging

from docutils import nodes, utils
from docutils.core import publish_parts
from docutils.parsers.rst import directives, roles, Directive
from docutils.writers import html4css1

from thot.parser import Parser
from thot.utils import render_latex_to_image, embed_image

__all__ = [
    'RstParser',
]

try:
    import pygments
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import get_lexer_by_name, TextLexer
    has_pygments = True
except:
    has_pygments = False


# from sphinx.util.nodes

def set_source_info(directive, node):
    node.source, node.line = \
        directive.state_machine.get_source_and_line(directive.lineno)


# from sphinx.ext.mathbase

class math(nodes.Inline, nodes.TextElement):
    pass

class displaymath(nodes.Part, nodes.Element):
    pass

class eqref(nodes.Inline, nodes.TextElement):
    pass


def math_role(role, rawtext, text, lineno, inliner, options={}, content=[]):
    latex = utils.unescape(text, restore_backslashes=True)
    return [math(latex=latex)], []

def eq_role(role, rawtext, text, lineno, inliner, options={}, content=[]):
    text = utils.unescape(text)
    node = eqref('(?)', '(?)', target=text)
    try:
        node['docname'] = inliner.document.settings.env.docname
    except:
        pass
    return [node], []


class MathDirective(Directive):

    has_content = True
    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = True
    option_spec = {
        'label': directives.unchanged,
        'name': directives.unchanged,
        'nowrap': directives.flag,
    }

    def run(self):
        latex = '\n'.join(self.content)
        if self.arguments and self.arguments[0]:
            latex = self.arguments[0] + '\n\n' + latex
        node = displaymath()
        node['latex'] = latex
        node['label'] = self.options.get('name', None)
        if node['label'] is None:
            node['label'] = self.options.get('label', None)
        node['nowrap'] = 'nowrap' in self.options
        try:
            node['docname'] = self.state.document.settings.env.docname
        except:
            pass
        ret = [node]
        set_source_info(self, node)
        if hasattr(self, 'src'):
            node.source = self.src
        if node['label']:
            tnode = nodes.target('', '', ids=['equation-' + node['label']])
            self.state.document.note_explicit_target(tnode)
            ret.insert(0, tnode)
        return ret

# from pygments.external.rst-directive

class PygmentsDirective(Directive):
    """ Source code syntax hightlighting.
    """
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
#    option_spec = dict([(key, directives.flag) for key in VARIANTS])
    has_content = True

    def run(self):
        """
        Parse sourcecode using Pygments

        From http://bitbucket.org/birkenfeld/pygments-main/src/tip/external/rst-directive-old.py
        """
        try:
            lexer = get_lexer_by_name(self.arguments[0])
        except ValueError:
            # no lexer found - use the text one instead of an exception
            lexer = TextLexer()
        # take an arbitrary option if more than one is given
        formatter = HtmlFormatter(noclasses=False)
        parsed = highlight(u'\n'.join(self.content), lexer, formatter)
        return [nodes.raw('', parsed, format='html')]


# original work

class ThotHTMLWriter(html4css1.Writer):

    def __init__(self):
        html4css1.Writer.__init__(self)
        self.translator_class = ThotHTMLTranslator


class ThotHTMLTranslator(html4css1.HTMLTranslator):

    def _wrap_displaymath(self, math, label=None):
        parts = math.split('\n\n')
        ret = []
        for i, part in enumerate(parts):
            if label is not None and i == 0:
                ret.append('\\begin{split}%s\\end{split}' % part +
                           (label and '\\label{'+label+'}' or ''))
            else:
                ret.append('\\begin{split}%s\\end{split}\\notag' % part)
        return '\\begin{gather}\n' + '\\\\'.join(ret) + '\n\\end{gather}'

    def _render_math(self, latex, alt_text=None):
        png_path = render_latex_to_image(latex)
        if png_path:
            embedded_image = embed_image(png_path)
            os.remove(png_path)

            # build the actual element
            alt_text = self.encode(alt_text).strip() if alt_text \
                       else self.encode(latex).strip()
            return '<img class="math" src="%s" alt="%s" />' % \
                   (embedded_image, alt_text)
        else:
            logging.error('something went horribly wrong at rendering the formula: %s',
                          latex)
            return None

    def visit_math(self, node):
        elem = self._render_math('$' + node['latex'] + '$', node['latex'])
        if elem:
            self.body.append(elem)
        raise nodes.SkipNode

    def visit_displaymath(self, node):
        if node['nowrap']:
            latex = node['latex']
        else:
            latex = self._wrap_displaymath(node['latex'])
        elem = self._render_math(latex, node['latex'])
        if elem:
            self.body.append(self.starttag(node, 'div', CLASS='math'))
            self.body.append('<p>')
            if 'number' in node and node['number']:
                self.body.append('<span class="eqno">(%s)</span>' % node['number'])
            self.body.append(elem)
            self.body.append('</p></div>')
        raise nodes.SkipNode

    def visit_eqref(self, node):
        self.body.append('<a href="#equation-%s">' % node['target'])

    def depart_eqref(self, node):
        self.body.append('</a>')


# RST setup
roles.register_local_role('math', math_role)
roles.register_local_role('eq', eq_role)
directives.register_directive('math', MathDirective)
# if pygments is installed, register the "sourcecode" directive
if has_pygments:
    directives.register_directive(
        'sourcecode', PygmentsDirective)

class RstParser(Parser):
    """ReStructuredText Parser"""
    output_ext = 'html'
    parses = ['rst']

    def _parse_text(self):
        self.text = publish_parts(source=self.text,
                                  settings_overrides={
                                        "doctitle_xform": False,
                                        "initial_header_level": 2
                                  },
                                  writer=ThotHTMLWriter())['fragment']
