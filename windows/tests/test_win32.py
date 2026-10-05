"""Native ABI/installation checks run on Windows; no injected input."""
import ctypes
import sys
import unittest


@unittest.skipUnless(sys.platform == 'win32', 'Win32 hooks require Windows')
class NativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_64_bit_struct_layout(self):
        from lolping.win32 import KBD, MOUSE
        self.assertEqual(ctypes.sizeof(ctypes.c_void_p), 8)
        self.assertEqual(ctypes.sizeof(KBD), 24)
        self.assertEqual(ctypes.sizeof(MOUSE), 32)

    def test_hook_install_and_cleanup(self):
        from lolping.win32 import Input
        native = Input()
        try:
            native.start()
            self.assertTrue(native.keyboard_hook)
            self.assertTrue(native.mouse_hook)
        finally:
            native.stop()
        self.assertIsNone(native.keyboard_hook)
        self.assertIsNone(native.mouse_hook)

    def test_monitor_lookup(self):
        from lolping.win32 import cursor, monitor
        name, (left, top, right, bottom) = monitor(cursor())
        self.assertTrue(name)
        self.assertGreater(right, left)
        self.assertGreater(bottom, top)
