# Human friendly input/output in Python.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: June 27, 2015
# URL: https://humanfriendly.readthedocs.org

"""
The :mod:`~humanfriendly.terminal` module makes it easy to interact with UNIX
terminals and format text for rendering on UNIX terminals. If the terms used in
the documentation of this module don't make sense to you then please refer to
the `Wikipedia article on ANSI escape sequences`_ for details about how ANSI
escape sequences work.

.. _Wikipedia article on ANSI escape sequences: http://en.wikipedia.org/wiki/ANSI_escape_code#Sequence_elements
"""

# Standard library modules.
import os
import re
import subprocess
import sys

# The `fcntl' module is platform specific so importing it may give an error. We
# hide this implementation detail from callers by handling the import error and
# setting a flag instead.
try:
    import fcntl
    import termios
    import struct
    HAVE_IOCTL = True
except ImportError:
    HAVE_IOCTL = False

# Modules included in our package. We import find_meta_variables() here to
# preserve backwards compatibility with older versions of humanfriendly where
# that function was defined in this module.
from humanfriendly.usage import find_meta_variables, format_usage  # NOQA

ANSI_CSI = '\x1b['
"""The ANSI "Control Sequence Introducer" (a string)."""

ANSI_SGR = 'm'
"""The ANSI "Select Graphic Rendition" sequence (a string)."""

ANSI_ERASE_LINE = '%sK' % ANSI_CSI
"""The ANSI escape sequence to erase the current line (a string)."""

ANSI_RESET = '%s0%s' % (ANSI_CSI, ANSI_SGR)
"""The ANSI escape sequence to reset styling (a string)."""

ANSI_COLOR_CODES = dict(black=0, red=1, green=2, yellow=3, blue=4, magenta=5, cyan=6, white=7)
"""
A dictionary with (name, number) pairs of `portable color codes`_. Used by
:func:`ansi_style()` to generate ANSI escape sequences that change font color.

.. _portable color codes: http://en.wikipedia.org/wiki/ANSI_escape_code#Colors
"""

DEFAULT_LINES = 25
"""The default number of lines in a terminal (an integer)."""

DEFAULT_COLUMNS = 80
"""The default number of columns in a terminal (an integer)."""

HIGHLIGHT_COLOR = os.environ.get('HUMANFRIENDLY_HIGHLIGHT_COLOR', 'green')
"""
The color used to highlight important tokens in formatted text (e.g. the usage
message of the ``humanfriendly`` program). If the environment variable
``$HUMANFRIENDLY_HIGHLIGHT_COLOR`` is set it determines the value of
:data:`HIGHLIGHT_COLOR`.
"""


def ansi_strip(text):
    """
    Strip ANSI escape sequences from the given string.

    :param text: The text from which ANSI escape sequences should be removed (a
                 string).
    :returns: The text without ANSI escape sequences (a string).
    """
    pattern = '%s.*?%s' % (re.escape(ANSI_CSI), re.escape(ANSI_SGR))
    return re.sub(pattern, '', text)


def ansi_style(color=None, bold=False, faint=False, underline=False, inverse=False, strike_through=False):
    """
    Generate ANSI escape sequences for the given color and/or style(s).

    :param color: The name of a color (one of the strings 'black', 'red',
                  'green', 'yellow', 'blue', 'magenta', 'cyan' or 'white') or
                  :data:`None` (the default) which means no escape sequence to
                  switch color will be emitted.
    :param bold: :data:`True` enables bold font (the default is :data:`False`).
    :param faint: :data:`True` enables faint font (the default is
                  :data:`False`).
    :param underline: :data:`True` enables underline font (the default is
                      :data:`False`).
    :param inverse: :data:`True` enables inverse font (the default is
                    :data:`False`).
    :param strike_through: :data:`True` enables crossed-out / strike-through
                           font (the default is :data:`False`).
    :returns: The ANSI escape sequences to enable the requested text styles or
              an empty string if no styles were requested.
    :raises: :py:exc:`~exceptions.ValueError` when an invalid color name is given.
    """
    sequences = []
    if bold:
        sequences.append('1')
    if faint:
        sequences.append('2')
    if underline:
        sequences.append('4')
    if inverse:
        sequences.append('7')
    if strike_through:
        sequences.append('9')
    if color:
        if color not in ANSI_COLOR_CODES:
            msg = "Invalid color name %r! (expected one of %s)"
            raise ValueError(msg % (color, ", ".join(sorted(ANSI_COLOR_CODES))))
        sequences.append('3%i' % ANSI_COLOR_CODES[color])
    if sequences:
        return ANSI_CSI + ';'.join(sequences) + ANSI_SGR
    else:
        return ''


def ansi_width(text):
    """
    Calculate the effective width of the given text (ignoring ANSI escape sequences).

    :param text: The text whose width should be calculated (a string).
    :returns: The width of the text without ANSI escape sequences (an
              integer).

    This function uses :func:`ansi_strip()` to strip ANSI escape sequences from
    the given string and returns the length of the resulting string.
    """
    return len(ansi_strip(text))


def ansi_wrap(text, **kw):
    """
    Wrap text in ANSI escape sequences for the given color and/or style(s).

    :param text: The text to wrap (a string).
    :param kw: Any keyword arguments are passed to :func:`ansi_style()`.
    :returns: The result of this function depends on the keyword arguments:

              - If :func:`ansi_style()` generates an ANSI escape sequence based
                on the keyword arguments, the given text is prefixed with the
                generated ANSI escape sequence and suffixed with
                :data:`ANSI_RESET`.

              - If :func:`ansi_style()` returns an empty string then the text
                given by the caller is returned unchanged.
    """
    start_sequence = ansi_style(**kw)
    if start_sequence:
        return start_sequence + text + ANSI_RESET
    else:
        return text


