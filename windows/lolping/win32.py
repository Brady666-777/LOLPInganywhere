"""Win32 low-level input hooks; no injection, key logging, or game integration."""
import ctypes as C
from ctypes import wintypes as W
from PySide6.QtCore import QObject, Signal

user32 = C.WinDLL('user32', use_last_error=True)
kernel32 = C.WinDLL('kernel32', use_last_error=True)
LRESULT = C.c_ssize_t
HOOKPROC = C.WINFUNCTYPE(LRESULT, C.c_int, W.WPARAM, W.LPARAM)


class KBD(C.Structure):
    _fields_ = [('vk', W.DWORD), ('scan', W.DWORD), ('flags', W.DWORD),
                ('time', W.DWORD), ('extra', C.c_size_t)]


class MOUSE(C.Structure):
    _fields_ = [('pt', W.POINT), ('data', W.DWORD), ('flags', W.DWORD),
                ('time', W.DWORD), ('extra', C.c_size_t)]


class MONITOR(C.Structure):
    _fields_ = [('size', W.DWORD), ('rect', W.RECT), ('work', W.RECT),
                ('flags', W.DWORD), ('device', W.WCHAR * 32)]


user32.SetWindowsHookExW.argtypes = [C.c_int, HOOKPROC, W.HINSTANCE, W.DWORD]
user32.SetWindowsHookExW.restype = W.HANDLE
user32.CallNextHookEx.argtypes = [W.HANDLE, C.c_int, W.WPARAM, W.LPARAM]
user32.CallNextHookEx.restype = LRESULT
user32.UnhookWindowsHookEx.argtypes = [W.HANDLE]
user32.UnhookWindowsHookEx.restype = W.BOOL
user32.GetAsyncKeyState.argtypes = [C.c_int]
user32.GetAsyncKeyState.restype = C.c_short
user32.GetCursorPos.argtypes = [C.POINTER(W.POINT)]
user32.GetCursorPos.restype = W.BOOL
user32.GetForegroundWindow.restype = W.HWND
user32.MonitorFromPoint.argtypes = [W.POINT, W.DWORD]
user32.MonitorFromPoint.restype = W.HANDLE
user32.GetMonitorInfoW.argtypes = [W.HANDLE, C.POINTER(MONITOR)]
user32.GetMonitorInfoW.restype = W.BOOL
kernel32.GetModuleHandleW.argtypes = [W.LPCWSTR]
kernel32.GetModuleHandleW.restype = W.HMODULE
kernel32.CreateMutexW.argtypes = [C.c_void_p, W.BOOL, W.LPCWSTR]
kernel32.CreateMutexW.restype = W.HANDLE
kernel32.CloseHandle.argtypes = [W.HANDLE]
kernel32.CloseHandle.restype = W.BOOL

TRIGGER_ALT = {0xA4, 0xA5}   # Left Alt, Right Alt
TRIGGER_G = {0x47}             # G key


def singleton():
    handle = kernel32.CreateMutexW(None, False, 'Local\\LoLPing-Windows-Desktop')
    if not handle:
        raise C.WinError(C.get_last_error())
    if C.get_last_error() == 183:
        kernel32.CloseHandle(handle)
        return None
    return handle


def foreground():
    return user32.GetForegroundWindow()


def monitor(point):
    h = user32.MonitorFromPoint(W.POINT(*point), 2)
    info = MONITOR()
    info.size = C.sizeof(info)
    if not user32.GetMonitorInfoW(h, C.byref(info)):
        raise C.WinError(C.get_last_error())
    return info.device, (info.rect.left, info.rect.top, info.rect.right, info.rect.bottom)


def cursor():
    pt = W.POINT()
    if not user32.GetCursorPos(C.byref(pt)):
        return (0, 0)
    return pt.x, pt.y


class Input(QObject):
    event = Signal(str, object)
    failed = Signal(str)

    def __init__(self):
        super().__init__()
        self.keyboard_hook = self.mouse_hook = None
        self.active = False
        self.trigger = 'alt'          # set by controller
        self.trigger_held = False
        self.rmb_swallowed = False
        self.esc_swallowed = False
        self.keyboard_proc = HOOKPROC(self._keyboard)
        self.mouse_proc = HOOKPROC(self._mouse)

    def modifiers(self):
        return 0

    def start(self):
        self.stop()
        module = kernel32.GetModuleHandleW(None)
        self.keyboard_hook = user32.SetWindowsHookExW(13, self.keyboard_proc, module, 0)
        if not self.keyboard_hook:
            raise C.WinError(C.get_last_error())
        self.mouse_hook = user32.SetWindowsHookExW(14, self.mouse_proc, module, 0)
        if not self.mouse_hook:
            error = C.WinError(C.get_last_error())
            self.stop()
            raise error

    def stop(self):
        self.active = False
        self.trigger_held = False
        self.rmb_swallowed = False
        self.esc_swallowed = False
        for handle in (self.keyboard_hook, self.mouse_hook):
            if handle:
                user32.UnhookWindowsHookEx(handle)
        self.keyboard_hook = self.mouse_hook = None

    def _trigger_vks(self):
        return TRIGGER_ALT if self.trigger == 'alt' else TRIGGER_G

    def _keyboard(self, code, message, data):
        if code >= 0:
            try:
                event = C.cast(data, C.POINTER(KBD)).contents
                if not event.flags & 0x10:
                    key = event.vk
                    down = message in (0x100, 0x104)
                    if key in self._trigger_vks():
                        if down and not self.trigger_held:
                            self.trigger_held = True
                            self.event.emit('trigger_down', cursor())
                        elif not down and self.trigger_held:
                            self.trigger_held = False
                            self.event.emit('trigger_up', None)
                    elif key == 0x1B and down:
                        if self.active:
                            self.esc_swallowed = True
                        self.event.emit('cancel', None)
                        if self.esc_swallowed:
                            return 1
                    elif key == 0x1B and not down and self.esc_swallowed:
                        self.esc_swallowed = False
                        return 1
            except Exception as error:
                self.failed.emit(str(error))
        return user32.CallNextHookEx(None, code, message, data)

    def _mouse(self, code, message, data):
        if code >= 0:
            try:
                event = C.cast(data, C.POINTER(MOUSE)).contents
                if not event.flags & 1:
                    pt = (event.pt.x, event.pt.y)
                    if message == 0x200:
                        self.event.emit('move', pt)
                    elif message == 0x204:  # RMB down — open wheel
                        if self.trigger_held:
                            self.rmb_swallowed = True
                            self.event.emit('lmb_down', pt)
                            return 1
                    elif message == 0x205:  # RMB up — commit
                        if self.rmb_swallowed:
                            self.rmb_swallowed = False
                            self.event.emit('lmb_up', None)
                            return 1
                    elif message == 0x201:  # LMB down — cancel if wheel open
                        if self.active:
                            self.event.emit('cancel', None)
                    elif message in (0x20A, 0x20E):  # scroll — cancel
                        if self.active:
                            self.event.emit('cancel', None)
            except Exception as error:
                self.failed.emit(str(error))
        return user32.CallNextHookEx(None, code, message, data)
