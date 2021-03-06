# Human friendly input/output in Python.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: July 19, 2015
# URL: https://humanfriendly.readthedocs.org

"""
The :mod:`~humanfriendly.text` module contains simple functions to manipulate text:

- The :func:`concatenate()` and :func:`pluralize()` functions make it easy to
  generate human friendly output.

- The :func:`format()`, :func:`compact()` and :func:`dedent()` functions
  provide a clean and simple to use syntax for composing large text fragments
  with interpolated variables.

- The :func:`tokenize()` function parses simple user input.
"""

# Standard library modules.
import math
import re
import textwrap

def concatenate(items):
    """
    Concatenate a list of items in a human friendly way.

    :param items: A sequence of strings.
    :returns: A single string.

    >>> from humanfriendly.text import concatenate
    >>> concatenate(["eggs", "milk", "bread"])
    'eggs, milk and bread'
    """
    items = list(items)
    if len(items) > 1:
        return ', '.join(items[:-1]) + ' and ' + items[-1]
    elif items:
        return items[0]
    else:
        return ''

def format(text, *args, **kw):
    """
    Format a string using the string formatting operator and/or :func:`str.format()`.

    :param text: The text to format (a string).
    :param args: Any positional arguments are interpolated into the text using
                 the string formatting operator (``%``). If no positional
                 arguments are given no interpolation is done.
    :param kw: Any keyword arguments are interpolated into the text using the
               :func:`str.format()` function. If no keyword arguments are given
               no interpolation is done.
    :returns: The text with any positional and/or keyword arguments
              interpolated (a string).

    The implementation of this function is so trivial that it seems silly to
    even bother writing and documenting it. Justifying this requires some
    context :-).

    **Why format() instead of the string formatting operator?**

    For really simple string interpolation Python's string formatting operator
    is ideal, but it does have some strange quirks:

    - When you switch from interpolating a single value to interpolating
      multiple values you have to wrap them in tuple syntax. Because
      :func:`format()` takes a `variable number of arguments`_ it always
      receives a tuple (which saves me a context switch :-). Here's an
      example:

      >>> from humanfriendly.text import format
      >>> # The string formatting operator.
      >>> print('the magic number is %s' % 42)
      the magic number is 42
      >>> print('the magic numbers are %s and %s' % (12, 42))
      the magic numbers are 12 and 42
      >>> # The format() function.
      >>> print(format('the magic number is %s', 42))
      the magic number is 42
      >>> print(format('the magic numbers are %s and %s', 12, 42))
      the magic numbers are 12 and 42

    - When you interpolate a single value and someone accidentally passes in a
      tuple your code raises a :exc:`~exceptions.TypeError`. Because
      :func:`format()` takes a `variable number of arguments`_ it always
      receives a tuple so this can never happen. Here's an example:

      >>> # How expecting to interpolate a single value can fail.
      >>> value = (12, 42)
      >>> print('the magic value is %s' % value)
      Traceback (most recent call last):
        File "<stdin>", line 1, in <module>
      TypeError: not all arguments converted during string formatting
      >>> # The following line works as intended, no surprises here!
      >>> print(format('the magic value is %s', value))
      the magic value is (12, 42)

    **Why format() instead of the str.format() method?**

    When you're doing complex string interpolation the :func:`str.format()`
    function results in more readable code, however I frequently find myself
    adding parentheses to force evaluation order. The :func:`format()` function
    avoids this because of the relative priority between the comma and dot
    operators. Here's an example:

    >>> "{adjective} example" + " " + "(can't think of anything less {adjective})".format(adjective='silly')
    "{adjective} example (can't think of anything less silly)"
    >>> ("{adjective} example" + " " + "(can't think of anything less {adjective})").format(adjective='silly')
    "silly example (can't think of anything less silly)"
    >>> format("{adjective} example" + " " + "(can't think of anything less {adjective})", adjective='silly')
    "silly example (can't think of anything less silly)"

    The :func:`compact()` and :func:`dedent()` functions are wrappers that
    combine :func:`format()` with whitespace manipulation to make it easy to
    write nice to read Python code.

    .. _variable number of arguments: https://docs.python.org/2/tutorial/controlflow.html#arbitrary-argument-lists
    """
    if args:
        text %= args
    if kw:
        text = text.format(**kw)
    return text

def compact(text, *args, **kw):
    '''
    Compact whitespace in a string.

    Trims leading and trailing whitespace, replaces runs of whitespace
    characters with a single space and interpolates any arguments using
    :func:`format()`.

    :param text: The text to compact (a string).
    :param args: Any positional arguments are interpolated using :func:`format()`.
    :param kw: Any keyword arguments are interpolated using :func:`format()`.
    :returns: The compacted text (a string).

    Here's an example of how I like to use the :func:`compact()` function, this
    is an example from a random unrelated project I'm working on at the moment::

        raise PortDiscoveryError(compact("""
            Failed to discover port(s) that Apache is listening on!
            Maybe I'm parsing the wrong configuration file? ({filename})
        """, filename=self.ports_config))

    The combination of :func:`compact()` and Python's multi line strings allows
    me to write long text fragments with interpolated variables that are easy
    to write, easy to read and work well with Python's whitespace
    sensitivity.
    '''
    non_whitespace_tokens = text.split()
    compacted_text = ' '.join(non_whitespace_tokens)
    return format(compacted_text, *args, **kw)

