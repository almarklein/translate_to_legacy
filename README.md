# translate_to_legacy

Single module to translate Python 3 code to Python 2.7. Write all your
code in Python 3, and convert it to Python 2.7 during installation.


## Docs


### General usage

```
from translate_to_legacy import LegacyPythonTranslator

translator = LegacyPythonTranslator(code)
translator.translate()
new_code = translator.dump()
```

TODO: how to use in a `setup.py`


### The Translator

The translator is the main class that manages the parsing and
translation process. The fixes that it applies are implemented as
methods that are prefixed with `fix_`. 

The `BaseTranslator` provides the basic functionality, and the
`LegacyPythonTranslator` implements the fixers specific for the purpose
to translate to legacy Python. To add more fixers, simply subclass and
add some methods. Existing fixers can be disabled by setting the
corresponding class attribute to None.

The `BaseTranslator` class has the following attributes:
    
* `tokens` - the list of found tokens.
* `parse()` - parse the code to generate tokens (is called automatically).
* `translate()` - apply the fixers to the tokens.
* `dump()` - get the result as a string. 


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
* `find_forward()` - find the position of a character to the right.
* `find_forward()` - find the position of a character to the left.


### How to write a fixer

TODO
