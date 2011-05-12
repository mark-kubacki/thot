import markdown

from thot.parser import Parser

__all__ = [
    'MarkdownParser',
]

class MarkdownParser(Parser):
    """Markdown Parser"""
    output_ext = 'html'
    parses = ['md', 'markdown']

    def _parse_text(self):
        self.text = markdown.markdown(self.text,
                                      ['codehilite(css_class=highlight)'])

