"""
cloud_viewer_export.py

Turn a 3D numpy array of cloud volume-extinction coefficients into a single,
self-contained, interactive HTML page. The page renders the volume with a
GPU ray-marching shader (Three.js / WebGL2) and lets the viewer orbit, pan
and zoom a virtual camera around the scene with the mouse / touch.

Typical usage
-------------
    import numpy as np
    from cloud_viewer_export import export_cloud_scene

    # sigma_ext: 3D array of extinction coefficients, shape (nx, ny, nz),
    # units are whatever you used (e.g. 1/km). Axis order is x, y, z with
    # z the vertical axis.
    sigma_ext = ...  # your data, e.g. from a cloud-resolving model / LES

    export_cloud_scene(
        sigma_ext,
        extent=((0, 6.4), (0, 6.4), (0, 3.2)),   # physical size, km
        output_path="cloud_scene.html",
        title="LES Cumulus Field",
    )

Then just open cloud_scene.html in a browser - no server required.

Only dependency is numpy.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

import numpy as np

_TEMPLATE_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>__TITLE__</title>
<style>
  :root {
    --bg: #06080f;
    --panel-bg: rgba(13, 18, 32, 0.82);
    --panel-border: rgba(140, 170, 220, 0.18);
    --ink: #dfe6f2;
    --ink-dim: #8b97ab;
    --accent: #7fb2ff;
    --accent-warm: #ffb37f;
    --mono: "SF Mono", "JetBrains Mono", ui-monospace, Menlo, Consolas, monospace;
    --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Roboto, sans-serif;
  }
  * { box-sizing: border-box; }
  html, body {
    margin: 0; padding: 0; width: 100%; height: 100%;
    background: var(--bg);
    color: var(--ink);
    font-family: var(--sans);
    overflow: hidden;
  }
  #canvas-wrap { position: fixed; inset: 0; }
  canvas { display: block; width: 100%; height: 100%; touch-action: none; }

  #header {
    position: fixed; top: 0; left: 0; right: 0;
    padding: 18px 22px 10px;
    pointer-events: none;
    background: linear-gradient(to bottom, rgba(6,8,15,0.75), transparent);
    z-index: 5;
  }
  #header h1 {
    margin: 0; font-size: 15px; font-weight: 600; letter-spacing: 0.02em;
    color: var(--ink);
  }
  #header .sub {
    margin-top: 3px; font-size: 11.5px; color: var(--ink-dim);
    font-family: var(--mono); letter-spacing: 0.01em;
  }

  #panel {
    position: fixed; left: 18px; bottom: 18px;
    width: 268px;
    background: var(--panel-bg);
    border: 1px solid var(--panel-border);
    border-radius: 10px;
    padding: 14px 16px 16px;
    backdrop-filter: blur(10px);
    z-index: 10;
    font-size: 12.5px;
  }
  #panel h2 {
    margin: 0 0 10px; font-size: 10.5px; text-transform: uppercase;
    letter-spacing: 0.09em; color: var(--ink-dim); font-weight: 600;
  }
  .row { margin-bottom: 11px; }
  .row:last-child { margin-bottom: 0; }
  .row label {
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 4px; color: var(--ink); font-size: 12px;
  }
  .row label span.val { color: var(--accent); font-family: var(--mono); font-size: 11.5px; }
  input[type="range"] {
    width: 100%; height: 3px; -webkit-appearance: none; appearance: none;
    background: rgba(140,170,220,0.22); border-radius: 3px; outline: none;
  }
  input[type="range"]::-webkit-slider-thumb {
    -webkit-appearance: none; width: 13px; height: 13px; border-radius: 50%;
    background: var(--accent); cursor: pointer; box-shadow: 0 0 6px rgba(127,178,255,0.7);
  }
  input[type="range"]::-moz-range-thumb {
    width: 13px; height: 13px; border-radius: 50%; border: none;
    background: var(--accent); cursor: pointer;
  }
  select {
    width: 100%; background: rgba(140,170,220,0.10); color: var(--ink);
    border: 1px solid var(--panel-border); border-radius: 6px; padding: 5px 8px;
    font-size: 12px; font-family: var(--sans);
  }
  .toggle-row { display: flex; gap: 8px; }
  .toggle-btn {
    flex: 1; padding: 6px 4px; text-align: center; border-radius: 6px;
    border: 1px solid var(--panel-border); background: rgba(140,170,220,0.06);
    color: var(--ink-dim); font-size: 11px; cursor: pointer; user-select: none;
    transition: all 0.12s ease;
  }
  .toggle-btn.active { background: rgba(127,178,255,0.18); color: var(--accent); border-color: rgba(127,178,255,0.4); }
  .toggle-btn:hover { color: var(--ink); }
  hr.div { border: none; border-top: 1px solid var(--panel-border); margin: 12px 0; }
  #reset-btn {
    width: 100%; padding: 7px; border-radius: 6px; border: 1px solid var(--panel-border);
    background: rgba(140,170,220,0.06); color: var(--ink); font-size: 11.5px; cursor: pointer;
  }
  #reset-btn:hover { background: rgba(140,170,220,0.14); }

  #info {
    position: fixed; right: 18px; bottom: 18px;
    text-align: right; font-family: var(--mono); font-size: 10.5px;
    color: var(--ink-dim); line-height: 1.6; z-index: 10;
    pointer-events: none;
  }
  #info b { color: var(--ink); font-weight: 500; }

  #hint {
    position: fixed; top: 18px; right: 22px; z-index: 10;
    font-size: 11px; color: var(--ink-dim); text-align: right; line-height: 1.6;
    pointer-events: none;
  }

  #loading {
    position: fixed; inset: 0; display: flex; align-items: center; justify-content: center;
    background: var(--bg); z-index: 100; color: var(--ink-dim); font-size: 12.5px;
    font-family: var(--mono); letter-spacing: 0.02em;
  }
</style>
</head>
<body>

<div id="loading">building volume texture&hellip;</div>

<div id="canvas-wrap"></div>

<div id="header">
  <h1 id="title-text"></h1>
  <div class="sub" id="subtitle-text"></div>
</div>

<div id="hint">drag &mdash; rotate &nbsp;&middot;&nbsp; scroll &mdash; zoom<br/>right-drag / two-finger &mdash; pan</div>

<div id="panel">
  <h2>Render</h2>
  <div class="row">
    <label>Density <span class="val" id="densityVal">1.00&times;</span></label>
    <input type="range" id="density" min="0.05" max="6" step="0.01" value="1.0" />
  </div>
  <div class="row">
    <label>Quality (steps) <span class="val" id="stepsVal">128</span></label>
    <input type="range" id="steps" min="32" max="256" step="8" value="128" />
  </div>
  <div class="row">
    <label>Light mix <span class="val" id="lightVal">0.55</span></label>
    <input type="range" id="lightmix" min="0" max="1" step="0.01" value="0.55" />
  </div>
  <div class="row">
    <label>Colormap</label>
    <select id="colormap">
      <option value="0">Cloud (natural)</option>
      <option value="1">Fire (structure)</option>
      <option value="2">Viridis (scientific)</option>
    </select>
  </div>
  <hr class="div" />
  <div class="row">
    <label style="margin-bottom:6px;">Scene</label>
    <div class="toggle-row">
      <div class="toggle-btn active" id="toggle-box">Bounding box</div>
      <div class="toggle-btn" id="toggle-sky">Sky bg</div>
    </div>
  </div>
  <div class="row" style="margin-top:10px;">
    <button id="reset-btn">Reset camera</button>
  </div>
</div>

<div id="info"></div>

<script type="importmap">
{
  "imports": {
    "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
    "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"
  }
}
</script>

<script type="module">
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const META = __META_JSON__;
const VOLUME_B64 = "__VOLUME_B64__";

document.getElementById("title-text").textContent = META.title;
document.getElementById("subtitle-text").textContent =
  `${META.dims[0]}\u00d7${META.dims[1]}\u00d7${META.dims[2]} volume \u00b7 ` +
  `max extinction ${META.maxExtinction.toFixed(2)}`;
document.getElementById("info").innerHTML =
  `<b>${META.axisLabels[0]}</b> ${META.extent.xmin.toFixed(2)} \u2192 ${META.extent.xmax.toFixed(2)}<br/>` +
  `<b>${META.axisLabels[1]}</b> ${META.extent.ymin.toFixed(2)} \u2192 ${META.extent.ymax.toFixed(2)}<br/>` +
  `<b>${META.axisLabels[2]}</b> ${META.extent.zmin.toFixed(2)} \u2192 ${META.extent.zmax.toFixed(2)}`;

// ---- decode embedded volume ----
function base64ToUint8(b64) {
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
}
const [NX, NY, NZ] = META.dims;
const volBytes = base64ToUint8(VOLUME_B64); // ordered [z][y][x]

// ---- renderer / scene / camera ----
const wrap = document.getElementById("canvas-wrap");
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
wrap.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const skyDark = new THREE.Color(0x06080f);
const skyLight = new THREE.Color(0x9fc3e8);
scene.background = skyDark.clone();

const sizeX = META.extent.sizeX, sizeY = META.extent.sizeY, sizeZ = META.extent.sizeZ;
const diag = Math.sqrt(sizeX * sizeX + sizeY * sizeY + sizeZ * sizeZ);

const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, diag / 2000, diag * 20);
const startPos = new THREE.Vector3(diag * 0.85, diag * 0.55, diag * 0.9);
camera.position.copy(startPos);

const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 0, 0);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.minDistance = diag * 0.05;
controls.maxDistance = diag * 8;
controls.update();

// ---- 3D texture ----
const texture = new THREE.Data3DTexture(volBytes, NX, NY, NZ);
texture.format = THREE.RedFormat;
texture.type = THREE.UnsignedByteType;
texture.minFilter = THREE.LinearFilter;
texture.magFilter = THREE.LinearFilter;
texture.wrapS = THREE.ClampToEdgeWrapping;
texture.wrapT = THREE.ClampToEdgeWrapping;
texture.wrapR = THREE.ClampToEdgeWrapping;
texture.unpackAlignment = 1;
texture.needsUpdate = true;

// ---- shader ----
const vertexShader = `
  out vec3 vWorldPos;
  void main() {
    vec4 wp = modelMatrix * vec4(position, 1.0);
    vWorldPos = wp.xyz;
    gl_Position = projectionMatrix * viewMatrix * wp;
  }
`;

const fragmentShader = `
  precision highp float;
  precision highp sampler3D;

  in vec3 vWorldPos;

  uniform sampler3D uVolume;
  uniform vec3 uBoxSize;
  uniform vec3 uCameraPos;
  uniform float uDensityMul;
  uniform float uMaxExtinction;
  uniform int uSteps;
  uniform float uLightMix;
  uniform int uColormap;

  vec3 cloudColor(float d) {
    vec3 shadow = vec3(0.42, 0.47, 0.58);
    vec3 lit = vec3(1.0, 0.99, 0.97);
    return mix(shadow, lit, pow(clamp(d, 0.0, 1.0), 0.45));
  }
  vec3 fireColor(float d) {
    vec3 c1 = vec3(0.03, 0.0, 0.02);
    vec3 c2 = vec3(0.65, 0.06, 0.0);
    vec3 c3 = vec3(1.0, 0.55, 0.0);
    vec3 c4 = vec3(1.0, 0.96, 0.75);
    float t = clamp(d, 0.0, 1.0);
    vec3 col = mix(c1, c2, smoothstep(0.0, 0.32, t));
    col = mix(col, c3, smoothstep(0.28, 0.66, t));
    col = mix(col, c4, smoothstep(0.62, 1.0, t));
    return col;
  }
  vec3 viridisColor(float d) {
    vec3 c0 = vec3(0.267, 0.005, 0.329);
    vec3 c1 = vec3(0.283, 0.141, 0.458);
    vec3 c2 = vec3(0.254, 0.265, 0.530);
    vec3 c3 = vec3(0.207, 0.372, 0.553);
    vec3 c4 = vec3(0.164, 0.471, 0.558);
    vec3 c5 = vec3(0.128, 0.567, 0.551);
    vec3 c6 = vec3(0.135, 0.659, 0.518);
    vec3 c7 = vec3(0.267, 0.749, 0.441);
    vec3 c8 = vec3(0.478, 0.821, 0.318);
    vec3 c9 = vec3(0.741, 0.873, 0.150);
    vec3 c10 = vec3(0.993, 0.906, 0.144);
    float t = clamp(d, 0.0, 1.0) * 10.0;
    float f = fract(t);
    int i = int(floor(t));
    vec3 a, b;
    if (i <= 0) { a = c0; b = c1; }
    else if (i == 1) { a = c1; b = c2; }
    else if (i == 2) { a = c2; b = c3; }
    else if (i == 3) { a = c3; b = c4; }
    else if (i == 4) { a = c4; b = c5; }
    else if (i == 5) { a = c5; b = c6; }
    else if (i == 6) { a = c6; b = c7; }
    else if (i == 7) { a = c7; b = c8; }
    else if (i == 8) { a = c8; b = c9; }
    else { a = c9; b = c10; }
    return mix(a, b, f);
  }
  vec3 shade(float d) {
    if (uColormap == 1) return fireColor(d);
    if (uColormap == 2) return viridisColor(d);
    return cloudColor(d);
  }

  // ray vs axis-aligned box centered at origin, half-extent uBoxSize/2
  vec2 intersectBox(vec3 ro, vec3 rd) {
    vec3 half = uBoxSize * 0.5;
    vec3 invRd = 1.0 / rd;
    vec3 t0 = (-half - ro) * invRd;
    vec3 t1 = (half - ro) * invRd;
    vec3 tmin = min(t0, t1);
    vec3 tmax = max(t0, t1);
    float tNear = max(max(tmin.x, tmin.y), tmin.z);
    float tFar = min(min(tmax.x, tmax.y), tmax.z);
    return vec2(tNear, tFar);
  }

  void main() {
    vec3 rd = normalize(vWorldPos - uCameraPos);
    vec3 ro = uCameraPos;

    vec2 tHit = intersectBox(ro, rd);
    float tNear = max(tHit.x, 0.0);
    float tFar = tHit.y;
    if (tFar <= tNear) { discard; }

    float dist = tFar - tNear;
    float dt = dist / float(uSteps);

    // ambient light: cool from below/behind, warm key light from above-front
    vec3 ambientCool = vec3(0.35, 0.40, 0.52);
    vec3 keyWarm = vec3(1.0, 0.94, 0.86);

    float transmittance = 1.0;
    vec3 radiance = vec3(0.0);

    vec3 half = uBoxSize * 0.5;

    for (int i = 0; i < 256; i++) {
      if (i >= uSteps) break;
      float t = tNear + (float(i) + 0.5) * dt;
      if (t > tFar) break;
      vec3 pos = ro + rd * t;
      vec3 uvw = (pos + half) / uBoxSize;

      float sample_ = texture(uVolume, uvw).r;
      float sigma = sample_ * uMaxExtinction * uDensityMul * 0.35;
      if (sigma <= 0.0001) continue;

      float stepOD = sigma * dt;
      float stepAlpha = 1.0 - exp(-stepOD);

      float heightFrac = clamp(uvw.z, 0.0, 1.0);
      vec3 lightColor = mix(ambientCool, keyWarm, uLightMix * heightFrac + (1.0 - uLightMix) * 0.5);
      vec3 col = shade(sample_) * lightColor;

      radiance += transmittance * stepAlpha * col;
      transmittance *= (1.0 - stepAlpha);

      if (transmittance < 0.003) break;
    }

    if (radiance.r + radiance.g + radiance.b < 0.0005 && transmittance > 0.999) discard;

    gl_FragColor = vec4(radiance, 1.0 - transmittance);
  }
`;

const uniforms = {
  uVolume: { value: texture },
  uBoxSize: { value: new THREE.Vector3(sizeX, sizeY, sizeZ) },
  uCameraPos: { value: camera.position.clone() },
  uDensityMul: { value: 1.0 },
  uMaxExtinction: { value: META.maxExtinction },
  uSteps: { value: 128 },
  uLightMix: { value: 0.55 },
  uColormap: { value: 0 },
};

const material = new THREE.ShaderMaterial({
  glslVersion: THREE.GLSL3,
  uniforms,
  vertexShader,
  fragmentShader,
  transparent: true,
  side: THREE.BackSide,
  depthWrite: false,
});

const geometry = new THREE.BoxGeometry(sizeX, sizeY, sizeZ);
const volumeMesh = new THREE.Mesh(geometry, material);
scene.add(volumeMesh);

// ---- bounding box wireframe ----
const edgesGeo = new THREE.EdgesGeometry(geometry);
const edgesMat = new THREE.LineBasicMaterial({ color: 0x7fb2ff, transparent: true, opacity: 0.35 });
const boxHelper = new THREE.LineSegments(edgesGeo, edgesMat);
scene.add(boxHelper);

// ---- UI wiring ----
const densitySlider = document.getElementById("density");
const densityVal = document.getElementById("densityVal");
densitySlider.addEventListener("input", () => {
  uniforms.uDensityMul.value = parseFloat(densitySlider.value);
  densityVal.textContent = parseFloat(densitySlider.value).toFixed(2) + "\u00d7";
});

const stepsSlider = document.getElementById("steps");
const stepsVal = document.getElementById("stepsVal");
stepsSlider.addEventListener("input", () => {
  uniforms.uSteps.value = parseInt(stepsSlider.value, 10);
  stepsVal.textContent = stepsSlider.value;
});

const lightSlider = document.getElementById("lightmix");
const lightVal = document.getElementById("lightVal");
lightSlider.addEventListener("input", () => {
  uniforms.uLightMix.value = parseFloat(lightSlider.value);
  lightVal.textContent = parseFloat(lightSlider.value).toFixed(2);
});

document.getElementById("colormap").addEventListener("change", (e) => {
  uniforms.uColormap.value = parseInt(e.target.value, 10);
});

const boxToggle = document.getElementById("toggle-box");
boxToggle.addEventListener("click", () => {
  boxHelper.visible = !boxHelper.visible;
  boxToggle.classList.toggle("active", boxHelper.visible);
});

const skyToggle = document.getElementById("toggle-sky");
let skyOn = false;
skyToggle.addEventListener("click", () => {
  skyOn = !skyOn;
  scene.background = (skyOn ? skyLight : skyDark).clone();
  skyToggle.classList.toggle("active", skyOn);
});

document.getElementById("reset-btn").addEventListener("click", () => {
  camera.position.copy(startPos);
  controls.target.set(0, 0, 0);
  controls.update();
});

// apply default select value for the colormap set in META
const cmSelect = document.getElementById("colormap");
const cmIndex = { cloud: "0", fire: "1", viridis: "2" }[META.colormap] ?? "0";
cmSelect.value = cmIndex;
uniforms.uColormap.value = parseInt(cmIndex, 10);

// ---- resize ----
window.addEventListener("resize", () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

// ---- render loop ----
function animate() {
  requestAnimationFrame(animate);
  controls.update();
  uniforms.uCameraPos.value.copy(camera.position);
  renderer.render(scene, camera);
}

document.getElementById("loading").style.display = "none";
animate();
</script>
</body>
</html>
"""


