# Windows PCM sound effects

Derived from the nine corresponding `../Sounds/*.mp3` assets, with the same source attribution and rights described in `../asset-sources.json`. These are format conversions, not new recordings.

Generated using `python scripts/convert-windows-sounds.py`: FFmpeg decodes to 44.1 kHz, stereo, signed 16-bit PCM WAV. Runtime playback uses Qt QSoundEffect and does not require an FFmpeg executable. Original MP3 files remain unchanged for macOS.
