from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


class MockMediaFixtureError(RuntimeError):
    """Raised when a deterministic mock media fixture cannot be produced."""


def deterministic_mock_media_bytes(
    media_type: str,
    *,
    data_dir: str | Path,
    ffmpeg_path: str = "ffmpeg",
    native_audio: bool = False,
) -> bytes:
    """Return a small, valid deterministic media payload for mock/dev execution.

    The fixture is intentionally tiny but is a real decodable file so downstream
    editing/probing paths can exercise the same code paths as provider output.
    """

    normalized = media_type.strip().lower()
    if normalized not in {"image", "video", "audio"}:
        raise MockMediaFixtureError(f"unsupported_mock_media_type:{media_type}")

    root = Path(data_dir)
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise MockMediaFixtureError("mock_media_data_dir_unavailable") from error

    executable = _resolve_ffmpeg(ffmpeg_path)

    suffix = {"image": ".png", "video": ".mp4", "audio": ".mp3"}[normalized]
    try:
        with tempfile.TemporaryDirectory(prefix="adcraft-mock-", dir=root) as tmp:
            output = Path(tmp) / f"fixture{suffix}"
            command = _command(
                executable,
                normalized,
                output,
                native_audio=native_audio,
            )
            result = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=30,
            )
            if result.returncode != 0 or not output.is_file():
                detail = result.stderr.decode("utf-8", errors="replace")[-1000:]
                raise MockMediaFixtureError(
                    f"mock_media_ffmpeg_failed:{result.returncode}:{detail}"
                )
            payload = output.read_bytes()
    except (OSError, subprocess.SubprocessError) as error:
        raise MockMediaFixtureError("mock_media_fixture_generation_failed") from error

    if not payload:
        raise MockMediaFixtureError("mock_media_fixture_empty")
    return payload


def _resolve_ffmpeg(ffmpeg_path: str) -> str:
    candidate = str(ffmpeg_path or "ffmpeg")
    if "/" in candidate:
        if Path(candidate).is_file():
            return candidate
        raise MockMediaFixtureError(f"ffmpeg_not_found:{candidate}")
    resolved = shutil.which(candidate)
    if resolved is None:
        raise MockMediaFixtureError(f"ffmpeg_not_found:{candidate}")
    return resolved


def _command(
    ffmpeg: str,
    media_type: str,
    output: Path,
    *,
    native_audio: bool,
) -> list[str]:
    common = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-y",
    ]

    if media_type == "image":
        return common + [
            "-f",
            "lavfi",
            "-i",
            "color=c=0x20242b:s=320x180:d=1",
            "-frames:v",
            "1",
            "-vf",
            "format=rgb24",
            str(output),
        ]

    if media_type == "audio":
        return common + [
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=44100:duration=1",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "96k",
            "-map_metadata",
            "-1",
            str(output),
        ]

    command = common + [
        "-f",
        "lavfi",
        "-i",
        "color=c=0x20242b:s=320x180:r=24:d=1",
    ]
    if native_audio:
        command += [
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=44100:duration=1",
        ]
    command += [
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "-map_metadata",
        "-1",
    ]
    if native_audio:
        command += ["-c:a", "aac", "-b:a", "96k", "-shortest"]
    else:
        command += ["-an"]
    command += [str(output)]
    return command
