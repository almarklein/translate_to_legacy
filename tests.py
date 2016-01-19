""" Run tests.
"""

import os
import subprocess
import pytest
from pytest import raises

from translate_to_legacy import Token, BaseTranslator, LegacyPythonTranslator


def test_token():
    
    text = 'aa bb\ncc dd'
    
    t1 = Token(text, '', 0, 2)
    t2 = Token(text, '', 3, 5)
    t3 = Token(text, '', 6, 8)
    t4 = Token(text, '', 9, 11)
    
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
    

def test_indentation():
    text = 'foo\n  foo\n    foo'
    t1, t2, t3 = BaseTranslator(text).tokens
    assert t1.indentation == 0
    assert t2.indentation == 2
    assert t3.indentation == 4


def test_base_translator():
    
    raises(TypeError, BaseTranslator)
    
    # Test small input, that tokens get initialized, and result is the same
    for text in ['', 'foo', 'foo, bar', 'foo, bar, spam']:
        t = BaseTranslator(text)
        assert t.dump() == text
        t.translate()
        assert t.dump() == text
        for token in t.tokens:
            assert hasattr(token,  'prev_token')
            assert hasattr(token,  'next_token')
    
    # Check same result on more realistic example
    text = 'spam = 3\ndef foo():\n  return XX\nfoo()'
    t = BaseTranslator(text)
    t.translate()
    assert t.dump() == text
    
    # Apply a manual fix, check that result is correct
    assert t.tokens[-2].text == 'XX'
    t.tokens[-2].fix = 'YYYY'
    assert t.dump() == text.replace('XX', 'YYYY')
    t.tokens[-2].fix = ''
    assert t.dump() == text.replace('XX', '')


def test_fix_newstyle():
    code = """
    class Foo1:
        pass
    class Foo2(X):
        pass
    class Foo3(x, *bla):
        pass
    """
    t = LegacyPythonTranslator(code)
    t.translate()
    new_code = t.dump()
    
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
    t = LegacyPythonTranslator(code)
    t.translate()
    new_code = t.dump()
    
    # These should not have been touched
    assert 'super().x' in new_code
    assert 'super().y' in new_code
    
    # But these should
    assert 'super(Foo, self).bar()' in new_code
    assert 'super(Foo, self).spam()' in new_code
    assert 'super(Foo2, self).eggs()' in new_code


if __name__ == '__main__':
    os.chdir(os.path.dirname(__file__))
    pytest.main('-v -x --color=yes %s' % repr(__file__))

