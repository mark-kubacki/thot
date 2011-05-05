import markdown

from pyll.parser import Parser, parses


@parses('md', 'markdown')
class MarkdownParser(Parser):
    """Markdown Parser"""
    output_ext = 'html'

    def _parse_text(self):
        self.text = markdown.markdown(self.text,
                                      ['codehilite(css_class=highlight)'])

