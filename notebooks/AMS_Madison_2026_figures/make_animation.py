"""
Create a forward-then-backward looping animation from a directory of PNG frames.

Expects files named like: frame00.png, frame01.png, frame02.png, ...

Supports several output formats, in order of image quality:
    - apng  : Lossless, full 32-bit color + alpha. Largest files. (recommended for max quality)
    - webp  : Lossless or high-quality lossy, full color + alpha. Great quality/size balance.
    - mp4   : Lossy but visually near-lossless at high quality settings. Smallest files.
              No alpha channel support. Requires ffmpeg (via imageio-ffmpeg).
    - gif   : Widest compatibility, but limited to 256 colors per frame (lowest quality).
              Uses adaptive per-frame palettes with no dithering to maximize quality.

Usage:
    python make_animation.py /path/to/frames_dir output.webp --fps 12
    python make_animation.py /path/to/frames_dir output.png --format apng --fps 12
    python make_animation.py /path/to/frames_dir output.mp4 --fps 24 --crf 15
    python make_animation.py /path/to/frames_dir output.gif --fps 12
"""

import argparse
import glob
import os
import re
import sys

from PIL import Image


def find_frames(frame_dir: str):
    """Find and sort frame files matching frame{i:02d}.png (or similar zero-padded patterns)."""
    pattern = os.path.join(frame_dir, "frame*.png")
    files = glob.glob(pattern)

    if not files:
        raise FileNotFoundError(f"No files matching 'frame*.png' found in {frame_dir}")

    def frame_number(path):
        match = re.search(r"frame(\d+)\.png$", os.path.basename(path))
        if not match:
            return float("inf")  # push non-matching files to the end
        return int(match.group(1))

    files.sort(key=frame_number)
    return files


def build_boomerang_sequence(frames):
    """Return frames playing forward then backward, without duplicating the endpoints."""
    if len(frames) < 2:
        return frames
    # Forward: frame0 .. frameN
    # Backward: frameN-1 .. frame1  (skip duplicating last and first frame)
    return frames + frames[-2:0:-1]


def save_apng(images, output_path, duration_ms, loop):
    """Lossless animated PNG. Full 32-bit color + alpha, no palette quantization."""
    images[0].save(
        output_path,
        format="PNG",
        save_all=True,
        append_images=images[1:],
        duration=duration_ms,
        loop=loop,
    )


def save_webp(images, output_path, duration_ms, loop, lossless=True, quality=95):
    """Animated WebP. Lossless mode preserves full quality; still much smaller than APNG."""
    images[0].save(
        output_path,
        format="WEBP",
        save_all=True,
        append_images=images[1:],
        duration=duration_ms,
        loop=loop,
        lossless=lossless,
        quality=quality,
        method=6,  # slowest/best compression effort
    )


def save_gif(images, output_path, duration_ms, loop):
    """
    Animated GIF with best-effort quality: each frame gets its own adaptive
    palette (up to 256 colors) and dithering is disabled to avoid noisy speckling.
    Still inherently lossy compared to APNG/WebP/MP4 due to the 256-color cap.
    """
    quantized = [
        im.convert("RGB").quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        for im in images
    ]
    quantized[0].save(
        output_path,
        save_all=True,
        append_images=quantized[1:],
        duration=duration_ms,
        loop=loop,
        disposal=2,
    )


def save_mp4(images, output_path, fps, crf=15):
    """
    High-quality H.264 MP4 via imageio-ffmpeg. crf lower = higher quality
    (15-18 is visually near-lossless; default libx264 quality is crf=23).
    No alpha channel support - transparency will be flattened onto white.
    """
    try:
        import imageio.v3 as iio
    except ImportError:
        raise RuntimeError(
            "MP4 export requires imageio and imageio-ffmpeg. Install with:\n"
            "    pip install imageio imageio-ffmpeg"
        )

    import numpy as np

    frames = []
    for im in images:
        if im.mode == "RGBA":
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im, mask=im.split()[3])
            im = bg
        else:
            im = im.convert("RGB")
        frames.append(np.array(im))

    iio.imwrite(
        output_path,
        frames,
        fps=fps,
        codec="libx264",
        output_params=["-crf", str(crf), "-pix_fmt", "yuv420p"],
    )


def create_animation(
    frame_dir: str,
    output_path: str,
    fmt: str,
    fps: float = 12.0,
    loop: int = 0,
    webp_lossless: bool = True,
    webp_quality: int = 95,
    crf: int = 15,
):
    frame_paths = find_frames(frame_dir)
    print(f"Found {len(frame_paths)} frames.")

    sequence_paths = build_boomerang_sequence(frame_paths)
    print(f"Boomerang sequence length: {len(sequence_paths)} frames.")

    images = [Image.open(p).convert("RGBA") for p in sequence_paths]
    duration_ms = int(1000 / fps)

    if fmt == "apng":
        save_apng(images, output_path, duration_ms, loop)
    elif fmt == "webp":
        save_webp(images, output_path, duration_ms, loop, lossless=webp_lossless, quality=webp_quality)
    elif fmt == "gif":
        save_gif(images, output_path, duration_ms, loop)
    elif fmt == "mp4":
        save_mp4(images, output_path, fps, crf=crf)
    else:
        raise ValueError(f"Unknown format: {fmt}")

    print(f"Saved animation to {output_path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("frame_dir", help="Directory containing frame{i:02d}.png files")
    parser.add_argument("output", help="Output file path (e.g. output.webp, output.png, output.mp4, output.gif)")
    parser.add_argument(
        "--format",
        choices=["apng", "webp", "gif", "mp4"],
        default=None,
        help="Output format. If omitted, inferred from the output file extension (.png -> apng).",
    )
    parser.add_argument("--fps", type=float, default=12.0, help="Frames per second (default: 12)")
    parser.add_argument("--loop", type=int, default=0, help="Number of loops, 0 = infinite (default: 0)")
    parser.add_argument("--webp-lossy", action="store_true", help="Use lossy WebP instead of lossless")
    parser.add_argument("--webp-quality", type=int, default=95, help="WebP quality 0-100 if lossy (default: 95)")
    parser.add_argument("--crf", type=int, default=15, help="MP4 quality, lower=better, 15-18 is near-lossless")

    args = parser.parse_args()

    fmt = args.format
    if fmt is None:
        ext = os.path.splitext(args.output)[1].lower().lstrip(".")
        fmt = "apng" if ext == "png" else ext
        if fmt not in ("apng", "webp", "gif", "mp4"):
            print(f"Could not infer format from extension '.{ext}'. Please pass --format.", file=sys.stderr)
            sys.exit(1)

    try:
        create_animation(
            args.frame_dir,
            args.output,
            fmt=fmt,
            fps=args.fps,
            loop=args.loop,
            webp_lossless=not args.webp_lossy,
            webp_quality=args.webp_quality,
            crf=args.crf,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()