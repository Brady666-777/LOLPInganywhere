import json
import math
import sys
import time
from pathlib import Path
from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget
from .core import PINGS


def resource_root():
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS) / 'Resources'
    return Path(__file__).resolve().parents[2] / 'Resources'


def check_assets():
    root = resource_root()
    required = [root / 'Artwork/ping-vectors.json', root / 'Icons/ping.png']
    required += [root / 'SoundsWav' / (p.sound + '.wav') for p in PINGS]
    missing = [str(p) for p in required if not p.is_file()]
    if missing:
        raise FileNotFoundError('缺少素材：' + ', '.join(missing))
    vectors = json.loads(required[0].read_text(encoding='utf-8'))
    for ping in PINGS:
        if not vectors.get(ping.key, {}).get('contours'):
            raise ValueError('缺少矢量图标：' + ping.key)
    return vectors


class Art:
    def __init__(self, vectors):
        self.paths = {}
        for key, data in vectors.items():
            path = QPainterPath()
            path.setFillRule(Qt.FillRule.OddEvenFill)
            for contour in data['contours']:
                # Shared vectors use AppKit's bottom-left origin (see
                # trace_wheel_icons.py). Qt's origin is top-left: flip only
                # the normalized icon geometry, not text or wheel positions.
                x, y = contour[0]
                path.moveTo(x, 1 - y)
                for x, y in contour[1:]:
                    path.lineTo(x, 1 - y)
                path.closeSubpath()
            self.paths[key] = path

    def icon(self, painter, index, center, size, color=None):
        painter.save()
        painter.translate(center.x() - size / 2, center.y() - size / 2)
        painter.scale(size, size)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(color or PINGS[index].color))
        painter.drawPath(self.paths[PINGS[index].key])
        painter.restore()

    def wheel(self, p, center, scale, selected):
        p.save()
        p.translate(center)
        p.scale(scale, scale)
        p.setPen(QPen(QColor('#bca36d'), 1.5))
        p.setBrush(QColor(12, 24, 32, 240))
        p.drawEllipse(QPointF(0, 0), 140, 140)
        if selected < 8:
            p.setPen(Qt.PenStyle.NoPen)
            c = QColor(PINGS[selected].color)
            c.setAlpha(80)
            p.setBrush(c)
            p.drawPie(QRectF(-138, -138, 276, 276), round((67.5 - selected * 45) * 16), 45 * 16)
        p.setPen(QPen(QColor('#49606b'), 1))
        for i in range(8):
            a = (i * 45 + 22.5) * math.pi / 180
            p.drawLine(QPointF(66 * math.sin(a), -66 * math.cos(a)),
                       QPointF(139 * math.sin(a), -139 * math.cos(a)))
        p.setPen(QPen(QColor('#bca36d'), 1.5))
        p.setBrush(QColor('#101f29'))
        p.drawEllipse(QPointF(0, 0), 66, 66)
        for i in range(8):
            a = i * math.pi / 4
            self.icon(p, i, QPointF(101 * math.sin(a), -101 * math.cos(a)), 32 if selected == i else 24)
        self.icon(p, selected, QPointF(0, -15), 29)
        p.setPen(QColor('#f0e7d4'))
        font = QFont('Microsoft YaHei')
        font.setPixelSize(13)
        p.setFont(font)
        p.drawText(QRectF(-65, 10, 130, 28), Qt.AlignmentFlag.AlignCenter, PINGS[selected].title)
        p.restore()

    def effect(self, p, center, scale, index, age):
        if age < 0 or age >= 2.1:
            return
        p.save()
        p.translate(center)
        p.scale(scale, scale)
        p.setOpacity(min(1, age / .10) * min(1, (2.1 - age) / .5))
        color = QColor(PINGS[index].color)
        for offset in (0, .25):
            t = age - offset
            if 0 <= t < 1.35:
                c = QColor(color)
                c.setAlphaF((1 - t / 1.35) * .85)
                p.setPen(QPen(c, 2.5))
                p.setBrush(Qt.BrushStyle.NoBrush)
                radius = 10 + 45 * t
                p.drawEllipse(QPointF(0, 0), radius, radius * .42)
        lift = min(age / .18, 1) * 20 + math.sin(min(age, 1) * math.pi) * 5
        self.icon(p, index, QPointF(0, -18 - lift), 44)
        p.setPen(QPen(color, 2))
        p.drawLine(QPointF(-4, 0), QPointF(4, 0))
        p.drawLine(QPointF(0, -4), QPointF(0, 4))
        p.restore()


class Overlay(QWidget):
    def __init__(self, art):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowTransparentForInput |
                         Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.art = art
        self.mode = 'wheel'
        self.selected = 8
        self.scale = 1
        self.started = 0
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self.tick)

    def place(self, point, scale, screen):
        self.scale = scale
        size = round(304 * scale)
        self.winId()
        self.windowHandle().setScreen(screen)
        self.resize(size, size)
        self.move(round(point[0] - size / 2), round(point[1] - size / 2))

    def show_wheel(self, point, scale, screen):
        self.timer.stop()
        self.mode = 'wheel'
        self.selected = 8
        self.place(point, scale, screen)
        self.show()
        self.update()

    def show_ping(self, index, point, scale, screen):
        self.mode = 'effect'
        self.selected = index
        self.started = time.monotonic()
        self.place(point, scale, screen)
        self.show()
        self.timer.start()
        self.update()

    def clear(self):
        self.timer.stop()
        self.hide()

    def tick(self):
        if time.monotonic() - self.started >= 2.1:
            self.clear()
        else:
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        center = QPointF(self.width() / 2, self.height() / 2)
        if self.mode == 'wheel':
            self.art.wheel(p, center, self.scale, self.selected)
        else:
            self.art.effect(p, center, self.scale, self.selected, time.monotonic() - self.started)
        p.end()


class Preview(QWidget):
    def __init__(self, art):
        super().__init__()
        self.art = art
        self.index = 8
        self.scale = 1
        self.started = None
        self.setMinimumHeight(245)
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self.tick)

    def play(self, index):
        self.index = index
        self.started = time.monotonic()
        self.timer.start()
        self.update()

    def clear(self):
        self.timer.stop()
        self.started = None
        self.update()

    def tick(self):
        if time.monotonic() - self.started >= 2.1:
            self.clear()
        else:
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor('#0c1922'))
        if self.started is not None:
            self.art.effect(p, QPointF(self.width() / 2, self.height() * .65), self.scale,
                            self.index, time.monotonic() - self.started)
        else:
            p.setPen(QColor('#8ca4b1'))
            font = QFont('Microsoft YaHei')
            font.setPixelSize(14)
            p.setFont(font)
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, '点击上方信号，在这里试用')
        p.end()
