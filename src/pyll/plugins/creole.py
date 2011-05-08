from creole import creole2html

from pyll.parser import Parser, parses

__all__ = [
    'CreoleParser',
]

@parses('creole', 'cre')
class CreoleParser(Parser):
    "Creole to HTML parser."
    output_ext = 'html'

    def _parse_text(self):
        self.text = creole2html(self.text)
