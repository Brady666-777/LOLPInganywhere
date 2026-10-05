import os
import sys
from pathlib import Path
from PySide6.QtCore import QObject, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QImage, QPainter
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QGridLayout, QHBoxLayout,
                              QLabel, QMainWindow, QMenu, QMessageBox, QPushButton,
                              QSlider, QSystemTrayIcon, QVBoxLayout, QWidget)
from .audio import Sound
from .core import TRIGGERS, Gesture, PINGS, clamp_center
from .settings import load, save, settings_path
from .visuals import Art, Overlay, Preview, check_assets, resource_root


class Controller(QObject):
    changed = Signal(bool, str)
    actions = Signal(object)

    def __init__(self, app, art, prefs, smoke=False):
        super().__init__()
        self.app = app
        self.prefs = prefs
        self.enabled = False
        self.smoke = smoke
        self.machine = Gesture(TRIGGERS[prefs['trigger']], prefs['scale'] / 100)
        self.wheel = Overlay(art)
        self.effect = Overlay(art)
        self.sound = Sound()
        self.sound.error.connect(lambda msg: self.changed.emit(self.enabled, msg))
        self.preview = None
        self.input = None
        self.epoch = 0
        self.screen = app.primaryScreen()
        self.origin = (0, 0)
        self.ratio = 1
        self.actions.connect(self.apply_actions, Qt.ConnectionType.QueuedConnection)
        self.last_foreground = None
        self.health = QTimer(self)
        self.health.setInterval(100)
        self.health.timeout.connect(self.check_foreground)
        if not smoke:
            from . import win32
            self.native = win32
            self.input = win32.Input()
            # The hook callback only updates the pure state machine and queues UI work.
            self.input.event.connect(self.receive)
            self.input.failed.connect(self.input_failed, Qt.ConnectionType.QueuedConnection)
            self.health.start()
        self.app.screenAdded.connect(self.screen_changed)
        self.app.screenRemoved.connect(self.screen_changed)
        for screen in app.screens():
            self.watch_screen(screen)


    def watch_screen(self, screen):
        screen.geometryChanged.connect(lambda *_: self.cancel_all())
        screen.logicalDotsPerInchChanged.connect(lambda *_: self.cancel_all())

    def screen_changed(self, screen):
        self.cancel_all()
        if screen in self.app.screens():
            self.watch_screen(screen)

    def input_failed(self, message):
        self.enable(False)
        self.changed.emit(False, '全局输入已停止：' + message)

    def persist(self):
        if self.smoke:
            return
        try:
            save(settings_path(), self.prefs)
        except OSError as error:
            self.changed.emit(self.enabled, '设置未能保存：' + str(error))

    def enable(self, value):
        self.cancel_all()
        if self.input:
            self.input.stop()
        self.enabled = False
        self.machine = Gesture(TRIGGERS[self.prefs['trigger']], self.prefs['scale'] / 100)
        message = '全局信号已关闭，仍可在窗口内试用。'
        if value and self.input:
            try:
                self.input.start()
                self.input.trigger = TRIGGERS[self.prefs['trigger']]
                self.enabled = True
                self.last_foreground = self.native.foreground()
                message = '已启用：按住 ' + self.prefs['trigger'] + '，按住右键选择，松开发送。'
            except OSError as error:
                message = '无法安装全局输入监听：' + str(error)
        self.prefs['enabled'] = self.enabled
        self.changed.emit(self.enabled, message)
        self.persist()

    def configure(self, key, value):
        self.prefs[key] = value
        if key in ('trigger', 'scale'):
            self.enable(self.enabled)
        else:
            self.sound.set_volume(value)
            self.persist()
        if self.preview:
            self.preview.scale = self.prefs['scale'] / 100

    def check_foreground(self):
        if not self.input:
            return
        current = self.native.foreground()
        if current != self.last_foreground:
            if self.machine.active:
                self.cancel_all()
            self.last_foreground = current

    def set_anchor_screen(self, point):
        _name, rect = self.native.monitor(point)
        rx, ry, rr, rb = rect
        # Match Qt screen by overlapping physical rect (Win32 uses physical pixels,
        # Qt geometry uses logical pixels scaled by devicePixelRatio).
        best = None
        for s in self.app.screens():
            g = s.geometry()
            r = s.devicePixelRatio()
            # Convert Qt logical rect to physical pixels for comparison.
            px, py = round(g.x() * r), round(g.y() * r)
            pw, ph = round(g.width() * r), round(g.height() * r)
            if px == rx and py == ry and pw == (rr - rx) and ph == (rb - ry):
                best = s
                break
        if best is None:
            # Fallback: pick the screen whose physical origin is closest to the monitor rect origin.
            best = min(self.app.screens(), key=lambda s: (
                (round(s.geometry().x() * s.devicePixelRatio()) - rx) ** 2 +
                (round(s.geometry().y() * s.devicePixelRatio()) - ry) ** 2
            ))
        self.screen = best
        geometry = self.screen.geometry()
        self.ratio = (rr - rx) / geometry.width()
        self.origin = (rx, ry)

    def logical(self, point):
        geometry = self.screen.geometry()
        return (geometry.x() + (point[0] - self.origin[0]) / self.ratio,
                geometry.y() + (point[1] - self.origin[1]) / self.ratio)

    def receive(self, kind, data):
        try:
            self.receive_event(kind, data)
        except Exception as error:
            self.input.active = False
            self.input.failed.emit(str(error))

    def receive_event(self, kind, data):
        if not self.enabled:
            return
        current = self.native.foreground()
        if current != self.last_foreground:
            if self.machine.active:
                self.machine.cancel()
                self.epoch += 1
                self.actions.emit((self.epoch, [('clear',)]))
            self.last_foreground = current
        if kind == 'trigger_down':
            self.dispatch(self.machine.trigger_down(data))
        elif kind == 'trigger_up':
            self.dispatch(self.machine.trigger_up())
        elif kind == 'lmb_down':
            self.set_anchor_screen(data)
            point = self.logical(data)
            self.dispatch(self.machine.lmb_down(point))
        elif kind == 'lmb_up':
            self.dispatch(self.machine.lmb_up())
        elif kind == 'move':
            if self.machine.active:
                self.dispatch(self.machine.moved(self.logical(data)))
        elif kind == 'cancel':
            self.dispatch(self.machine.cancel())
        self.input.active = self.machine.active

    def dispatch(self, actions):
        if actions:
            self.actions.emit((self.epoch, actions))

    def apply_actions(self, payload):
        epoch, actions = payload
        if epoch != self.epoch:
            return
        for action in actions:
            kind = action[0]
            if kind == 'clear':
                self.clear_visuals()
            elif kind == 'show' and self.enabled and self.machine.active:
                rect = self.screen.availableGeometry()
                scale = self.prefs['scale'] / 100
                center = clamp_center(action[1], (rect.x(), rect.y(), rect.width(), rect.height()), 152 * scale)
                self.machine.center = center
                self.wheel.show_wheel(center, scale, self.screen)
            elif kind == 'hover':
                self.wheel.selected = action[1]
                self.wheel.update()
            elif kind == 'hide':
                self.wheel.clear()
            elif kind == 'commit' and self.enabled:
                self.effect.show_ping(action[1], action[2], self.prefs['scale'] / 100, self.screen)
                self.sound.play(action[1], self.prefs['volume'])

    def clear_visuals(self):
        self.wheel.clear()
        self.effect.clear()
        self.sound.stop()
        if self.preview:
            self.preview.clear()

    def cancel_all(self):
        self.epoch += 1
        self.machine.cancel()
        if self.input:
            self.input.active = False
        self.clear_visuals()

    def try_ping(self, index):
        self.preview.play(index)
        self.sound.play(index, self.prefs['volume'])

    def shutdown(self):
        self.health.stop()
        self.cancel_all()
        if self.input:
            self.input.stop()
        self.wheel.close()
        self.effect.close()