def export_cloud_scene(
    sigma_ext: np.ndarray,
    extent: tuple[tuple[float, float], tuple[float, float], tuple[float, float]] = (
        (0.0, 1.0),
        (0.0, 1.0),
        (0.0, 1.0),
    ),
    output_path: str | Path = "cloud_scene.html",
    title: str = "Cloud Extinction Volume",
    axis_labels: tuple[str, str, str] = ("x (km)", "y (km)", "z (km)"),
    colormap: str = "cloud",
) -> Path:
    """
    Export a 3D extinction-coefficient field to a self-contained interactive
    HTML viewer.

    Parameters
    ----------
    sigma_ext : np.ndarray, shape (nx, ny, nz)
        Volume extinction coefficient. Any non-negative units are fine
        (e.g. 1/km, 1/m); the value range found in the array is used to
        calibrate the optical-depth scaling in the shader, and is also
        exposed as a "density" slider in the page so the viewer can adjust
        the look interactively.
    extent : ((xmin,xmax), (ymin,ymax), (zmin,zmax))
        Physical extent of the volume, used for axes / bounding box labels
        and to keep the aspect ratio of the rendered box correct.
    output_path : str or Path
        Where to write the .html file.
    title : str
        Page title / heading shown in the viewer.
    axis_labels : (str, str, str)
        Labels for the x, y, z axes shown in the UI.
    colormap : {"cloud", "fire", "viridis"}
        Coloring scheme used to shade the volume.

    Returns
    -------
    Path to the written HTML file.
    """
    if sigma_ext.ndim != 3:
        raise ValueError(f"sigma_ext must be a 3D array, got shape {sigma_ext.shape}")

    nx, ny, nz = sigma_ext.shape
    if nx > 256 or ny > 256 or nz > 256:
        raise ValueError(
            "Volume is too large to embed directly (max 256 per axis). "
            "Downsample first, e.g. sigma_ext[::2, ::2, ::2]."
        )

    vol = np.asarray(sigma_ext, dtype=np.float32)
    vol = np.nan_to_num(vol, nan=0.0, posinf=0.0, neginf=0.0)
    vol = np.clip(vol, 0.0, None)

    max_val = float(vol.max())
    if max_val <= 0:
        raise ValueError("sigma_ext is all zeros; nothing to render.")

    # Quantize to 8-bit for compact embedding. The shader multiplies the
    # normalized [0,1] sample back up by max_val (passed in as a uniform)
    # and then by a user-controlled density slider, so this doesn't lose
    # meaningful dynamic range for visualization purposes.
    normalized = vol / max_val
    quantized = np.round(normalized * 255.0).astype(np.uint8)

    # WebGL 3D textures are indexed [z][y][x] (z-major/slowest) in the flat
    # buffer we upload, so reorder axes accordingly before flattening.
    tex_data = np.transpose(quantized, (2, 1, 0)).copy()  # (nz, ny, nx)
    raw_bytes = tex_data.tobytes(order="C")
    b64_data = base64.b64encode(raw_bytes).decode("ascii")

    (xmin, xmax), (ymin, ymax), (zmin, zmax) = extent
    size_x, size_y, size_z = xmax - xmin, ymax - ymin, zmax - zmin

    meta = {
        "dims": [int(nx), int(ny), int(nz)],
        "extent": {
            "xmin": xmin, "xmax": xmax,
            "ymin": ymin, "ymax": ymax,
            "zmin": zmin, "zmax": zmax,
            "sizeX": size_x, "sizeY": size_y, "sizeZ": size_z,
        },
        "maxExtinction": max_val,
        "axisLabels": list(axis_labels),
        "title": title,
        "colormap": colormap,
    }

    html = (
        _TEMPLATE_HTML
        .replace("__TITLE__", json.dumps(title))
        .replace("__META_JSON__", json.dumps(meta))
        .replace("__VOLUME_B64__", b64_data)
    )

    output_path = Path(output_path)
    output_path.write_text(html, encoding="utf-8")
    return output_path