def connected_to_terminal(stream=None):
    """
    Check if a stream is connected to a terminal.

    If this function returns :data:`True` on a UNIX system it generally means
    that ANSI escape sequences are supported and can be used.

    :param stream: The stream to check (a :class:`file` object, defaults to
                   :data:`sys.stdout`).
    :returns: :data:`True` if the stream is connected to a terminal,
              :data:`False` otherwise.
    """
    if stream is None:
        stream = sys.stdout
    try:
        return stream.isatty()
    except Exception:
        return False


def find_terminal_size():
    """
    Determine the number of lines and columns visible in the terminal.

    :returns: A tuple of two integers with the line and column count.

    The result of this function is based on the first of the following three
    methods that works:

    1. First :func:`find_terminal_size_using_ioctl()` is tried,
    2. then :func:`find_terminal_size_using_stty()` is tried,
    3. finally :data:`DEFAULT_LINES` and :data:`DEFAULT_COLUMNS` are returned.

    .. note:: The :func:`find_terminal_size()` function performs the steps
              above every time it is called, the result is not cached. This is
              because the size of a virtual terminal can change at any time and
              the result of :func:`find_terminal_size()` should be correct.

              `Pre-emptive snarky comment`_: It's possible to cache the result
              of this function and use :data:`signal.SIGWINCH` to refresh the
              cached values!

              Response: As a library I don't consider it the role of the
              :py:mod:`humanfriendly.terminal` module to install a process wide
              signal handler ...

    .. _Pre-emptive snarky comment: http://blogs.msdn.com/b/oldnewthing/archive/2008/01/30/7315957.aspx
    """
    # The first method. Any of the standard streams may have been redirected
    # somewhere and there's no telling which, so we'll just try them all.
    for stream in sys.stdin, sys.stdout, sys.stderr:
        try:
            result = find_terminal_size_using_ioctl(stream)
            if min(result) >= 1:
                return result
        except Exception:
            pass
    # The second method.
    try:
        result = find_terminal_size_using_stty()
        if min(result) >= 1:
            return result
    except Exception:
        pass
    # Fall back to conservative defaults.
    return DEFAULT_LINES, DEFAULT_COLUMNS


def find_terminal_size_using_ioctl(stream):
    """
    Find the terminal size using :func:`fcntl.ioctl()`.

    :param stream: A stream connected to the terminal (a file object with a
                   ``fileno`` attribute).
    :returns: A tuple of two integers with the line and column count.
    :raises: This function can raise exceptions but I'm not going to document
             them here, you should be using :func:`find_terminal_size()`.

    Based on an `implementation found on StackOverflow <http://stackoverflow.com/a/3010495/788200>`_.
    """
    if not HAVE_IOCTL:
        raise NotImplementedError("It looks like the `fcntl' module is not available!")
    h, w, hp, wp = struct.unpack('HHHH',
        fcntl.ioctl(stream, termios.TIOCGWINSZ,
        struct.pack('HHHH', 0, 0, 0, 0)))
    return h, w


def find_terminal_size_using_stty():
    """
    Find the terminal size using the external command ``stty size``.

    :param stream: A stream connected to the terminal (a file object).
    :returns: A tuple of two integers with the line and column count.
    :raises: This function can raise exceptions but I'm not going to document
             them here, you should be using :func:`find_terminal_size()`.
    """
    stty = subprocess.Popen(['stty', 'size'],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    stdout, stderr = stty.communicate()
    tokens = stdout.split()
    if len(tokens) != 2:
        raise Exception("Invalid output from `stty size'!")
    return tuple(map(int, tokens))


def usage(usage_text):
    """
    Print a human friendly usage message to the terminal.

    :param text: The usage message to print (a string).

    This function does two things:

    1. If :data:`sys.stdout` is connected to a terminal (see
       :func:`connected_to_terminal()`) then the usage message is formatted
       using :func:`.format_usage()`.
    2. The usage message is shown using a pager (see :func:`show_pager()`).
    """
    if connected_to_terminal(sys.stdout):
        usage_text = format_usage(usage_text)
    show_pager(usage_text)


def show_pager(formatted_text):
    """
    Print a large text to the terminal using a pager.

    :param formatted_text: The text to print to the terminal (a string).

    The use of a pager helps to avoid the wall of text effect where the user
    has to scroll up to see where the output began (not very user friendly).

    If :data:`sys.stdout` is not connected to a terminal (see
    :func:`connected_to_terminal()`) then the text is printed directly without
    invoking a pager.

    If the given text contains ANSI escape sequences the command ``less
    --RAW-CONTROL-CHARS`` is used, otherwise ``$PAGER`` is used (if ``$PAGER``
    isn't set the command ``less`` is used).
    """
    if connected_to_terminal(sys.stdout):
        if ANSI_CSI in formatted_text:
            pager_command = ['less', '--RAW-CONTROL-CHARS']
        else:
            pager_command = [os.environ.get('PAGER', 'less')]
        pager = subprocess.Popen(pager_command, stdin=subprocess.PIPE)
        pager.communicate(input=formatted_text)
    else:
        print(formatted_text)