class Window(QMainWindow):
    def __init__(self, controller, art, icon):
        super().__init__()
        self.controller = controller
        self.quitting = False
        self.tray = None
        self.setWindowTitle('LoLPing · Windows 桌面信号')
        self.setWindowIcon(icon)
        self.resize(590, 650)
        self.setStyleSheet('''
            QMainWindow, QWidget { background: #101e28; color: #e3edf3; font-size: 14px; }
            QPushButton, QComboBox { background: #203747; border: 1px solid #456172; border-radius: 5px; padding: 9px; }
            QPushButton:hover { background: #315365; }
            QSlider::groove:horizontal { height: 5px; background: #345064; }
            QSlider::handle:horizontal { width: 14px; margin: -5px 0; background: #76cddd; border-radius: 6px; }
        ''')
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(13)
        heading = QLabel('LoLPing  /  桌面信号')
        heading.setStyleSheet('font-size: 25px; font-weight: bold; color: #e5c483;')
        layout.addWidget(heading)
        intro = QLabel('按住 Alt（或 G），按住右键呼出轮盘，移动选择，松开发送。\nEsc / 左键取消；仅在本机桌面显示，不向游戏发送信号。')
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.enabled = QCheckBox('启用全局 Ping')
        self.enabled.toggled.connect(controller.enable)
        layout.addWidget(self.enabled)
        self.trigger = QComboBox()
        self.trigger.addItems(TRIGGERS.keys())
        self.trigger.setCurrentText(controller.prefs['trigger'])
        self.trigger.currentTextChanged.connect(lambda v: controller.configure('trigger', v))
        layout.addWidget(self.trigger)
        for key, title, low, high in [('volume', '音量', 0, 100), ('scale', '大小', 75, 150)]:
            row = QHBoxLayout()
            label = QLabel(f'{title} {controller.prefs[key]}%')
            label.setMinimumWidth(92)
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(low, high)
            slider.setValue(controller.prefs[key])
            slider.valueChanged.connect(lambda v, k=key, t=title, l=label: (l.setText(f'{t} {v}%'), controller.configure(k, v)))
            row.addWidget(label)
            row.addWidget(slider)
            layout.addLayout(row)
        grid = QGridLayout()
        for i, ping in enumerate(PINGS):
            button = QPushButton(ping.title)
            button.clicked.connect(lambda checked=False, index=i: controller.try_ping(index))
            grid.addWidget(button, i // 3, i % 3)
        layout.addLayout(grid)
        controller.preview = Preview(art)
        controller.preview.scale = controller.prefs['scale'] / 100
        layout.addWidget(controller.preview)
        self.status = QLabel('全局信号已关闭，仍可在窗口内试用。')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        quit_button = QPushButton('退出软件')
        quit_button.clicked.connect(self.quit)
        layout.addWidget(quit_button)
        self.setCentralWidget(container)
        self.tray_toggle = None
        if not controller.smoke and QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = QSystemTrayIcon(icon, self)
            menu = QMenu()
            show = menu.addAction('打开 LoLPing')
            show.triggered.connect(self.reopen)
            self.tray_toggle = menu.addAction('启用全局 Ping')
            self.tray_toggle.setCheckable(True)
            self.tray_toggle.toggled.connect(controller.enable)
            menu.addSeparator()
            menu.addAction('退出软件').triggered.connect(self.quit)
            self.tray.setContextMenu(menu)
            self.tray.activated.connect(lambda reason: self.reopen() if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick) else None)
            self.tray.setToolTip('LoLPing · 已暂停')
            self.tray.show()
        controller.changed.connect(self.state_changed)

    def state_changed(self, enabled, message):
        self.enabled.blockSignals(True)
        self.enabled.setChecked(enabled)
        self.enabled.blockSignals(False)
        if self.tray_toggle:
            self.tray_toggle.blockSignals(True)
            self.tray_toggle.setChecked(enabled)
            self.tray_toggle.blockSignals(False)
            self.tray.setToolTip('LoLPing · ' + ('已启用' if enabled else '已暂停'))
        self.status.setText(message)

    def reopen(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        if self.tray and not self.quitting:
            self.hide()
            event.ignore()
        else:
            event.accept()
            if not self.quitting:
                self.quitting = True
                if self.tray:
                    self.tray.hide()
                self.controller.app.quit()

    def quit(self):
        self.quitting = True
        if self.tray:
            self.tray.hide()
        self.controller.app.quit()


def smoke_test(app, window, controller, art):
    """Render real widgets/assets and exercise timers without installing hooks."""
    from PySide6.QtCore import QPointF
    assert window.centralWidget() is not None
    for scale in (.75, 1, 1.5):
        for index in range(9):
            image = QImage(500, 500, QImage.Format.Format_ARGB32_Premultiplied)
            image.fill(QColor('#101e28'))
            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            art.wheel(painter, QPointF(250, 250), scale, index)
            painter.end()
            assert image.pixelColor(250, 250) != QColor('#101e28')
            for age in (.05, .25, .8, 1.8):
                image.fill(Qt.GlobalColor.transparent)
                painter = QPainter(image)
                art.effect(painter, QPointF(250, 250), scale, index, age)
                painter.end()
                assert any(image.pixelColor(250, y).alpha() for y in range(100, 350))
    output = os.environ.get('LOLPING_SMOKE_OUTPUT')
    if output:
        assert window.grab().save(output)
    controller.preview.play(0)
    controller.cancel_all()
    assert not controller.preview.timer.isActive()
    assert not controller.wheel.isVisible()
    assert not controller.effect.isVisible()
    print('UI smoke test passed: 27 wheels, 108 effect frames, assets, preview cancellation.')
    app.quit()


def main():
    smoke = '--smoke-test' in sys.argv
    app = QApplication(sys.argv)
    app.setApplicationName('LoLPing')
    app.setOrganizationName('LoLPing')
    app.setQuitOnLastWindowClosed(False)
    handle = None
    if not smoke:
        from . import win32
        handle = win32.singleton()
        if handle is None:
            QMessageBox.information(None, 'LoLPing', 'LoLPing 已在运行，请从系统托盘打开。')
            return 0
    try:
        art = Art(check_assets())
        prefs = load(settings_path()) if not smoke else load(Path('/nonexistent-lolping-settings'))
        restored_enabled = prefs['enabled']
        icon = QIcon(str(resource_root() / 'Icons/ping.png'))
        app.setWindowIcon(icon)
        controller = Controller(app, art, prefs, smoke)
        window = Window(controller, art, icon)
        app.aboutToQuit.connect(controller.shutdown)
        window.show()
        if smoke:
            result = [0]
            def run_smoke():
                try:
                    smoke_test(app, window, controller, art)
                except Exception:
                    import traceback
                    traceback.print_exc()
                    result[0] = 1
                    app.quit()
            QTimer.singleShot(50, run_smoke)
            app.exec()
            return result[0]
        if restored_enabled:
            controller.enable(True)
        return app.exec()
    except Exception as error:
        if smoke:
            raise
        QMessageBox.critical(None, 'LoLPing 启动失败', str(error))
        return 1
    finally:
        if handle:
            win32.kernel32.CloseHandle(handle)
