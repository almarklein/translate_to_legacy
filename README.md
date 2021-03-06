# translate_to_legacy

Single module to translate Python 3 code to Python 2.7. Write all your
code in Python 3, and convert it to Python 2.7 at install time.


### Purpose

Python 3 was first released in 2008. Initially people mostly wrote code
in Python 2, and converted that to Python 3 using 2to3. Later, it became
more popular to support both Python versions from a single code base
using e.g. six.py. Although this works well, it restricts the developer
from writing pretty Python 3 code. The aim of this project is to allow
developers to write in Python 3, and support Python 2 using a
translation step at build time.

This project is an alternative to lib3to2, but only uses a tokenizer
(and not an ast parser), which makes it faster and small enough to fit
in one module. This is enough to handle most fixes. Translations for
imports are handled differently though, see below. Strings/unicode/bytes
are also handled differtently (better IMHO) by this module.


### Limitations

For this to work, not all Python 3 functionality can be used. E.g. type
annotations, the `@` operator, and `nonlocal`. Further, not all relevant
fixers might be implemented yet, because for now I've focussed on what
I need. Fixers are easily added though (see below).


### General usage

In your `setup.py` add the following code (or similar):

```python
from translate_to_legacy import LegacyPythonTranslator
shutil.copytree(original_dir, legacy_dir)
LegacyPythonTranslator.translate_dir(legacy_dir, skip=files_to_skip)
``` 

For a bit more fine-grained control, here is how the translator class
can be used to translate strings from individual files:

```python
from translate_to_legacy import LegacyPythonTranslator
translator = LegacyPythonTranslator(code)
new_code = translator.translate()
```

To adopt this approach in your project and still allow single-source
distribution:
  
* add one module to the root of your project.
* in `setup.py`
  [invoke the translation](https://github.com/zoofIO/flexx/blob/master/setup.py#L56)
  at build time.
* in the root `__init__.py` add 
  [two lines](https://github.com/zoofIO/flexx/blob/master/flexx/__init__.py#L32-L33)
  to make legacy Python use the translated code.
* probably make a few modification to make the translations work correctly.
* optionally add more translations by subclassing `LegacyPythonTranslator`.
* resolve tricky situations like `isinstance(x, bytes)`.


### The translator

The translator is the main class that manages the parsing and
translation process. The fixes that it applies are implemented as
methods that are prefixed with `fix_`. 

The `BaseTranslator` provides the basic functionality, and the
`LegacyPythonTranslator` implements the fixers specific for the purpose
to translate to legacy Python. To add more fixers, simply subclass and
add some methods. Existing fixers can be disabled by setting the
corresponding class attribute to None.

The `BaseTranslator` class has the following attributes:
    
* `translate()` - apply the fixers to the tokens and return the result
  as a string. This should usually be all you need.
* `tokens` - the list of found tokens.
* `dump()` - get the result as a string (translate() calls this).
* `translate_dir()` - classmethod to translate all .py files in the given
  directory and its subdirectories. Skips files that match names
  in skip (which can be full file names, absolute paths, and paths
  relative to dirname). Any file that imports 'print_function'
  from __future__ is cancelled.


### How to write a custom fixer

To implement a custom fixer, create a subclass of the translator class and
implement a method prefixed with `fix_`:
    
```
class MyTranslator(LegacyPythonTranslator):
    
    def fix_range(self, token):
        if token.type == 'identifier' and token.text == 'range':
            if token.next_char == '(' and token.prev_char != '.':
                token.fix = 'xrange'
    
    def fix_make_legacy_slow(self, token):
        if token.type == 'keyword' and token.text == 'return':
            indent = token.indentation * ' '
            t = Token(token.total_text, 'custom', token.start, token.start)
            t.fix = '\n%simport time; time.sleep(0.1)\n' % indent
            return t
```

The code snippet above contains an example to make use of `xrange`,
which is a standard fixer. One can see how the fix is applied by setting
the `fix` attribute. In the second (less serious) fixer, a new token
is returned to insert a piece of code.


### The tokens

A token is a unit piece of code. This module only generates tokens for
constructs of interest, e.g. operators are not present in tokens. Each
token specifies its positionin the total text, so that replacements can
be easily made, without scrambling the text too much.

The fixers receive one token at a time, and must use it to determine
if a fix should be applied. To do this, surrounding tokens and
characters can be inspected. To apply a fix, simply set the `fix`
attribute.

The `Token` class has the following attributes:
    
* `type` - the type of token: 'comment', 'string', 'keyword',
  'number' or 'identifier'.
* `total_text` - the total text that the token is part of.
* `text` - the original text of the token.
* `start` - the start position in the total text.
* `end` - the end position in the total text.
* `fix` - the string to replace this token with.
* `prev_token` - the token to the left of this token.
* `next_token` - the token to the right of this token.
* `prev_char` - the first non-whitespace char to the left of this token
  that is still on the same line.
* `next_char` - the first non-whitespace char to the right of this token
  that is still on the same line.
* `line_tokens` - all (non-comment) tokens that are on the same line.
* `find_forward()` - find the position of a character to the right.
* `find_forward()` - find the position of a character to the left.
