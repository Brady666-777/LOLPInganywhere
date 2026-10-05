"""Platform-independent gesture logic. Windows coordinates grow downwards."""
from dataclasses import dataclass
import math


TRIGGERS = {
    'Alt + 右键': 'alt',
    'G + 右键': 'g',
}


@dataclass(frozen=True)
class Ping:
    key: str
    title: str
    sound: str
    color: str


PINGS = (
    Ping('retreat', '撤退', 'retreat', '#ff635b'),
    Ping('push', '推进', 'push', '#62dce0'),
    Ping('onMyWay', '正在路上', 'on_my_way', '#67d4bb'),
    Ping('allIn', '全力进攻', 'all_in', '#f4ad69'),
    Ping('assist', '请求协助', 'assist_me', '#62c5ed'),
    Ping('needVision', '需要视野', 'need_vision', '#a29bfa'),
    Ping('missing', '敌人消失', 'q_mark', '#f3ce75'),
    Ping('enemyVision', '敌方视野', 'enemy_vision', '#ee747c'),
    Ping('generic', '普通信号', 'alert', '#63cfff'),
)


def selection(point, center, dead_zone=66):
    dx, dy = point[0] - center[0], point[1] - center[1]
    if math.hypot(dx, dy) <= dead_zone:
        return 8
    return math.floor((math.atan2(dx, -dy) + math.pi / 8) / (math.pi / 4)) % 8


def clamp_center(anchor, rect, radius):
    x, y, w, h = rect
    def clamp(v, lo, hi):
        return (lo + hi) / 2 if lo > hi else min(max(v, lo), hi)
    return clamp(anchor[0], x + radius, x + w - radius), clamp(anchor[1], y + radius, y + h - radius)


class Gesture:
    """State machine: idle → open (on trigger+LMB down) → commit/cancel (on LMB up)."""

    def __init__(self, trigger='alt', scale=1):
        self.trigger = trigger  # 'alt' or 'g'
        self.dead_zone = 66 * scale
        self.reset()

    @property
    def active(self):
        return self.phase == 'open'

    def reset(self):
        self.phase = 'idle'
        self.trigger_held = False
        self.selected = 8
        self.anchor = self.center = self.pointer = (0, 0)

    def trigger_down(self, point):
        """Called when the trigger key is pressed."""
        self.trigger_held = True
        return []

    def trigger_up(self):
        """Called when the trigger key is released."""
        self.trigger_held = False
        if self.phase == 'open':
            # Cancel: trigger released before LMB
            self.phase = 'idle'
            self.selected = 8
            return [('hide',)]
        return []

    def lmb_down(self, point):
        """Called when LMB is pressed while trigger is held."""
        if not self.trigger_held or self.phase != 'idle':
            return []
        self.anchor = self.center = self.pointer = point
        self.selected = 8
        self.phase = 'open'
        return [('show', point)]

    def lmb_up(self):
        """Called when LMB is released."""
        if self.phase != 'open':
            return []
        selected = self.selected
        anchor = self.anchor
        self.phase = 'idle'
        self.selected = 8
        if selected == 8:
            # Center = cancel
            return [('hide',)]
        return [('hide',), ('commit', selected, anchor)]

    def moved(self, point):
        self.pointer = point
        if self.phase != 'open':
            return []
        self.selected = selection(point, self.center, self.dead_zone)
        return [('hover', self.selected)]

    def cancel(self):
        if self.phase == 'open':
            self.phase = 'idle'
            self.selected = 8
            return [('hide',)]
        return []
