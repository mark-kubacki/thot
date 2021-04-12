"""Plugin for ingesting Markdown.
"""
# pylint: disable=invalid-name

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
        self.text = markdown.markdown(
            self.text,
            extensions=['codehilite(css_class=highlight)'],
        )

