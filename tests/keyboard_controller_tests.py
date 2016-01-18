# coding: utf-8
import unittest

import contextlib
import locale
import sys
import threading

import pynput.keyboard

from . import notify


class KeyboardControllerTest(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        notify(
            'This test case is non-interactive, so you must not use the '
            'keyboard',
            delay=2)

    def setUp(self):
        self.controller = pynput.keyboard.Controller()

    def decode(self, string):
        """Decodes a string read from ``stdin``.

        :param str string: The string to decode.
        """
        if sys.version_info.major >= 3:
            yield string
        else:
            for encoding in (
                    'utf-8',
                    locale.getpreferredencoding(),
                    sys.stdin.encoding):
                if encoding:
                    try:
                        yield string.decode(encoding)
                    except:
                        pass

    @contextlib.contextmanager
    def capture(self):
        """Captures a string in a code block.

        :returns: a callable which returns the actual data read
        """
        data = []

        #: The thread body that reads a line from stdin and appends it to data
        def reader():
            while reader.running:
                data.append(sys.stdin.readline()[:-1])
        reader.running = True

        # Start the thread
        thread = threading.Thread(target=reader)
        thread.start()

        # Run the code block
        try:
            yield lambda: tuple(self.decode(''.join(data)))

        finally:
            # Send a newline to let sys.stdin.readline return in reader
            reader.running = False
            self.controller.press(pynput.keyboard.Key.enter)
            self.controller.release(pynput.keyboard.Key.enter)
            thread.join()

    def assertInput(self, failure_message, expected):
        """Asserts that a specific text is generated when typing.

        :param str failure_message: The message to display upon failure.

        :param text: The text to type and expect.
        """
        with self.capture() as collect:
            self.controller.type(expected)

        self.assertIn(expected, collect(), failure_message)

    def test_keys(self):
        """Asserts that all keys defined for the base keyboard interface are
        defined for the current platform"""
        from pynput.keyboard._base import Key
        for key in Key:
            self.assertTrue(
                hasattr(pynput.keyboard.Key, key.name),
                '%s is not defined for the current platform' % key.name)

    def test_press_release(self):
        """Asserts that a press followed by a release generates a typed string
        for an ascii character"""
        with self.capture() as collect:
            self.controller.press(pynput.keyboard.Key.space)
            self.controller.release(pynput.keyboard.Key.space)

        self.assertIn(
            ' ',
            collect(),
            'Failed to press and release space')

    def test_touch(self):
        """Asserts that the touch shortcut behaves as expected"""
        with self.capture() as collect:
            self.controller.touch(pynput.keyboard.Key.space, True)
            self.controller.touch(pynput.keyboard.Key.space, False)

        self.assertIn(
            ' ',
            collect(),
            'Failed to press and release space')

    def test_touch_dead(self):
        """Asserts that pressing dead keys generate combined characters"""
        with self.capture() as collect:
            dead = pynput.keyboard.KeyCode.from_dead('~')
            self.controller.press(dead)
            self.controller.release(dead)
            self.controller.press('a')
            self.controller.release('a')

        self.assertIn(
            u'ã',
            collect(),
            'Failed to apply dead key')

    def test_touch_dead_space(self):
        """Asserts that pressing dead keys followed by space yields the
        non-dead version"""
        with self.capture() as collect:
            dead = pynput.keyboard.KeyCode.from_dead('~')
            self.controller.press(dead)
            self.controller.release(dead)
            self.controller.press(pynput.keyboard.Key.space)
            self.controller.release(pynput.keyboard.Key.space)

        self.assertIn(
            u'~',
            collect(),
            'Failed to apply dead key')

    def test_touch_dead_twice(self):
        """Asserts that pressing dead keys twice yields the non-dead version"""
        with self.capture() as collect:
            dead = pynput.keyboard.KeyCode.from_dead('~')
            self.controller.press(dead)
            self.controller.release(dead)
            self.controller.press(dead)
            self.controller.release(dead)

        self.assertIn(
            u'~',
            collect(),
            'Failed to apply dead key')

    def test_alt_pressed(self):
        """Asserts that alt_pressed works"""
        # We do not test alt_r, since that does not necessarily exist on the
        # keyboard
        for key in (
                pynput.keyboard.Key.alt,
                pynput.keyboard.Key.alt_l):
            self.controller.press(key)
            self.assertTrue(
                self.controller.alt_pressed,
                'alt_pressed was not set with %s down' % key.name)
            self.controller.release(key)
            self.assertFalse(
                self.controller.alt_pressed,
                'alt_pressed was incorrectly set')

    def test_ctrl_pressed(self):
        """Asserts that ctrl_pressed works"""
        for key in (
                pynput.keyboard.Key.ctrl,
                pynput.keyboard.Key.ctrl_l,
                pynput.keyboard.Key.ctrl_r):
            self.controller.press(key)
            self.assertTrue(
                self.controller.ctrl_pressed,
                'ctrl_pressed was not set with %s down' % key.name)
            self.controller.release(key)
            self.assertFalse(
                self.controller.ctrl_pressed,
                'ctrl_pressed was incorrectly set')

    def test_shift_pressed(self):
        """Asserts that shift_pressed works with normal presses"""
        for key in (
                pynput.keyboard.Key.shift,
                pynput.keyboard.Key.shift_l,
                pynput.keyboard.Key.shift_r):
            self.controller.press(key)
            self.assertTrue(
                self.controller.shift_pressed,
                'shift_pressed was not set with %s down' % key.name)
            self.controller.release(key)
            self.assertFalse(
                self.controller.shift_pressed,
                'shift_pressed was incorrectly set')

    def test_shift_pressed_caps_lock(self):
        """Asserts that shift_pressed is True when caps lock is toggled"""
        self.controller.press(pynput.keyboard.Key.caps_lock)
        self.controller.release(pynput.keyboard.Key.caps_lock)
        self.assertTrue(
            self.controller.shift_pressed,
            'shift_pressed was not set with caps lock toggled')

        self.controller.press(pynput.keyboard.Key.caps_lock)
        self.controller.release(pynput.keyboard.Key.caps_lock)
        self.assertFalse(
            self.controller.shift_pressed,
            'shift_pressed was not deactivated with caps lock toggled')

    def test_pressed_shift(self):
        """Asserts that pressing and releasing a Latin character while pressing
        shift causes it to shift to upper case"""
        with self.capture() as collect:
            with self.controller.pressed(pynput.keyboard.Key.shift):
                self.controller.press('a')
                self.controller.release('a')

                with self.controller.modifiers as modifiers:
                    self.assertIn(
                        pynput.keyboard.Key.shift,
                        modifiers)

        self.assertIn(
            'A',
            collect(),
            'shift+a did not yield "A"')

    def test_type_latin(self):
        """Asserts that type works for a Latin string"""
        self.assertInput(
            'Failed to type latin string',
            u'Hello World')

    def test_type_ascii(self):
        """Asserts that type works for an ascii string"""
        self.assertInput(
            'Failed to type ascii string',
            u'abc123, "quoted!"')

    def test_type_nonascii(self):
        """Asserts that type works for a non-ascii strings"""
        self.assertInput(
            'Failed to type Spanish string',
            u'Teclado (informática)')
        self.assertInput(
            'Failed to type Russian string',
            u'Компьютерная клавиатура')
