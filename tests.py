""" Run tests.
"""

import os
import subprocess
import pytest
from pytest import raises

from translate_to_legacy import (BaseTranslator, LegacyPythonTranslator,
                                 Token, CancelTranslation)


def test_token1():
    
    code = 'aa bb\ncc dd'
    
    t1 = Token(code, '', 0, 2)
    t2 = Token(code, '', 3, 5)
    t3 = Token(code, '', 6, 8)
    t4 = Token(code, '', 9, 11)
    
    assert t1.text == 'aa'
    assert t2.text == 'bb'
    assert t3.text == 'cc'
    assert t4.text == 'dd'
    
    assert t1.prev_char == ''
    assert t2.prev_char == 'a'
    assert t3.prev_char == ''
    assert t4.prev_char == 'c'
    
    assert t1.next_char == 'b'
    assert t2.next_char == ''
    assert t3.next_char == 'd'
    assert t4.next_char == ''
    

def test_token2():
    code = 'foo\n  foo\n    foo'
    t1, t2, t3 = BaseTranslator(code).tokens
    assert t1.indentation == 0
    assert t2.indentation == 2
    assert t3.indentation == 4
    
    code = 'x\nfoo, bar, spam\nx, x # y'
    tokens = BaseTranslator(code).tokens
    assert [t.text for t in tokens[0].line_tokens] == ['x']
    assert [t.text for t in tokens[1].line_tokens] == ['foo', 'bar', 'spam']
    assert [t.text for t in tokens[2].line_tokens] == ['foo', 'bar', 'spam']
    assert [t.text for t in tokens[3].line_tokens] == ['foo', 'bar', 'spam']
    assert [t.text for t in tokens[4].line_tokens] == ['x', 'x']


def test_base_translator():
    
    raises(TypeError, BaseTranslator)
    
    # Test small input, that tokens get initialized, and result is the same
    for code in ['', 'foo', 'foo, bar', 'foo, bar, spam']:
        t = BaseTranslator(code)
        assert t.dumps() == code
        t.translate()
        assert t.dumps() == code
        for token in t.tokens:
            assert hasattr(token,  'prev_token')
            assert hasattr(token,  'next_token')
    
    # Check same result on more realistic example
    code = 'spam = 3\ndef foo():\n  return XX\nfoo()'
    t = BaseTranslator(code)
    t.translate()
    assert t.dumps() == code
    
    # Apply a manual fix, check that result is correct
    assert t.tokens[-2].text == 'XX'
    t.tokens[-2].fix = 'YYYY'
    assert t.dumps() == code.replace('XX', 'YYYY')
    t.tokens[-2].fix = ''
    assert t.dumps() == code.replace('XX', '')


def test_tokenization():
    
    # Comments
    code = """# foo ''
    # ''' x '''
    # hi # hi
    """
    tokens = BaseTranslator(code).tokens
    assert len(tokens) == 3
    assert all([token.type == 'comment' for token in tokens])
    
    # Strings
    code = """
    ''' foo
    '''
    b''' bar
    '''
    'spam'
    b'eggs'
    ''
    b''
    """
    tokens = BaseTranslator(code).tokens
    assert len(tokens) == 6
    assert all([token.type == 'string' for token in tokens])
    
    # Empty strings
    for s in ('""', "''", 'b""', '""""""', "''''''", 'b""""""' ):
        code = s + ' ' + s
        tokens = BaseTranslator(code).tokens
        assert len(tokens) == 2
        assert all([token.type == 'string' for token in tokens])
    
    # Escaping strings
    code = '" \\"  \\" "'
    tokens = BaseTranslator(code).tokens
    assert len(tokens) == 1
    assert tokens[0].type == 'string'
    
    # Numbers
    for i, s in enumerate(('', '3', '0x10, 100',)):
        tokens = BaseTranslator(s).tokens
        assert len(tokens) == i
        assert all([token.type == 'number' for token in tokens])
    
    # keywords
    for i, s in enumerate(('', 'for', 'yield, return',)):
        tokens = BaseTranslator(s).tokens
        assert len(tokens) == i
        assert all([token.type == 'keyword' for token in tokens])
    
    # Identifiers
    for i, s in enumerate(('', 'foo', 'foo + bar1', 'foo, bar.spam2')):
        tokens = BaseTranslator(s).tokens
        assert len(tokens) == i
        assert all([token.type == 'identifier' for token in tokens])


def test_cancel():
    
    code = """
    from __future__ import print_function
    bla
    """
    
    raises(CancelTranslation, LegacyPythonTranslator(code).translate)


