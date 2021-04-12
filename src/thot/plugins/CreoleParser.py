"""Creole markup to HTML plugin.
"""
# pylint: disable=invalid-name

from creole import creole2html

from thot.parser import Parser

__all__ = [
    'CreoleParser',
]

class CreoleParser(Parser):
    output_ext = 'html'
    parses = ['creole', 'cre']

    def _parse_text(self):
        self.text = creole2html(self.text)
