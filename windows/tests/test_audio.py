"""Test the real audio controller with fake Qt devices/loaders, without hardware.

This checks request/cancellation behavior, not Qt's native audio playback.
"""
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch
import importlib.util
import sys
import unittest


class Signal:
    def __init__(self, *args):
        self.slots = []
        self.values = []

    def connect(self, slot):
        self.slots.append(slot)

    def disconnect(self):
        self.slots.clear()

    def emit(self, *args):
        self.values.append(args)
        for slot in list(self.slots):
            slot(*args)


class Devices:
    device = None

    def __init__(self, parent):
        self.audioOutputsChanged = Signal()

    @classmethod
    def defaultAudioOutput(cls):
        return cls.device


class Effect:
    Status = SimpleNamespace(Loading=1, Ready=2, Error=3)

    def __init__(self, parent):
        self.statusChanged = Signal()
        self.state = self.Status.Loading
        self.play_count = 0
        self.stopped = False
        self.deleted = False

    def setAudioDevice(self, device):
        self.device = device

    def setLoopCount(self, count):
        self.loops = count

    def setVolume(self, volume):
        self.volume = volume

    def setSource(self, source):
        self.source = source

    def status(self):
        return self.state

    def finish(self, failed=False):
        self.state = self.Status.Error if failed else self.Status.Ready
        self.statusChanged.emit()

    def play(self):
        self.play_count += 1
        self.stopped = False

    def stop(self):
        self.stopped = True

    def deleteLater(self):
        self.deleted = True


def load_audio_controller():
    core = ModuleType('PySide6.QtCore')
    core.QObject = object
    core.QUrl = SimpleNamespace(fromLocalFile=lambda value: value)
    core.Signal = Signal
    multimedia = ModuleType('PySide6.QtMultimedia')
    multimedia.QMediaDevices = Devices
    multimedia.QSoundEffect = Effect
    visuals = ModuleType('lolping.visuals')
    visuals.resource_root = lambda: Path('/test-resources')
    replacements = {'PySide6.QtCore': core, 'PySide6.QtMultimedia': multimedia, 'lolping.visuals': visuals}
    spec = importlib.util.spec_from_file_location('lolping._audio_test', Path(__file__).resolve().parents[1] / 'lolping/audio.py')
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, replacements):
        spec.loader.exec_module(module)
    return module.Sound


class SoundRequestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.Sound = load_audio_controller()

    def setUp(self):
        Devices.device = SimpleNamespace(isNull=lambda: False)
        self.sound = self.Sound()
        self.sound.error = Signal()

    def test_loading_plays_once_when_ready(self):
        self.sound.play(0, 55)
        effect = self.sound.effects[0]
        self.assertEqual(Path(effect.source).parts[-2:], ('SoundsWav', 'retreat.wav'))
        self.assertEqual(effect.play_count, 0)
        effect.finish()
        effect.finish()
        self.assertEqual(effect.play_count, 1)
        self.assertEqual(effect.volume, .55)
        self.assertEqual(effect.loops, 1)

    def test_cancel_while_loading_does_not_play_later(self):
        self.sound.play(0, 55)
        effect = self.sound.effects[0]
        self.sound.stop()
        effect.finish()
        self.assertEqual(effect.play_count, 0)

    def test_new_ping_supersedes_old_load(self):
        self.sound.play(0, 55)
        old = self.sound.effects[0]
        self.sound.play(1, 70)
        new = self.sound.effects[1]
        old.finish()
        new.finish()
        self.assertEqual(old.play_count, 0)
        self.assertEqual(new.play_count, 1)
        self.assertEqual(new.volume, .7)

    def test_cached_effect_replays_and_volume_updates(self):
        self.sound.play(0, 55)
        effect = self.sound.effects[0]
        effect.finish()
        self.sound.play(0, 80)
        self.assertEqual(effect.play_count, 2)
        self.sound.set_volume(20)
        self.assertEqual(effect.volume, .2)

    def test_mute_does_not_load_or_play(self):
        self.sound.play(0, 0)
        self.assertEqual(self.sound.effects, {})
        self.assertIsNone(self.sound.pending)

    def test_no_device_reports_error_without_starting_loader(self):
        Devices.device = SimpleNamespace(isNull=lambda: True)
        self.sound.play(0, 55)
        self.assertEqual(self.sound.effects, {})
        self.assertEqual(len(self.sound.error.values), 1)

    def test_failed_load_can_retry(self):
        self.sound.play(0, 55)
        old = self.sound.effects[0]
        old.finish(failed=True)
        self.assertEqual(len(self.sound.error.values), 1)
        self.assertTrue(old.deleted)
        self.sound.play(0, 55)
        self.assertIsNot(self.sound.effects[0], old)
        self.sound.effects[0].finish()
        self.assertEqual(self.sound.effects[0].play_count, 1)

    def test_output_device_change_invalidates_old_effects(self):
        self.sound.play(0, 55)
        old = self.sound.effects[0]
        new_device = SimpleNamespace(isNull=lambda: False)
        Devices.device = new_device
        self.sound.devices.audioOutputsChanged.emit()
        old.finish()
        self.assertTrue(old.deleted)
        self.assertEqual(old.play_count, 0)
        self.sound.play(0, 55)
        self.assertIs(self.sound.effects[0].device, new_device)
