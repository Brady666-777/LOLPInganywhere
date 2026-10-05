"""Maintainer tool: convert bundled MP3s to PCM WAV for Qt QSoundEffect.

Requires ffmpeg on PATH only when regenerating assets; normal builds are offline.
"""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'windows'))
from lolping.core import PINGS


def main():
    destination = ROOT / 'Resources' / 'SoundsWav'
    destination.mkdir(exist_ok=True)
    for ping in PINGS:
        source = ROOT / 'Resources' / 'Sounds' / (ping.sound + '.mp3')
        target = destination / (ping.sound + '.wav')
        subprocess.run([
            'ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin', '-y',
            '-i', str(source), '-map_metadata', '-1', '-vn',
            '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '2', str(target),
        ], check=True)
        print(target.name)


if __name__ == '__main__':
    main()
