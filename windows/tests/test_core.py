import itertools
import math
from pathlib import Path
import tempfile
import unittest
from lolping.core import CHORDS, Gesture, Mod, PINGS, clamp_center, selection
from lolping.settings import DEFAULTS, load, save


class GestureTests(unittest.TestCase):
    def open(self, machine=None, anchor=(500, 400)):
        machine = machine or Gesture()
        self.assertEqual(machine.flags_changed(machine.chord, anchor), [('arm', anchor)])
        self.assertEqual(machine.delay_elapsed(), [('show', anchor)])
        return machine

    def test_directions_and_scale(self):
        for scale in (.75, 1, 1.5):
            for i in range(8):
                angle = i * math.pi / 4
                self.assertEqual(selection((100 * scale * math.sin(angle), -100 * scale * math.cos(angle)), (0, 0), 66 * scale), i)
            self.assertEqual(selection((66 * scale, 0), (0, 0), 66 * scale), 8)
            self.assertEqual(selection((66 * scale + .01, 0), (0, 0), 66 * scale), 2)

    def test_sector_boundaries(self):
        for i in range(8):
            for delta, expected in ((-.00001, i), (.00001, (i + 1) % 8)):
                angle = (i + .5) * math.pi / 4 + delta
                self.assertEqual(selection((100 * math.sin(angle), -100 * math.cos(angle)), (0, 0)), expected)

    def test_short_press_and_late_timer(self):
        m = Gesture()
        m.flags_changed(m.chord, (0, 0))
        self.assertEqual(m.flags_changed(Mod.NONE, (0, 0)), [('hide',)])
        self.assertEqual(m.delay_elapsed(), [])

    def test_all_chords_and_release_orders(self):
        for chord in CHORDS.values():
            keys = [k for k in (Mod.CTRL, Mod.ALT, Mod.SHIFT, Mod.WIN) if k & chord]
            for order in itertools.permutations(keys):
                m = self.open(Gesture(chord))
                m.moved((400, 400))
                remaining = chord
                commits = []
                for key in order:
                    remaining &= ~key
                    commits += [a for a in m.flags_changed(remaining, (1, 2)) if a[0] == 'commit']
                self.assertEqual(commits, [('commit', 6, (500, 400))])
                self.assertEqual(m.phase, 'idle')

    def test_repress_requires_full_release(self):
        m = self.open()
        m.flags_changed(m.chord & ~Mod.SHIFT, (0, 0))
        self.assertEqual(m.flags_changed(m.chord, (0, 0)), [])
        self.assertEqual(m.delay_elapsed(), [])
        m.flags_changed(Mod.NONE, (0, 0))
        self.open(m)

    def test_cancel_during_arming_and_open(self):
        for opened in (False, True):
            m = Gesture()
            m.flags_changed(m.chord, (0, 0))
            if opened:
                m.delay_elapsed()
            self.assertEqual(m.cancel(), [('hide',)])
            self.assertEqual(m.phase, 'blocked')
            self.assertEqual(m.delay_elapsed(), [])
            self.assertEqual(m.flags_changed(Mod.NONE, (0, 0)), [])
            self.assertEqual(m.phase, 'idle')

    def test_extra_modifier_cancels(self):
        m = self.open()
        self.assertEqual(m.flags_changed(m.chord | Mod.WIN, (0, 0)), [('hide',)])
        self.assertEqual(m.flags_changed(Mod.NONE, (0, 0)), [])

    def test_drag_or_existing_key_blocks(self):
        m = Gesture()
        self.assertEqual(m.flags_changed(m.chord, (0, 0), True), [])
        self.assertEqual(m.phase, 'blocked')
        self.assertEqual(m.delay_elapsed(), [])

    def test_disable_prevents_commit(self):
        m = self.open()
        m.reset()
        self.assertEqual(m.flags_changed(Mod.NONE, (0, 0)), [])
        self.assertEqual(m.delay_elapsed(), [])

    def test_start_while_chord_held(self):
        m = Gesture()
        m.reset(blocked=True)
        self.assertEqual(m.flags_changed(m.chord, (0, 0)), [])
        m.flags_changed(Mod.NONE, (0, 0))
        self.open(m)

    def test_negative_monitor_edge_keeps_anchor(self):
        anchor = (-1915, -1075)
        center = clamp_center(anchor, (-1920, -1080, 1920, 1080), 150)
        self.assertEqual(center, (-1770, -930))
        m = self.open(anchor=anchor)
        self.assertEqual(m.set_center(center), [])
        self.assertEqual(m.selected, 8)
        m.moved((center[0] + 90, center[1]))
        self.assertEqual(m.flags_changed(Mod.NONE, (0, 0)), [('hide',), ('commit', 2, anchor)])

    def test_motion_during_delay_is_applied(self):
        m = Gesture()
        m.flags_changed(m.chord, (500, 400))
        self.assertEqual(m.moved((500, 300)), [])
        m.delay_elapsed()
        self.assertEqual(m.set_center((500, 400)), [('hover', 0)])

    def test_small_screen_clamping(self):
        self.assertEqual(clamp_center((0, 0), (-100, -100, 200, 200), 152), (0, 0))

    def test_idle_motion_never_opens(self):
        m = Gesture()
        for point in [(0, 0), (-1000, 500), (9000, 7000)]:
            self.assertEqual(m.moved(point), [])
            self.assertEqual(m.delay_elapsed(), [])


class SettingsTests(unittest.TestCase):
    def test_round_trip_and_corruption(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'nested/settings.json'
            self.assertEqual(load(path), DEFAULTS)
            prefs = dict(DEFAULTS, volume=0, scale=150, enabled=True)
            save(path, prefs)
            self.assertEqual(load(path), prefs)
            self.assertFalse(path.with_suffix('.tmp').exists())
            for text in ('broken', '[]', 'null', '{"enabled": "yes", "chord": [], "volume": true}'):
                path.write_text(text)
                self.assertEqual(load(path), DEFAULTS)
            path.write_text('{"volume": -2, "scale": 999, "chord": "invalid"}')
            self.assertEqual(load(path), dict(DEFAULTS, volume=0, scale=150))


class AssetTests(unittest.TestCase):
    def test_every_ping_has_packaged_assets(self):
        import json
        root = Path(__file__).resolve().parents[2] / 'Resources'
        vectors = json.loads((root / 'Artwork/ping-vectors.json').read_text())
        self.assertEqual(len(PINGS), 9)
        for ping in PINGS:
            self.assertGreater((root / 'Sounds' / (ping.sound + '.mp3')).stat().st_size, 1000)
            import wave
            import struct
            with wave.open(str(root / 'SoundsWav' / (ping.sound + '.wav')), 'rb') as sound:
                self.assertEqual((sound.getnchannels(), sound.getsampwidth(), sound.getframerate()), (2, 2, 44100))
                self.assertEqual(sound.getcomptype(), 'NONE')
                self.assertTrue(.1 < sound.getnframes() / sound.getframerate() < 5)
                samples = sound.readframes(sound.getnframes())
                self.assertTrue(any(abs(value[0]) > 100 for value in struct.iter_unpack('<h', samples)))
            for contour in vectors[ping.key]['contours']:
                self.assertGreaterEqual(len(contour), 3)
                for x, y in contour:
                    self.assertTrue(0 <= x <= 1 and 0 <= y <= 1)


if __name__ == '__main__':
    unittest.main()