def generate_synthetic_cloud(
    shape: tuple[int, int, int] = (64, 64, 40),
    seed: int = 0,
    spectral_slope: float = 3.0,
    threshold: float = 0.42,
    softness: float = 0.18,
    vertical_center: float = 0.45,
    vertical_spread: float = 0.16,
    max_extinction: float = 40.0,
) -> np.ndarray:
    """
    Build a synthetic, physically-plausible-looking cumulus-style cloud
    field for demos and testing, using spectral (Fourier-filtered) noise
    shaped by a vertical envelope so the field looks like a puffy cloud
    layer rather than uniform static.

    Returns an array of shape `shape` with values in [0, max_extinction],
    representing a volume extinction coefficient (arbitrary units, e.g. 1/km).
    """
    rng = np.random.default_rng(seed)
    nx, ny, nz = shape

    noise = rng.normal(size=shape)
    fft = np.fft.fftn(noise)

    kx = np.fft.fftfreq(nx)[:, None, None]
    ky = np.fft.fftfreq(ny)[None, :, None]
    kz = np.fft.fftfreq(nz)[None, None, :]
    k = np.sqrt(kx**2 + ky**2 + kz**2)
    k[0, 0, 0] = k[k > 0].min()  # avoid divide-by-zero at DC

    spectral_filter = 1.0 / np.power(k, spectral_slope)
    field = np.fft.ifftn(fft * spectral_filter).real

    field -= field.min()
    field /= field.max()

    z = np.linspace(0.0, 1.0, nz)
    envelope = np.exp(-((z - vertical_center) ** 2) / (2 * vertical_spread**2))
    field *= envelope[None, None, :]

    field -= field.min()
    field /= max(field.max(), 1e-8)

    density = np.clip((field - threshold) / softness, 0.0, 1.0)
    density = density**1.5  # sharpen cloud edges a bit

    return (density * max_extinction).astype(np.float32)


if __name__ == "__main__":
    # Quick self-test / demo: generate a synthetic cloud field and export it.
    cloud = generate_synthetic_cloud(shape=(72, 72, 44), seed=3)
    out = export_cloud_scene(
        cloud,
        extent=((0, 7.2), (0, 7.2), (0, 4.4)),
        output_path="cloud_scene_demo.html",
        title="Synthetic Cumulus Field \u2014 Extinction Coefficient",
    )
    print(f"Wrote {out} ({out.stat().st_size / 1e6:.2f} MB)")
