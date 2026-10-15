from __future__ import annotations

import struct
import wave
from pathlib import Path

from manim import Scene


def test_add_sound(tmpdir):
    # create sound file
    sound_loc = Path(tmpdir, "noise.wav")
    with wave.open(str(sound_loc), "w") as f:
        f.setparams((2, 2, 44100, 0, "NONE", "not compressed"))
        for _ in range(22050):  # half a second of sound
            packed_value = struct.pack("h", 14242)
            f.writeframes(packed_value)
            f.writeframes(packed_value)

    scene = Scene()
    scene.add_sound(sound_loc)


def _write_noise(path, seconds):
    with wave.open(str(path), "w") as f:
        f.setparams((2, 2, 44100, 0, "NONE", "not compressed"))
        packed_value = struct.pack("h", 14242)
        f.writeframes(packed_value * 2 * int(44100 * seconds))


def test_stop_sound_truncates_audio(tmpdir):
    sound_loc = Path(tmpdir, "noise.wav")
    _write_noise(sound_loc, 2)

    scene = Scene()
    file_writer = scene.renderer.file_writer
    scene.add_sound(sound_loc)
    scene.add_sound(sound_loc, time_offset=1.5)
    scene.renderer.time = 0.5
    scene.stop_sound()
    assert file_writer.audio_segment.duration_seconds == 0.5

    # sounds added after stopping play in full
    scene.renderer.time = 1
    scene.add_sound(sound_loc)
    assert file_writer.audio_segment.duration_seconds == 3


def test_stop_sound_without_sound_is_noop():
    scene = Scene()
    scene.stop_sound()
    assert not scene.renderer.file_writer.includes_sound


def test_pause_and_resume_sound(tmpdir):
    sound_loc = Path(tmpdir, "noise.wav")
    _write_noise(sound_loc, 2)

    scene = Scene()
    file_writer = scene.renderer.file_writer
    scene.add_sound(sound_loc)
    scene.renderer.time = 0.5
    scene.pause_sound()
    assert file_writer.audio_segment.duration_seconds == 0.5

    scene.renderer.time = 1.5
    scene.resume_sound()
    audio = file_writer.audio_segment
    # the remaining 1.5 seconds play after a 1 second pause
    assert audio.duration_seconds == 3
    assert audio[:500].max > 0
    assert audio[500:1500].max == 0
    assert audio[1500:].max > 0


def test_pause_sound_delays_scheduled_sounds(tmpdir):
    sound_loc = Path(tmpdir, "noise.wav")
    _write_noise(sound_loc, 0.5)

    scene = Scene()
    file_writer = scene.renderer.file_writer
    scene.add_sound(sound_loc, time_offset=1)
    scene.pause_sound()
    scene.renderer.time = 2
    scene.resume_sound()
    audio = file_writer.audio_segment
    assert audio.duration_seconds == 3.5
    assert audio[:3000].max == 0
    assert audio[3000:].max > 0


def test_stop_sound_discards_paused_sound(tmpdir):
    sound_loc = Path(tmpdir, "noise.wav")
    _write_noise(sound_loc, 2)

    scene = Scene()
    file_writer = scene.renderer.file_writer
    scene.add_sound(sound_loc)
    scene.renderer.time = 0.5
    scene.pause_sound()
    scene.stop_sound()
    scene.renderer.time = 1
    scene.resume_sound()
    assert file_writer.audio_segment.duration_seconds == 0.5


def test_pause_and_resume_sound_warn_when_misused(manim_caplog):
    scene = Scene()
    scene.resume_sound()
    assert "Sound is not paused" in manim_caplog.text

    scene.pause_sound()
    scene.pause_sound()
    assert "Sound is already paused" in manim_caplog.text

    # pausing a scene without sound still allows resuming without warnings
    manim_caplog.clear()
    scene.resume_sound()
    assert manim_caplog.text == ""
    assert not scene.renderer.file_writer.includes_sound
