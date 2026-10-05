"""Short, predecoded PCM effects; no QMediaPlayer/FFmpeg MP3 resampling."""
from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtMultimedia import QMediaDevices, QSoundEffect
from .core import PINGS
from .visuals import resource_root


class Sound(QObject):
    error = Signal(str)

    def __init__(self):
        super().__init__()
        self.devices = QMediaDevices(self)
        self.devices.audioOutputsChanged.connect(self.outputs_changed)
        self.effects = {}
        self.pending = None
        self.volume = .55

    def set_volume(self, volume):
        self.volume = max(0, min(100, volume)) / 100
        for effect in self.effects.values():
            effect.setVolume(self.volume)

    def play(self, index, volume):
        self.stop()
        self.set_volume(volume)
        if self.volume == 0:
            return
        device = QMediaDevices.defaultAudioOutput()
        if device.isNull():
            self.error.emit('未检测到音频输出设备，请连接或启用扬声器/耳机后重试。')
            return
        self.pending = index
        effect = self.effects.get(index)
        if effect is None:
            effect = QSoundEffect(self)
            effect.setAudioDevice(device)
            effect.setLoopCount(1)
            effect.setVolume(self.volume)
            self.effects[index] = effect
            effect.statusChanged.connect(lambda i=index: self.start_if_ready(i))
            source = resource_root() / 'SoundsWav' / (PINGS[index].sound + '.wav')
            effect.setSource(QUrl.fromLocalFile(str(source)))
        self.start_if_ready(index)

    def start_if_ready(self, index):
        # A previous request may finish loading after cancellation or another Ping.
        if self.pending != index:
            return
        effect = self.effects[index]
        if effect.status() == QSoundEffect.Status.Ready:
            self.pending = None
            effect.play()
        elif effect.status() == QSoundEffect.Status.Error:
            self.pending = None
            self.error.emit('音效加载失败：' + PINGS[index].title + '。请检查 WAV 素材和音频输出设备。')
            # Permit retry after a transient device or loading failure.
            effect.statusChanged.disconnect()
            effect.deleteLater()
            del self.effects[index]

    def stop(self):
        self.pending = None
        for effect in self.effects.values():
            effect.stop()

    def outputs_changed(self):
        # Release cached players bound to the old default device, including
        # Bluetooth/headphone disconnects. The next Ping uses the new default.
        self.stop()
        for effect in self.effects.values():
            effect.statusChanged.disconnect()
            effect.deleteLater()
        self.effects.clear()