## Fixers


def test_fix_newstyle():
    code = """
    class Foo1:
        pass
    class Foo2(X):
        pass
    class Foo3(x, *bla):
        pass
    """
    new_code = LegacyPythonTranslator(code).translate()
    
    assert 'Foo1(object):' in new_code
    assert 'Foo2(X):' in new_code
    assert 'Foo3(x, *bla):' in new_code


def test_fix_super():
    code = """
    class Foo:
        def bar(self):
            super().bar()
        def spam(self):
            super().spam()
            class Foo2:
                def eggs(self):
                    super().eggs()
    def spam():
        super().x
    super().y
    """
    new_code = LegacyPythonTranslator(code).translate()
    
    # These should not have been touched
    assert 'super().x' in new_code
    assert 'super().y' in new_code
    
    # But these should
    assert 'super(Foo, self).bar()' in new_code
    assert 'super(Foo, self).spam()' in new_code
    assert 'super(Foo2, self).eggs()' in new_code


def test_fix_future():
    code = """
    foo = 2
    """
    new_code = LegacyPythonTranslator(code).translate()
    assert new_code.count('from __future__ import ') == 1
    assert new_code.index('__future__') < new_code.index('foo')
    
    code = """
    # bla
    'docstring'
    foo = 2
    """
    new_code = LegacyPythonTranslator(code).translate()
    assert new_code.count('from __future__ import ') == 1
    assert new_code.index('__future__') < new_code.index('foo')
    assert new_code.index('__future__') > new_code.index('bla')
    assert new_code.index('__future__') > new_code.index('docstring')


def test_fix_unicode_literals():
    
    if not hasattr(LegacyPythonTranslator, 'fix_unicode_literals'):
        pytest.skip('Not using unicode literals fixer')
    
    code = """
    ''' a docstring
    '''
    r'''and another '''
    a = 'x' ; b = "x" ; c = r'x' ; d = r"x" ;
    k = u'x' ; l = b"x" ;
    """
    new_code = LegacyPythonTranslator(code).translate()
    assert """a = u'x' """ in new_code
    assert """b = u"x" """ in new_code
    assert """c = ur'x' """ in new_code
    assert """d = ur"x" """ in new_code
    
    assert """a = 'x' """ not in new_code
    assert """d = r"x" """ not in new_code
    
    assert """k = u'x' """ in new_code
    assert """l = b"x" """ in new_code


def test_fix_unicode():
    code = """
    str(x)
    chr(y)
    bla = str
    isinstance(x, str)
    isinstance(y, (bytes, str))
    """
    new_code = LegacyPythonTranslator(code).translate()
    assert "unicode(x)" in new_code
    assert "unichr(y)" in new_code
    assert "bla = str" in new_code
    assert "isinstance(x, basestring)" in new_code
    assert "isinstance(y, (bytes, basestring))" in new_code


def test_fix_range():
    code = """
    range(1, 2, 3)
    y.range()
    """
    new_code = LegacyPythonTranslator(code).translate()
    assert 'xrange(1, 2, 3)' in new_code
    assert 'y.range()' in new_code


def test_fix_encode():
    code = """
    b = s.encode()
    s = b.decode()
    y = x.encode("ascii")
    x = y.decode("ascii")
    """
    new_code = LegacyPythonTranslator(code).translate()
    assert 's.encode("utf-8")' in new_code
    assert 'b.decode("utf-8")' in new_code
    assert 'x.encode("ascii")' in new_code
    assert 'y.decode("ascii")' in new_code


def test_fix_getcwd():
    code = """
    getcwd()
    os.getcwd()
    """
    new_code = LegacyPythonTranslator(code).translate()
    assert new_code.count('getcwd(') == 0
    assert new_code.count('getcwdu(') == 2


def test_fix_imports():
    code = """
    from urllib.request import urlopen
    import urllib.request.urlopen as urlopen
    import queue
    import urllib;
    from xx.yy import zz
    """
    new_code = LegacyPythonTranslator(code).translate()
    assert 'from urllib2 import urlopen' in new_code
    assert 'import urllib2.urlopen as urlopen' in new_code
    assert 'import Queue' in new_code
    assert 'from xx.yy import zz' in new_code
    assert 'import urllib;' in new_code


if __name__ == '__main__':
    os.chdir(os.path.dirname(__file__))
    pytest.main('-v -x --color=yes %s' % repr(__file__).lstrip('u'))
