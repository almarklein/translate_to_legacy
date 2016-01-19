# -*- coding: utf-8 -*-
# Copyright (c) 2016, Almar Klein
# The parser code and regexes are based on code by Rob Reilink from the
# IEP project.

"""
Single module to translate Python 3 code to Python 2.7. Write all your
code in Python 3, and convert it to Python 2.7 during installation.
"""

from __future__ import print_function

import re
import sys

ALPHANUM = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'

KEYWORDS = set(['False', 'None', 'True', 'and', 'as', 'assert', 'break', 
        'class', 'continue', 'def', 'del', 'elif', 'else', 'except', 'finally', 
        'for', 'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 
        'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'try', 'while', 
        'with', 'yield'])

# This regexp is used to find the tokens
tokenProg = re.compile(
    '(#)|' +					# Comment or
    '(' +  						# Begin of string group (group 1)
    '[bB]?[uU]?[rR]?' +			# Possibly bytes, unicode, raw
    '("""|\'\'\'|"|\')' +		# String start (triple qoutes first, group 3)
    ')|' +   					# End of string group
    '([' + ALPHANUM + '_]+)'  	# Identifiers/numbers (group 1) or
    )

# For a comment or a type of string, get the RegExp program to matches the end
endProgs = {
    "#": re.compile(r"\r?\n"),
    "'": re.compile(r"(^|[^\\])(\\\\)*'"),
    '"': re.compile(r'(^|[^\\])(\\\\)*"'),
    "'''": re.compile(r"(^|[^\\])(\\\\)*'''"),
    '"""': re.compile(r'(^|[^\\])(\\\\)*"""')
    }


class Token:
    """ A token in the source code. The type of token can be a comment,
    string, keyword, number or identifier. It has functionality to get
    information on neighboring tokens and neighboring characters. This
    should be enough to do all necessary translations.
    
    If the ``fix`` attribute is set, that string will replace the
    current string.
    """
    
    def __init__(self, total_text, type, start, end):
        self.total_text = total_text
        self.type = type
        self.start = start
        self.end = end
        self.fix = None
    
    def __repr__(self):
        return '<token %r>' % self.text
    
    def __len__(self):
        return self.end - self.start
    
    def find_forward(self, s):
        """ Find the position of a character to the right.
        """
        return self.total_text.find(s, self.end)
    
    def find_backward(self, s):
        """ Find the position of a character to the left.
        """
        return self.total_text.rfind(s, 0, self.start)
        
    @property
    def text(self):
        """ The original text of the token.
        """
        return self.total_text[self.start:self.end]
    
    @property
    def prev_char(self):
        """ The first non-whitespace char to the left of this token
        that is still on the same line.
        """
        i = max(0, self.find_backward('\n'))
        line = self.total_text[i:self.start]
        line = re.sub(r"\s+", '', line)  # remove whitespace
        return line[-1:]  # return single char or empty string
    
    @property
    def next_char(self):
        """ Get the first non-whitespace char to the right of this token
        that is still on the same line.
        """
        i = min(len(self.total_text), self.find_forward('\n'))
        line = self.total_text[self.end:i]
        line = re.sub(r"\s+", '', line)  # remove whitespace
        return line[:1]  # return single char or empty string
    
    @property
    def indentation(self):
        """ The number of chars that the current line uses for indentation.
        """
        i = max(0, self.find_backward('\n'))
        line1 = self.total_text[i+1:self.start]
        line2 = line1.lstrip()
        return len(line1) - len(line2)


class BaseTranslator:
    """ Translate Python code.
    """
    
    def __init__(self, text):
        self._text = text
        self._tokens = None
    
    @property
    def tokens(self):
        """ The list of tokens.
        """
        if self._tokens is None:
            self.parse()
        return self._tokens
    
    def parse(self):
        """ Generate tokens by parsing the code.
        """
        
        self._tokens = []
        pos = 0
        
        # Find tokens
        while True:
            token = self._find_next_token(pos)
            if token is None:
                break
            self._tokens.append(token)
            pos = token.end
        
        # Link tokens
        if self._tokens:
            self._tokens[0].prev_token = None
            self._tokens[len(self._tokens)-1].next_token = None
        for i in range(0, len(self._tokens)-1):
            self._tokens[i].next_token = self._tokens[i+1]
        for i in range(1, len(self._tokens)):
            self._tokens[i].prev_token = self._tokens[i-1]
    
    def _find_next_token(self, pos):
        """ Returns a token or None if no new tokens can be found.
        """
        
        text = self._text
        
        # Init tokens, if pos too large, were done
        if pos > len(text):
            return None
        
        # Find the start of the next string or comment
        match = tokenProg.search(text, pos)
        
        if not match:
            return None
        if match.group(1):
            # Comment
            start = match.start()
            end = endProgs['#'].search(text, start).start()
            return Token(text, 'comment', start, end)
        elif match.group(2) is not None:
            # String
            start = match.start()
            string_style = match.group(3)
            end = endProgs[string_style].search(text, start+1).end()
            return Token(text, 'string', start, end)
        else:
            # Identifier ("a word or number") Find out whether it is a key word
            identifier = match.group(4)
            tokenArgs = match.start(), match.end()
            if identifier in KEYWORDS:
                return Token(text, 'keyword', *tokenArgs)
            elif identifier[0] in '0123456789':
                return Token(text, 'number', *tokenArgs)
            else:
                return Token(text, 'identifier', *tokenArgs)
    
    def translate(self):
        """ Translate the code by applying fixes to the tokens.
        """
        
        # Collect fixers
        fixers = []
        for name in dir(self):
            if name.startswith('fix_'):
                fixers.append(getattr(self, name))
        
        # Apply fixers
        for token in self.tokens:
            for fixer in fixers:
                fixer(token)
    
    def dump(self):
        """ Return a string with the translated code.
        """
        
        text = self._text
        pos = len(self._text)
        pieces = []
        for t in reversed(self.tokens):
            pieces.append(text[t.end:pos])
            pieces.append(t.fix if t.fix is not None else t.text)
            pos = t.start
        pieces.append(text[:pos])
        return ''.join(reversed(pieces))


class LegacyPythonTranslator(BaseTranslator):
    """ A Translator to translate Python 3 to Python 2.7.
    """
    
    def fix_newstyle(self, token):
        """ Fix to always use new style classes.
        """
        if token.type == 'keyword' and token.text == 'class':
            nametoken = token.next_token
            if nametoken.next_char != '(':
                nametoken.fix = '%s(object)' % nametoken.text
    
    def fix_super(self, token):
        """ Fix super() -> super(Cls, self)
        """
        # First keep track of the current class
        if token.type == 'keyword':
            if token.text == 'class':
                self._current_class = token.indentation, token.next_token.text
            elif token.text == 'def':
                cls_indent, cls_name = getattr(self, '_current_class', (0, ''))
                if token.indentation <= cls_indent:
                    self._current_class = 0, ''
        
        # Then check for super
        if token.type == 'identifier' and token.text == 'super':
            if token.prev_char != '.' and token.next_char == '(':
                i = token.find_forward(')')
                sub = token.total_text[token.end:i+1]
                if re.sub(r"\s+", '', sub) == '()':
                    cls_indent, cls_name = getattr(self, '_current_class', (0, ''))
                    if cls_name:
                        token.end = i + 1
                        token.fix = 'super(%s, self)' % cls_name
