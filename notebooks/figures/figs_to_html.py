"""
figs_to_html.py

Save a list of figures/images into a single HTML file you can click
(or use arrow keys) to page through, like a slideshow.

Supports, per item in the list:
  - matplotlib Figure objects
  - PIL.Image objects
  - file paths (str) to existing image files (png/jpg/etc.)

Usage:
    from figs_to_html import figs_to_html
    figs_to_html([fig1, fig2, fig3], "gallery.html", titles=["A", "B", "C"])
"""

import base64
import io
import os


def _fig_to_base64(item):
    """Convert a single item (matplotlib Figure, PIL Image, or path) to a base64 PNG data URI."""
    # matplotlib Figure
    try:
        from matplotlib.figure import Figure
        if isinstance(item, Figure):
            buf = io.BytesIO()
            item.savefig(buf, format="png", bbox_inches="tight")
            buf.seek(0)
            data = base64.b64encode(buf.read()).decode("utf-8")
            return f"data:image/png;base64,{data}"
    except ImportError:
        pass

    # PIL Image
    try:
        from PIL import Image
        if isinstance(item, Image.Image):
            buf = io.BytesIO()
            item.save(buf, format="PNG")
            buf.seek(0)
            data = base64.b64encode(buf.read()).decode("utf-8")
            return f"data:image/png;base64,{data}"
    except ImportError:
        pass

    # File path
    if isinstance(item, str) and os.path.isfile(item):
        ext = os.path.splitext(item)[1].lstrip(".").lower() or "png"
        mime = "jpeg" if ext in ("jpg", "jpeg") else ext
        with open(item, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        return f"data:image/{mime};base64,{data}"

    raise TypeError(
        f"Unsupported item type for figs_to_html: {type(item)!r}. "
        "Expected a matplotlib Figure, PIL Image, or a valid file path."
    )


def figs_to_html(figs, output_path="figures.html", titles=None):
    """
    Save a list of figures/images to a self-contained, click-through HTML gallery.

    Args:
        figs: list of matplotlib Figures, PIL Images, and/or image file paths.
        output_path: path to write the .html file to.
        titles: optional list of strings, one per figure, shown as a caption.

    Returns:
        The output_path that was written.
    """
    if titles is not None and len(titles) != len(figs):
        raise ValueError("titles must be the same length as figs")

    images_b64 = [_fig_to_base64(f) for f in figs]
    titles = titles or [f"Figure {i + 1}" for i in range(len(figs))]

    slides_js = ",\n".join(f'"{img}"' for img in images_b64)
    titles_js = ",\n".join(
        '"' + t.replace('"', '\\"') + '"' for t in titles
    )

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Figure Gallery</title>
<style>
  body {{
    margin: 0; background: #111; color: #eee;
    font-family: -apple-system, Arial, sans-serif;
    display: flex; flex-direction: column; align-items: center;
    min-height: 100vh; justify-content: center;
  }}
  #view-toggle {{
    position: fixed; top: 16px; right: 16px;
  }}
  #slideshow-view {{
    display: flex; flex-direction: column; align-items: center;
    min-height: 100vh; justify-content: center;
  }}
  #grid-view {{
    display: none; flex-direction: column; align-items: center;
    width: 100%; box-sizing: border-box; padding: 50px 10px 10px;
  }}
  #grid-view.active {{ display: flex; }}
  #slideshow-view.hidden {{ display: none; }}
  #grid {{
    display: grid; gap: 4px; width: 100%; max-width: 100vw;
  }}
  .grid-item {{ cursor: pointer; text-align: center; }}
  .grid-item .grid-img-box {{
    width: 100%; aspect-ratio: 1 / 1; background: #1a1a1a;
    border-radius: 3px; overflow: hidden;
    display: flex; align-items: center; justify-content: center;
    transition: outline 0.1s;
  }}
  .grid-item img {{
    width: 100%; height: 100%; object-fit: contain;
    max-width: none; max-height: none;
  }}
  .grid-item:hover .grid-img-box {{ outline: 2px solid #6cf; }}
  .grid-item .grid-caption {{
    margin-top: 2px; font-size: 11px; color: #ccc;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }}
  #counter {{ margin-bottom: 10px; font-size: 14px; color: #aaa; }}
  #caption {{ margin-bottom: 12px; font-size: 18px; }}
  #imgwrap {{
    flex: 1; display: flex; align-items: center; justify-content: center;
    width: 90vw; max-height: 75vh;
  }}
  img {{
    max-width: 90vw; max-height: 75vh; border-radius: 6px;
    box-shadow: 0 0 20px rgba(0,0,0,0.6);
  }}
  .controls {{ margin-top: 16px; display: flex; gap: 20px; align-items: center; }}
  button {{
    background: #333; color: #eee; border: none; padding: 10px 18px;
    font-size: 16px; border-radius: 6px; cursor: pointer;
  }}
  button:hover {{ background: #555; }}
  button:disabled {{ opacity: 0.3; cursor: default; }}
  #thumbs {{ display: flex; gap: 6px; margin-top: 14px; flex-wrap: wrap; justify-content: center; max-width: 90vw; }}
  #thumbs img {{
    width: 50px; height: 50px; object-fit: cover; border-radius: 4px;
    opacity: 0.5; cursor: pointer; max-height: none; box-shadow: none;
  }}
  #thumbs img.active {{ opacity: 1; outline: 2px solid #6cf; }}
</style>
</head>
<body>
  <div id="view-toggle">
    <button id="toggle-btn">Grid view</button>
  </div>

  <div id="slideshow-view">
    <div id="counter"></div>
    <div id="caption"></div>
    <div id="imgwrap"><img id="main-img" src=""></div>
    <div class="controls">
      <button id="prev-btn">&#8592; Prev</button>
      <button id="next-btn">Next &#8594;</button>
    </div>
    <div id="thumbs"></div>
  </div>

  <div id="grid-view">
    <div id="grid"></div>
  </div>

<script>
  const slides = [
{slides_js}
  ];
  const titles = [
{titles_js}
  ];
  let idx = 0;

  const img = document.getElementById('main-img');
  const counter = document.getElementById('counter');
  const caption = document.getElementById('caption');
  const prevBtn = document.getElementById('prev-btn');
  const nextBtn = document.getElementById('next-btn');
  const thumbs = document.getElementById('thumbs');
  const toggleBtn = document.getElementById('toggle-btn');
  const slideshowView = document.getElementById('slideshow-view');
  const gridView = document.getElementById('grid-view');
  const grid = document.getElementById('grid');
  let gridMode = false;

  slides.forEach((src, i) => {{
    const t = document.createElement('img');
    t.src = src;
    t.addEventListener('click', () => show(i));
    thumbs.appendChild(t);

    const item = document.createElement('div');
    item.className = 'grid-item';
    const box = document.createElement('div');
    box.className = 'grid-img-box';
    const gi = document.createElement('img');
    gi.src = src;
    box.appendChild(gi);
    const gc = document.createElement('div');
    gc.className = 'grid-caption';
    gc.textContent = titles[i];
    item.appendChild(box);
    item.appendChild(gc);
    item.addEventListener('click', () => {{ setGridMode(false); show(i); }});
    grid.appendChild(item);
  }});

  // Lay the grid out as close to a square (rows ~= cols) as possible.
  const cols = Math.ceil(Math.sqrt(slides.length));
  grid.style.gridTemplateColumns = `repeat(${{cols}}, 1fr)`;

  function show(i) {{
    idx = Math.max(0, Math.min(slides.length - 1, i));
    img.src = slides[idx];
    counter.textContent = `${{idx + 1}} / ${{slides.length}}`;
    caption.textContent = titles[idx];
    prevBtn.disabled = idx === 0;
    nextBtn.disabled = idx === slides.length - 1;
    [...thumbs.children].forEach((el, i2) => el.classList.toggle('active', i2 === idx));
  }}

  function setGridMode(on) {{
    gridMode = on;
    gridView.classList.toggle('active', gridMode);
    slideshowView.classList.toggle('hidden', gridMode);
    toggleBtn.textContent = gridMode ? 'Slideshow view' : 'Grid view';
  }}

  toggleBtn.addEventListener('click', () => setGridMode(!gridMode));
  prevBtn.addEventListener('click', () => show(idx - 1));
  nextBtn.addEventListener('click', () => show(idx + 1));
  document.addEventListener('keydown', (e) => {{
    if (gridMode) return;
    if (e.key === 'ArrowLeft') show(idx - 1);
    if (e.key === 'ArrowRight') show(idx + 1);
  }});

  show(0);
</script>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path


if __name__ == "__main__":
    # quick demo with matplotlib if available
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    demo_figs = []
    for i in range(3):
        fig, ax = plt.subplots()
        ax.plot(range(10), [x ** (i + 1) for x in range(10)])
        ax.set_title(f"Demo plot {i + 1}")
        demo_figs.append(fig)

    figs_to_html(demo_figs, "demo_gallery.html", titles=[f"Plot {i+1}" for i in range(3)])
    print("Wrote demo_gallery.html")