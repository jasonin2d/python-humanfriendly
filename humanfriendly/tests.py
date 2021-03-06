#!/usr/bin/env python

# Tests for the 'humanfriendly' module.
#
# Author: Peter Odding <peter.odding@paylogic.eu>
# Last Change: July 19, 2015
# URL: https://humanfriendly.readthedocs.org

# Standard library modules.
import math
import os
import random
import sys
import time
import unittest

# Modules included in our package.
import humanfriendly
import humanfriendly.cli
from humanfriendly import compact, dedent
from humanfriendly.tables import (
    format_pretty_table,
    format_robust_table,
    format_smart_table,
)
from humanfriendly.terminal import (
    ANSI_CSI,
    ANSI_RESET,
    ANSI_SGR,
    ansi_strip,
    ansi_style,
    ansi_width,
    ansi_wrap,
    connected_to_terminal,
    find_terminal_size,
)
from humanfriendly.usage import (
    find_meta_variables,
    format_usage,
    import_module,
    render_usage,
)

try:
    # Python 2.x.
    from StringIO import StringIO
except ImportError:
    # Python 3.x.
    from io import StringIO


class HumanFriendlyTestCase(unittest.TestCase):

    def test_compact(self):
        assert compact(' a \n\n b ') == 'a b'
        assert compact('''
            %s template notation
        ''', 'Simple') == 'Simple template notation'
        assert compact('''
            More {type} template notation
        ''', type='readable') == 'More readable template notation'

    def test_dedent(self):
        assert dedent('\n line 1\n  line 2\n\n') == 'line 1\n line 2\n'
        assert dedent('''
            Dedented, %s text
        ''', 'interpolated') == 'Dedented, interpolated text\n'
        assert dedent('''
            Dedented, {op} text
        ''', op='formatted') == 'Dedented, formatted text\n'

    def test_pluralization(self):
        self.assertEqual('1 word', humanfriendly.pluralize(1, 'word'))
        self.assertEqual('2 words', humanfriendly.pluralize(2, 'word'))
        self.assertEqual('1 box', humanfriendly.pluralize(1, 'box', 'boxes'))
        self.assertEqual('2 boxes', humanfriendly.pluralize(2, 'box', 'boxes'))

    def test_boolean_coercion(self):
        for value in [True, 'TRUE', 'True', 'true', 'on', 'yes', '1']:
            self.assertEqual(True, humanfriendly.coerce_boolean(value))
        for value in [False, 'FALSE', 'False', 'false', 'off', 'no', '0']:
            self.assertEqual(False, humanfriendly.coerce_boolean(value))
        self.assertRaises(ValueError, humanfriendly.coerce_boolean, 'not a boolean')

    def test_format_timespan(self):
        minute = 60
        hour = minute * 60
        day = hour * 24
        week = day * 7
        year = week * 52
        self.assertEqual('0 seconds', humanfriendly.format_timespan(0))
        self.assertEqual('0.54 seconds', humanfriendly.format_timespan(0.54321))
        self.assertEqual('1 second', humanfriendly.format_timespan(1))
        self.assertEqual('3.14 seconds', humanfriendly.format_timespan(math.pi))
        self.assertEqual('1 minute', humanfriendly.format_timespan(minute))
        self.assertEqual('1 minute and 20 seconds', humanfriendly.format_timespan(80))
        self.assertEqual('2 minutes', humanfriendly.format_timespan(minute * 2))
        self.assertEqual('1 hour', humanfriendly.format_timespan(hour))
        self.assertEqual('2 hours', humanfriendly.format_timespan(hour * 2))
        self.assertEqual('1 day', humanfriendly.format_timespan(day))
        self.assertEqual('2 days', humanfriendly.format_timespan(day * 2))
        self.assertEqual('1 week', humanfriendly.format_timespan(week))
        self.assertEqual('2 weeks', humanfriendly.format_timespan(week * 2))
        self.assertEqual('1 year', humanfriendly.format_timespan(year))
        self.assertEqual('2 years', humanfriendly.format_timespan(year * 2))
        self.assertEqual('1 year, 2 weeks and 3 days', humanfriendly.format_timespan(year + week * 2 + day * 3 + hour * 12))

    def test_parse_timespan(self):
        self.assertEqual(0, humanfriendly.parse_timespan('0'))
        self.assertEqual(0, humanfriendly.parse_timespan('0s'))
        self.assertEqual(5, humanfriendly.parse_timespan('5s'))
        self.assertEqual(60*2, humanfriendly.parse_timespan('2m'))
        self.assertEqual(60*60*3, humanfriendly.parse_timespan('3 h'))
        self.assertEqual(60*60*24*4, humanfriendly.parse_timespan('4d'))
        self.assertEqual(60*60*24*7*5, humanfriendly.parse_timespan('5 w'))
        self.assertRaises(humanfriendly.InvalidTimespan, humanfriendly.parse_timespan, '1z')

    def test_parse_date(self):
        self.assertEqual((2013, 6, 17, 0, 0, 0), humanfriendly.parse_date('2013-06-17'))
        self.assertEqual((2013, 6, 17, 2, 47, 42), humanfriendly.parse_date('2013-06-17 02:47:42'))
        self.assertRaises(humanfriendly.InvalidDate, humanfriendly.parse_date, '2013-06-XY')

    def test_format_size(self):
        self.assertEqual('0 bytes', humanfriendly.format_size(0))
        self.assertEqual('1 byte', humanfriendly.format_size(1))
        self.assertEqual('42 bytes', humanfriendly.format_size(42))
        self.assertEqual('1 KB', humanfriendly.format_size(1024 ** 1))
        self.assertEqual('1 MB', humanfriendly.format_size(1024 ** 2))
        self.assertEqual('1 GB', humanfriendly.format_size(1024 ** 3))
        self.assertEqual('1 TB', humanfriendly.format_size(1024 ** 4))
        self.assertEqual('1 PB', humanfriendly.format_size(1024 ** 5))

    def test_parse_size(self):
        self.assertEqual(0, humanfriendly.parse_size('0B'))
        self.assertEqual(42, humanfriendly.parse_size('42'))
        self.assertEqual(42, humanfriendly.parse_size('42B'))
        self.assertEqual(1024, humanfriendly.parse_size('1k'))
        self.assertEqual(1024, humanfriendly.parse_size('1 KB'))
        self.assertEqual(1024, humanfriendly.parse_size('1 kilobyte'))
        self.assertEqual(1024 ** 3, humanfriendly.parse_size('1 GB'))
        self.assertEqual(1024 ** 3 * 1.5, humanfriendly.parse_size('1.5 GB'))
        self.assertRaises(humanfriendly.InvalidSize, humanfriendly.parse_size, '1z')
        self.assertRaises(humanfriendly.InvalidSize, humanfriendly.parse_size, 'a')

    def test_format_length(self):
        self.assertEqual('0 metres', humanfriendly.format_length(0))
        self.assertEqual('1 metre', humanfriendly.format_length(1))
        self.assertEqual('42 metres', humanfriendly.format_length(42))
        self.assertEqual('1 km', humanfriendly.format_length(1 * 1000))
        self.assertEqual('15.3 cm', humanfriendly.format_length(0.153))
        self.assertEqual('1 cm', humanfriendly.format_length(1e-02))
        self.assertEqual('1 mm', humanfriendly.format_length(1e-03))
        self.assertEqual('1 nm', humanfriendly.format_length(1e-09))

    def test_parse_length(self):
        self.assertEqual(0, humanfriendly.parse_length('0m'))
        self.assertEqual(42, humanfriendly.parse_length('42'))
        self.assertEqual(42, humanfriendly.parse_length('42m'))
        self.assertEqual(1000, humanfriendly.parse_length('1km'))
        self.assertEqual(0.153, humanfriendly.parse_length('15.3 cm'))
        self.assertEqual(1e-02, humanfriendly.parse_length('1cm'))
        self.assertEqual(1e-03, humanfriendly.parse_length('1mm'))
        self.assertEqual(1e-09, humanfriendly.parse_length('1nm'))
        self.assertRaises(humanfriendly.InvalidLength, humanfriendly.parse_length, '1z')
        self.assertRaises(humanfriendly.InvalidLength, humanfriendly.parse_length, 'a')

    def test_format_number(self):
        self.assertEqual('1', humanfriendly.format_number(1))
        self.assertEqual('1.5', humanfriendly.format_number(1.5))
        self.assertEqual('1.56', humanfriendly.format_number(1.56789))
        self.assertEqual('1.567', humanfriendly.format_number(1.56789, 3))
        self.assertEqual('1,000', humanfriendly.format_number(1000))
        self.assertEqual('1,000', humanfriendly.format_number(1000.12, 0))
        self.assertEqual('1,000,000', humanfriendly.format_number(1000000))
        self.assertEqual('1,000,000.42', humanfriendly.format_number(1000000.42))

    def test_round_number(self):
        self.assertEqual('1', humanfriendly.round_number(1))
        self.assertEqual('1', humanfriendly.round_number(1.0))
        self.assertEqual('1.00', humanfriendly.round_number(1, keep_width=True))
        self.assertEqual('3.14', humanfriendly.round_number(3.141592653589793))

    def test_format_path(self):
        friendly_path = os.path.join('~', '.vimrc')
        absolute_path = os.path.join(os.environ['HOME'], '.vimrc')
        self.assertEqual(friendly_path, humanfriendly.format_path(absolute_path))

    def test_parse_path(self):
        friendly_path = os.path.join('~', '.vimrc')
        absolute_path = os.path.join(os.environ['HOME'], '.vimrc')
        self.assertEqual(absolute_path, humanfriendly.parse_path(friendly_path))

    def test_pretty_tables(self):
        # The simplest case possible :-).
        data = [['Just one column']]
        assert format_pretty_table(data) == dedent("""
            -------------------
            | Just one column |
            -------------------
        """).strip()
        # A bit more complex: two rows, three columns, varying widths.
        data = [['One', 'Two', 'Three'], ['1', '2', '3']]
        assert format_pretty_table(data) == dedent("""
            ---------------------
            | One | Two | Three |
            | 1   | 2   | 3     |
            ---------------------
        """).strip()
        # A table including column names.
        column_names = ['One', 'Two', 'Three']
        data = [['1', '2', '3'], ['a', 'b', 'c']]
        assert ansi_strip(format_pretty_table(data, column_names)) == dedent("""
            ---------------------
            | One | Two | Three |
            ---------------------
            | 1   | 2   | 3     |
            | a   | b   | c     |
            ---------------------
        """).strip()
        # A table that contains a column with only numeric data (will be right aligned).
        column_names = ['Just a label', 'Important numbers']
        data = [['Row one', '15'], ['Row two', '300']]
        assert ansi_strip(format_pretty_table(data, column_names)) == dedent("""
            ------------------------------------
            | Just a label | Important numbers |
            ------------------------------------
            | Row one      |                15 |
            | Row two      |               300 |
            ------------------------------------
        """).strip()

    def test_robust_tables(self):
        column_names = ['One', 'Two', 'Three']
        data = [['1', '2', '3'], ['a', 'b', 'c']]
        assert ansi_strip(format_robust_table(data, column_names)) == dedent("""
            --------
            One: 1
            Two: 2
            Three: 3
            --------
            One: a
            Two: b
            Three: c
            --------
        """).strip()
        column_names = ['One', 'Two', 'Three']
        data = [['1', '2', '3'], ['a', 'b', 'Here comes a\nmulti line column!']]
        assert ansi_strip(format_robust_table(data, column_names)) == dedent("""
            ------------------
            One: 1
            Two: 2
            Three: 3
            ------------------
            One: a
            Two: b
            Three:
            Here comes a
            multi line column!
            ------------------
        """).strip()

    def test_smart_tables(self):
        column_names = ['One', 'Two', 'Three']
        data = [['1', '2', '3'], ['a', 'b', 'c']]
        assert ansi_strip(format_smart_table(data, column_names)) == dedent("""
            ---------------------
            | One | Two | Three |
            ---------------------
            | 1   | 2   | 3     |
            | a   | b   | c     |
            ---------------------
        """).strip()
        column_names = ['One', 'Two', 'Three']
        data = [['1', '2', '3'], ['a', 'b', 'Here comes a\nmulti line column!']]
        assert ansi_strip(format_smart_table(data, column_names)) == dedent("""
            ------------------
            One: 1
            Two: 2
            Three: 3
            ------------------
            One: a
            Two: b
            Three:
            Here comes a
            multi line column!
            ------------------
        """).strip()

    def test_concatenate(self):
        self.assertEqual(humanfriendly.concatenate([]), '')
        self.assertEqual(humanfriendly.concatenate(['one']), 'one')
        self.assertEqual(humanfriendly.concatenate(['one', 'two']), 'one and two')
        self.assertEqual(humanfriendly.concatenate(['one', 'two', 'three']), 'one, two and three')

    def test_split(self):
        from humanfriendly.text import split
        self.assertEqual(split(''), [])
        self.assertEqual(split('foo'), ['foo'])
        self.assertEqual(split('foo, bar'), ['foo', 'bar'])
        self.assertEqual(split('foo, bar, baz'), ['foo', 'bar', 'baz'])
        self.assertEqual(split('foo,bar,baz'), ['foo', 'bar', 'baz'])

    def test_timer(self):
        for seconds, text in ((1, '1 second'),
                              (2, '2 seconds'),
                              (60, '1 minute'),
                              (60*2, '2 minutes'),
                              (60*60, '1 hour'),
                              (60*60*2, '2 hours'),
                              (60*60*24, '1 day'),
                              (60*60*24*2, '2 days'),
                              (60*60*24*7, '1 week'),
                              (60*60*24*7*2, '2 weeks')):
            t = humanfriendly.Timer(time.time() - seconds)
            self.assertEqual(humanfriendly.round_number(t.elapsed_time, keep_width=True), '%i.00' % seconds)
            self.assertEqual(str(t), text)
        # Test rounding to seconds.
        t = humanfriendly.Timer(time.time() - 2.2)
        self.assertEqual(t.rounded, '2 seconds')
        # Test automatic timer.
        automatic_timer = humanfriendly.Timer()
        time.sleep(1)
        self.assertEqual(normalize_timestamp(humanfriendly.round_number(automatic_timer.elapsed_time, keep_width=True)), '1.00')
        # Test resumable timer.
        resumable_timer = humanfriendly.Timer(resumable=True)
        for i in range(2):
            with resumable_timer:
                time.sleep(1)
        self.assertEqual(normalize_timestamp(humanfriendly.round_number(resumable_timer.elapsed_time, keep_width=True)), '2.00')

    def test_spinner(self):
        stream = StringIO()
        spinner = humanfriendly.Spinner('test spinner', total=4, stream=stream, interactive=True)
        for progress in [1, 2, 3, 4]:
            spinner.step(progress=progress)
            time.sleep(0.2)
        spinner.clear()
        output = stream.getvalue()
        output = (output.replace(humanfriendly.show_cursor_code, '')
                        .replace(humanfriendly.hide_cursor_code, ''))
        lines = [line for line in output.split(humanfriendly.erase_line_code) if line]
        self.assertTrue(len(lines) > 0)
        self.assertTrue(all('test spinner' in l for l in lines))
        self.assertTrue(all('%' in l for l in lines))
        self.assertEqual(sorted(set(lines)), sorted(lines))

    def test_automatic_spinner(self):
        # There's not a lot to test about the AutomaticSpinner class, but by at
        # least running it here we are assured that the code functions on all
        # supported Python versions. AutomaticSpinner is built on top of the
        # Spinner class so at least we also have the tests for the Spinner
        # class to back us up.
        with humanfriendly.AutomaticSpinner('test spinner'):
            time.sleep(1)

    def test_prompt_for_choice(self):
        interactive_prompt = humanfriendly.interactive_prompt
        try:
            # Choice selection by full string match.
            humanfriendly.interactive_prompt = lambda prompt: 'foo'
            self.assertEqual(humanfriendly.prompt_for_choice(['foo', 'bar']), 'foo')
            # Choice selection by substring input.
            humanfriendly.interactive_prompt = lambda prompt: 'f'
            self.assertEqual(humanfriendly.prompt_for_choice(['foo', 'bar']), 'foo')
            # Choice selection by number.
            humanfriendly.interactive_prompt = lambda prompt: '2'
            self.assertEqual(humanfriendly.prompt_for_choice(['foo', 'bar']), 'bar')
            # Choice selection by going with the default.
            humanfriendly.interactive_prompt = lambda prompt: ''
            self.assertEqual(humanfriendly.prompt_for_choice(['foo', 'bar'], default='bar'), 'bar')
            # Invalid substrings are refused.
            responses = ['', 'q', 'z']
            humanfriendly.interactive_prompt = lambda prompt: responses.pop(0)
            self.assertEqual(humanfriendly.prompt_for_choice(['foo', 'bar', 'baz']), 'baz')
            # Choice selection by substring input requires an unambiguous substring match.
            responses = ['a', 'q']
            humanfriendly.interactive_prompt = lambda prompt: responses.pop(0)
            self.assertEqual(humanfriendly.prompt_for_choice(['foo', 'bar', 'baz', 'qux']), 'qux')
            # Invalid numbers are refused.
            responses = ['42', '2']
            humanfriendly.interactive_prompt = lambda prompt: responses.pop(0)
            self.assertEqual(humanfriendly.prompt_for_choice(['foo', 'bar', 'baz']), 'bar')
        finally:
            humanfriendly.interactive_prompt = interactive_prompt

    def test_cli(self):
        # Test that the usage message is printed by default.
        returncode, output = main()
        assert 'Usage:' in output
        # Test that the usage message can be requested explicitly.
        returncode, output = main('--help')
        assert 'Usage:' in output
        # Test handling of invalid command line options.
        returncode, output = main('--unsupported-option')
        assert returncode != 0
        # Test `humanfriendly --format-number'.
        returncode, output = main('--format-number=1234567')
        assert output.strip() == '1,234,567'
        # Test `humanfriendly --format-size'.
        random_byte_count = random.randint(1024, 1024*1024)
        returncode, output = main('--format-size=%i' % random_byte_count)
        assert output.strip() == humanfriendly.format_size(random_byte_count)
        # Test `humanfriendly --format-table'.
        returncode, output = main('--format-table', '--delimiter=\t', input='1\t2\t3\n4\t5\t6\n7\t8\t9')
        assert output.strip() == dedent('''
            -------------
            | 1 | 2 | 3 |
            | 4 | 5 | 6 |
            | 7 | 8 | 9 |
            -------------
        ''').strip()
        # Test `humanfriendly --format-timespan'.
        random_timespan = random.randint(5, 600)
        returncode, output = main('--format-timespan=%i' % random_timespan)
        assert output.strip() == humanfriendly.format_timespan(random_timespan)
        # Test `humanfriendly --parse-size'.
        returncode, output = main('--parse-size=5 KB')
        assert int(output) == humanfriendly.parse_size('5 KB')
        # Test `humanfriendly --run-command'.
        returncode, output = main('--run-command', 'bash', '-c', 'sleep 2 && exit 42')
        assert returncode == 42

    def test_ansi_style(self):
        assert ansi_style(bold=True) == '%s1%s' % (ANSI_CSI, ANSI_SGR)
        assert ansi_style(faint=True) == '%s2%s' % (ANSI_CSI, ANSI_SGR)
        assert ansi_style(underline=True) == '%s4%s' % (ANSI_CSI, ANSI_SGR)
        assert ansi_style(inverse=True) == '%s7%s' % (ANSI_CSI, ANSI_SGR)
        assert ansi_style(strike_through=True) == '%s9%s' % (ANSI_CSI, ANSI_SGR)
        assert ansi_style(color='blue') == '%s34%s' % (ANSI_CSI, ANSI_SGR)
        self.assertRaises(ValueError, ansi_style, color='unknown')

    def test_ansi_width(self):
        text = "Whatever"
        # Make sure ansi_width() works as expected on strings without ANSI escape sequences.
        assert len(text) == ansi_width(text)
        # Wrap a text in ANSI escape sequences and make sure ansi_width() treats it as expected.
        wrapped = ansi_wrap(text, bold=True)
        # Make sure ansi_wrap() changed the text.
        assert wrapped != text
        # Make sure ansi_wrap() added additional bytes.
        assert len(wrapped) > len(text)
        # Make sure the result of ansi_width() stays the same.
        assert len(text) == ansi_width(wrapped)

    def test_ansi_wrap(self):
        text = "Whatever"
        # Make sure ansi_wrap() does nothing when no keyword arguments are given.
        assert text == ansi_wrap(text)
        # Make sure ansi_wrap() starts the text with the CSI sequence.
        assert ansi_wrap(text, bold=True).startswith(ANSI_CSI)
        # Make sure ansi_wrap() ends the text by resetting the ANSI styles.
        assert ansi_wrap(text, bold=True).endswith(ANSI_RESET)

    def test_find_terminal_size(self):
        lines, columns = find_terminal_size()
        # We really can't assert any minimum or maximum values here because it
        # simply doesn't make any sense; it's impossible for me to anticipate
        # on what environments this test suite will run in the future.
        assert lines > 0
        assert columns > 0
        # The find_terminal_size_using_ioctl() function is the default
        # implementation and it will likely work fine. This makes it hard to
        # test the fall back code paths though. However there's an easy way to
        # make find_terminal_size_using_ioctl() fail ...
        saved_stdin = sys.stdin
        saved_stdout = sys.stdout
        saved_stderr = sys.stderr
        try:
            # What do you mean this is brute force?! ;-)
            sys.stdin = StringIO()
            sys.stdout = StringIO()
            sys.stderr = StringIO()
            # Now find_terminal_size_using_ioctl() should fail even though
            # find_terminal_size_using_stty() might work fine.
            lines, columns = find_terminal_size()
            assert lines > 0
            assert columns > 0
            # There's also an ugly way to make `stty size' fail: The
            # subprocess.Popen class uses os.execvp() underneath, so if we
            # clear the $PATH it will break.
            saved_path = os.environ['PATH']
            try:
                os.environ['PATH'] = ''
                # Now find_terminal_size_using_stty() should fail.
                lines, columns = find_terminal_size()
                assert lines > 0
                assert columns > 0
            finally:
                os.environ['PATH'] = saved_path
        finally:
            sys.stdin = saved_stdin
            sys.stdout = saved_stdout
            sys.stderr = saved_stderr

    def test_connected_to_terminal(self):
        for stream in [sys.stdin, sys.stdout, sys.stderr]:
            result = connected_to_terminal(stream)
            # We really can't assert a True or False value here because this
            # test suite should be able to run both interactively and
            # non-interactively :-).
            assert isinstance(result, bool)
        # We can at least verify that e.g. /dev/null is never a terminal :-).
        with open(os.devnull) as handle:
            assert not connected_to_terminal(handle)
        # We can also verify that objects without isatty() don't raise an exception.
        assert not connected_to_terminal(object())

    def test_find_meta_variables(self):
        assert sorted(find_meta_variables("""
            Here's one example: --format-number=VALUE
            Here's another example: --format-size=BYTES
            A final example: --format-timespan=SECONDS
            This line doesn't contain a META variable.
        """)) == sorted(['VALUE', 'BYTES', 'SECONDS'])

    def test_format_usage(self):
        # Test that options are highlighted.
        usage_text = "Just one --option"
        formatted_text = format_usage(usage_text)
        assert len(formatted_text) > len(usage_text)
        assert formatted_text.startswith("Just one ")
        # Test that the "Usage: ..." line is highlighted.
        usage_text = "Usage: humanfriendly [OPTIONS]"
        formatted_text = format_usage(usage_text)
        assert len(formatted_text) > len(usage_text)
        assert usage_text in formatted_text
        assert not formatted_text.startswith(usage_text)
        # Test that meta variables aren't erroneously highlighted.
        usage_text = (
            "--valid-option=VALID_METAVAR\n"
            "VALID_METAVAR is bogus\n"
            "INVALID_METAVAR should not be highlighted\n"
        )
        formatted_text = format_usage(usage_text)
        formatted_lines = formatted_text.splitlines()
        # Make sure the meta variable in the second line is highlighted.
        assert ANSI_CSI in formatted_lines[1]
        # Make sure the meta variable in the third line isn't highlighted.
        assert ANSI_CSI not in formatted_lines[2]

    def test_render_usage(self):
        assert render_usage("Usage: some-command WITH ARGS") == "**Usage:** `some-command WITH ARGS`"
        assert render_usage("Supported options:") == "**Supported options:**"
        assert 'code-block' in render_usage(dedent("""
            Here comes a shell command:

              $ echo test
              test
        """))
        assert all(token in render_usage("""
            Supported options:

              -n, --dry-run

                Don't change anything.
        """) for token in ('`-n`', '`--dry-run`'))

    def test_import_module(self):
        import humanfriendly
        assert humanfriendly is import_module('humanfriendly')
        from humanfriendly import cli
        assert cli is import_module('humanfriendly.cli')


def main(*args, **kw):
    returncode = 0
    input_buffer = StringIO(kw.get('input', ''))
    output_buffer = StringIO()
    saved_argv = sys.argv
    saved_stdin = sys.stdin
    saved_stdout = sys.stdout
    try:
        sys.argv = [sys.argv[0]] + list(args)
        sys.stdin = input_buffer
        sys.stdout = output_buffer
        humanfriendly.cli.main()
    except SystemExit as e:
        returncode = e.code or 1
    finally:
        sys.argv = saved_argv
        sys.stdin = saved_stdin
        sys.stdout = saved_stdout
    return returncode, output_buffer.getvalue()


def normalize_timestamp(value, ndigits=1):
    return '%.2f' % round(float(value), ndigits=ndigits)


if __name__ == '__main__':
    unittest.main()
