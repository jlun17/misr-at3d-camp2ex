"""
Create a forward-then-backward looping animation from a directory of PNG frames.

Expects files named like: frame00.png, frame01.png, frame02.png, ...

Usage:
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


def create_animation(frame_dir: str, output_path: str, fps: float = 12.0, loop: int = 0):
    """
    Create a looping forward-backward GIF from PNG frames.

    Args:
        frame_dir: Directory containing frame{i:02d}.png files.
        output_path: Path to save the output GIF.
        fps: Frames per second for playback.
        loop: Number of loops (0 = infinite loop).
    """
    frame_paths = find_frames(frame_dir)
    print(f"Found {len(frame_paths)} frames.")

    sequence_paths = build_boomerang_sequence(frame_paths)
    print(f"Boomerang sequence length: {len(sequence_paths)} frames.")

    images = [Image.open(p).convert("RGBA") for p in sequence_paths]

    duration_ms = int(1000 / fps)

    # Save as animated GIF
    images[0].save(
        output_path,
        save_all=True,
        append_images=images[1:],
        duration=duration_ms,
        loop=loop,
        disposal=2,
    )
    print(f"Saved animation to {output_path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("frame_dir", help="Directory containing frame{i:02d}.png files")
    parser.add_argument("output", help="Output GIF path (e.g. output.gif)")
    parser.add_argument("--fps", type=float, default=12.0, help="Frames per second (default: 12)")
    parser.add_argument("--loop", type=int, default=0, help="Number of loops, 0 = infinite (default: 0)")

    args = parser.parse_args()

    try:
        create_animation(args.frame_dir, args.output, fps=args.fps, loop=args.loop)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()