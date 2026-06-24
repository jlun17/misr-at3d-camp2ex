"""
Identifies horizontally contiguous regions in a 3D binary array.

"Horizontal" connectivity is defined along the X and Y axes only — two voxels
are in the same region if they are connected via 4-directional (up/down/left/right)
neighbours within the same Z-slice, or across Z-slices if they share the same
(x, y) position AND are connected through a continuous horizontal path at every
intermediate Z-level.

Array axis order is (X, Y, Z): volume[x, y, z].

If you only want per-slice regions (no cross-Z linkage), use `label_per_slice`.
If you want regions that span Z but only via horizontal paths, use `label_3d_horizontal`.
"""

from collections import deque
import numpy as np


# ---------------------------------------------------------------------------
# Option A – label each Z-slice independently
# ---------------------------------------------------------------------------

def label_per_slice(volume: np.ndarray) -> tuple[np.ndarray, int]:
    """
    Label contiguous regions independently in each Z-slice (XY plane).

    Connectivity: 4-directional (horizontal + vertical within the slice).
    Z-slices are completely independent — the same physical column can belong
    to different label IDs in adjacent slices.

    Parameters
    ----------
    volume : np.ndarray, shape (X, Y, Z), dtype bool or int
        3-D binary array.  Non-zero values are treated as foreground.

    Returns
    -------
    labels : np.ndarray, shape (X, Y, Z), dtype int
        Each foreground voxel is assigned a unique positive integer label.
        Background voxels remain 0.
    num_regions : int
        Total number of distinct regions found across all slices.
    """
    if volume.ndim != 3:
        raise ValueError(f"Expected a 3-D array, got shape {volume.shape}")

    X, Y, Z = volume.shape
    labels = np.zeros_like(volume, dtype=int)
    next_label = 1

    # 4-directional neighbours in the XY plane
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # (dx, dy)

    for z in range(Z):
        slice_ = volume[:, :, z]
        visited = labels[:, :, z]  # shared reference — writing here updates `labels`

        for x_start in range(X):
            for y_start in range(Y):
                if slice_[x_start, y_start] and visited[x_start, y_start] == 0:
                    # BFS flood-fill from this seed
                    queue = deque([(x_start, y_start)])
                    visited[x_start, y_start] = next_label

                    while queue:
                        x, y = queue.popleft()
                        for dx, dy in directions:
                            nx, ny = x + dx, y + dy
                            if (0 <= nx < X and 0 <= ny < Y
                                    and slice_[nx, ny]
                                    and visited[nx, ny] == 0):
                                visited[nx, ny] = next_label
                                queue.append((nx, ny))

                    next_label += 1

    return labels, next_label - 1


# ---------------------------------------------------------------------------
# Option B – label regions that are connected horizontally across Z-slices
# ---------------------------------------------------------------------------

def label_3d_horizontal(volume: np.ndarray) -> tuple[np.ndarray, int]:
    """
    Label contiguous regions with horizontal-only connectivity in 3-D.

    Two foreground voxels belong to the same region if and only if they are
    connected by a path whose every step moves in the X or Y direction
    (never in the Z direction).  This means voxels at (x, y, z1) and
    (x, y, z2) are in the same region only if there is a horizontal path
    at *every* intermediate Z-level connecting them.

    In practice the algorithm uses a 4-directional BFS in 3-D, restricted
    to moves that do not change Z.

    Parameters
    ----------
    volume : np.ndarray, shape (X, Y, Z), dtype bool or int

    Returns
    -------
    labels : np.ndarray, shape (X, Y, Z), dtype int
    num_regions : int
    """
    if volume.ndim != 3:
        raise ValueError(f"Expected a 3-D array, got shape {volume.shape}")

    X, Y, Z = volume.shape
    labels = np.zeros_like(volume, dtype=int)
    next_label = 1

    # Only horizontal moves (dz is always 0)
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # (dx, dy)

    for x_start in range(X):
        for y_start in range(Y):
            for z_start in range(Z):
                if volume[x_start, y_start, z_start] and labels[x_start, y_start, z_start] == 0:
                    queue = deque([(x_start, y_start, z_start)])
                    labels[x_start, y_start, z_start] = next_label

                    while queue:
                        x, y, z = queue.popleft()
                        for dx, dy in directions:
                            nx, ny = x + dx, y + dy
                            # same Z-slice, adjacent XY neighbour
                            if (0 <= nx < X and 0 <= ny < Y
                                    and volume[nx, ny, z]
                                    and labels[nx, ny, z] == 0):
                                labels[nx, ny, z] = next_label
                                queue.append((nx, ny, z))

                    next_label += 1

    return labels, next_label - 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def region_properties(labels: np.ndarray) -> list[dict]:
    """
    Return basic properties for each labelled region.

    Parameters
    ----------
    labels : np.ndarray
        Output from label_per_slice or label_3d_horizontal.

    Returns
    -------
    List of dicts, one per region, each containing:
      - label      : int
      - voxel_count: int
      - bbox       : dict with x_min, x_max, y_min, y_max, z_min, z_max
      - centroid   : (x, y, z) floats
    """
    props = []
    for lbl in range(1, labels.max() + 1):
        coords = np.argwhere(labels == lbl)  # shape (N, 3) → (x, y, z)
        if coords.size == 0:
            continue
        x, y, z = coords[:, 0], coords[:, 1], coords[:, 2]
        props.append({
            "label": lbl,
            "voxel_count": len(coords),
            "bbox": {
                "x_min": int(x.min()), "x_max": int(x.max()),
                "y_min": int(y.min()), "y_max": int(y.max()),
                "z_min": int(z.min()), "z_max": int(z.max()),
            },
            "centroid": (float(x.mean()), float(y.mean()), float(z.mean())),
        })
    return props


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Build a small 3-D binary volume (X=5, Y=4, Z=3): volume[x, y, z]
    vol = np.array([
        # X=0
        [[1, 1, 0],
         [1, 0, 0],
         [0, 0, 0],
         [0, 0, 0]],
        # X=1
        [[1, 1, 0],
         [0, 0, 0],
         [0, 0, 0],
         [0, 0, 0]],
        # X=2
        [[0, 0, 0],
         [0, 0, 0],
         [0, 1, 0],
         [0, 1, 0]],
        # X=3
        [[0, 1, 1],
         [1, 1, 1],
         [1, 0, 0],
         [0, 0, 0]],
        # X=4
        [[0, 1, 1],
         [1, 1, 1],
         [0, 0, 0],
         [0, 0, 0]],
    ], dtype=bool)

    print("=== Option A: label_per_slice ===")
    labels_a, n_a = label_per_slice(vol)
    print(f"Found {n_a} regions\n")
    for z in range(vol.shape[2]):
        print(f"  Z={z}:\n{labels_a[:, :, z]}")
    for p in region_properties(labels_a):
        print(p)

    print("\n=== Option B: label_3d_horizontal ===")
    labels_b, n_b = label_3d_horizontal(vol)
    print(f"Found {n_b} regions\n")
    for z in range(vol.shape[2]):
        print(f"  Z={z}:\n{labels_b[:, :, z]}")
    for p in region_properties(labels_b):
        print(p)