def dedent(text, *args, **kw):
    """
    Dedent a string (remove common leading whitespace from all lines).

    Removes common leading whitespace from all lines in the string using
    :func:`textwrap.dedent()`, removes leading and trailing empty lines using
    :func:`trim_empty_lines()` and interpolates any arguments using
    :func:`format()`.

    :param text: The text to dedent (a string).
    :param args: Any positional arguments are interpolated using :func:`format()`.
    :param kw: Any keyword arguments are interpolated using :func:`format()`.
    :returns: The dedented text (a string).

    The :func:`compact()` function's documentation contains an example of how I
    like to use the :func:`compact()` and :func:`dedent()` functions. The main
    difference is that I use :func:`compact()` for text that will be presented
    to the user (where whitespace is les significant) and :func:`dedent()` for
    all data file and code generation tasks (where newlines and indentation are
    very significant).
    """
    dedented_text = textwrap.dedent(text)
    trimmed_text = trim_empty_lines(dedented_text)
    return format(trimmed_text, *args, **kw)

def trim_empty_lines(text):
    """
    Trim leading and trailing empty lines from the given text.

    :param text: The text to trim (a string).
    :returns: The trimmed text (a string).
    """
    lines = text.splitlines(True)
    while lines and is_empty_line(lines[0]):
        lines.pop(0)
    while lines and is_empty_line(lines[-1]):
        lines.pop(-1)
    return ''.join(lines)

def is_empty_line(text):
    """
    Check if a text is empty or contains only whitespace.

    :param text: The text to check for "emptiness" (a string).
    :returns: :data:`True` if the text is empty or contains only whitespace,
              :data:`False` otherwise.
    """
    return len(text) == 0 or text.isspace()

def split_paragraphs(text):
    """
    Split a string into paragraphs (one or more lines delimited by an empty line).

    :param text: The text to split into paragraphs (a string).
    :returns: A list of strings.
    """
    paragraphs = []
    for chunk in text.split('\n\n'):
        chunk = trim_empty_lines(chunk)
        if chunk and not chunk.isspace():
            paragraphs.append(chunk)
    return paragraphs

def join_lines(text):
    """
    Remove "hard wrapping" from the paragraphs in a string.

    :param text: The text to reformat (a string).
    :returns: The text without hard wrapping (a string).

    This function works by removing line breaks when the last character before
    a line break and the first character after the line break are both
    non-whitespace characters. This means that common leading indentation will
    break :func:`join_lines()` (in that case you can use :func:`dedent()`
    before calling :func:`join_lines()`).
    """
    return re.sub(r'(\S)\n(\S)', r'\1 \2', text).strip()

def pluralize(count, singular, plural=None):
    """
    Combine a count with the singular or plural form of a word.

    If the plural form of the word is not provided it is obtained by
    concatenating the singular form of the word with the letter "s". Of course
    this will not always be correct, which is why you have the option to
    specify both forms.

    :param count: The count (a number).
    :param singular: The singular form of the word (a string).
    :param plural: The plural form of the word (a string or ``None``).
    :returns: The count and singular/plural word concatenated (a string).
    """
    if not plural:
        plural = singular + 's'
    return '%s %s' % (count, singular if math.floor(float(count)) == 1 else plural)

def split(text):
    """
    Split a comma-separated list of strings.

    :param text: The text to split (a string).
    :returns: A list of zero or more strings.

    **Example:**

    >>> from humanfriendly.text import split
    >>> 'foo,bar, baz,'.split(',')
    ['foo', 'bar', ' baz', '']
    >>> split('foo,bar, baz,')
    ['foo', 'bar', 'baz']
    """
    return [token.strip() for token in text.split(',') if token and not token.isspace()]

def tokenize(text):
    """
    Tokenize a text into numbers and strings.

    :param text: The text to tokenize (a string).
    :returns: A list of strings and/or numbers.

    This function is used to implement robust tokenization of user input in
    functions like :func:`.parse_size()` and :func:`.parse_timespan()`. It
    automatically coerces integer and floating point numbers, ignores
    whitespace and knows how to separate numbers from strings even without
    whitespace. Some examples to make this more concrete:

    >>> from humanfriendly.text import tokenize
    >>> tokenize('42')
    [42]
    >>> tokenize('42MB')
    [42, 'MB']
    >>> tokenize('42.5MB')
    [42.5, 'MB']
    >>> tokenize('42.5 MB')
    [42.5, 'MB']
    """
    tokenized_input = []
    for token in re.split(r'(\d+(?:\.\d+)?)', text):
        token = token.strip()
        if re.match(r'\d+\.\d+', token):
            tokenized_input.append(float(token))
        elif token.isdigit():
            tokenized_input.append(int(token))
        elif token:
            tokenized_input.append(token)
    return tokenized_input
