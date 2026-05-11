const TERRAIN = { // placeholder values
  OCEAN:    { top: [0.22, 0.53, 0.85], side: [0.13, 0.36, 0.64], h: 0.12 },
  PLAINS:   { top: [0.62, 0.82, 0.41], side: [0.44, 0.60, 0.26], h: 0.20 },
  GRASS:    { top: [0.30, 0.67, 0.22], side: [0.18, 0.46, 0.13], h: 0.26 },
  FOREST:   { top: [0.14, 0.42, 0.14], side: [0.08, 0.28, 0.07], h: 0.68 },
  HILLS:    { top: [0.68, 0.58, 0.38], side: [0.50, 0.42, 0.24], h: 0.50 },
  MOUNTAIN: { top: [0.80, 0.76, 0.72], side: [0.58, 0.54, 0.50], h: 1.00 },
  DESERT:   { top: [0.88, 0.78, 0.52], side: [0.68, 0.58, 0.36], h: 0.18 },
  TUNDRA:   { top: [0.86, 0.90, 0.94], side: [0.66, 0.70, 0.74], h: 0.22 },
};

const GRID_SIZE  = 18;
const TILE_SIZE  = 1.0;
const TILE_GAP   = 0.06;
const T          = TILE_SIZE - TILE_GAP; // effective tile footprint

function main() {
  const canvas = document.querySelector("#glCanvas");
  const gl = canvas.getContext("webgl2", {
    antialias:    true,
    depth:        true,
    powerPreference: "high-performance",
  });

  if (!gl) {
    const msg = document.createElement("p");
    msg.style.cssText = "color: black";
    msg.textContent = "WebGL2 not available";
    canvas.parentNode.insertAdjacentElement("afterend", msg);
    return;
  }

  const vsSource = `#version 300 es 
    // Modern syntax 

    // Tell GPU where it is
    layout(location = 0) in vec3 aPosition;
    layout(location = 1) in vec4 aColor;

    uniform mat4 uModelMatrix;      // Actual Model rotation, position, etc. Just one now extend to many later
    uniform mat4 uViewMatrix;       // Position of camera in world (3d world relative to camera)
    uniform mat4 uProjectionMatrix; // Actual field of objects through camera -> screen (clip space)

    out vec4 vColor;  // passed to fragment shader

    void main() {
      // Order must be Projection * View * Model (right to left).
      gl_Position = uProjectionMatrix * uViewMatrix * uModelMatrix * vec4(aPosition, 1.0);
      vColor = aColor;
    }
  `;

  const fsSource = `#version 300 es
    precision mediump float; // float16 (?) precision. Balance effiency and detail

    in vec4 vColor; // Apply gradient or smoothing
    out vec4 fragColor;

    void main() {
      fragColor = vColor;
    }
  `;

  const program = initShaderProgram(gl, vsSource, fsSource);
  if (!program) return;

  const uModelMatrix      = gl.getUniformLocation(program, "uModelMatrix");
  const uViewMatrix       = gl.getUniformLocation(program, "uViewMatrix");
  const uProjectionMatrix = gl.getUniformLocation(program, "uProjectionMatrix");

  const projection = mat4.create();
  mat4.perspective(
    projection,
    (55.0 * Math.PI) / 180.0, // 55 degrees above azimuth
    canvas.width / canvas.height, // use canvas pixel dims, not CSS dims (avoids 0 if not laid out yet)
    0.1,   // near clip plane
    200.0, // far clip plane
  );

  const halfGrid = (GRID_SIZE * TILE_SIZE) / 2;
  const cam = {
    target:    [halfGrid, 0, halfGrid],  // face towards map center
    azimuth:   Math.PI * 0.3, // start horizontal angle
    elevation: 0.72, // some degree above horizon
    radius:    22, // start zoom distance
    // Constraints (tuned)
    elevMin: 0.15,
    elevMax: 1.45,
    radMin:  5,
    radMax:  55,
  };

  gl.enable(gl.DEPTH_TEST); // Check depth buffer
  gl.enable(gl.CULL_FACE);  // Backface culling

  const tileMap = buildMap(GRID_SIZE);
  const scene = [];
  for (let row = 0; row < GRID_SIZE; row++) {
    for (let col = 0; col < GRID_SIZE; col++) {
      const terrain = tileMap[row][col];
      scene.push(makeTile(gl, {
        x: col * TILE_SIZE,
        z: row * TILE_SIZE,
        w: T, d: T,
        h: terrain.h,
        top:  terrain.top,
        side: terrain.side,
      }));
    }
  }

  // Ground plane so tiles have something to sit on
  const groundSize = GRID_SIZE * TILE_SIZE + 2;
  scene.push(makeTile(gl, {
    x: -1, z: -1, w: groundSize, d: groundSize, h: 0.04,
    top:  [0.06, 0.08, 0.10],
    side: [0.04, 0.06, 0.08],
  }));

  // model matrix for units later
  const modelMatrix = mat4.create(); // mat4.create() returns an identity matrix

  function render() {
    const view = buildViewMatrix(cam);
    gl.clearColor(0.04, 0.05, 0.08, 1.0); // polytopia bg
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);

    gl.useProgram(program);

    gl.uniformMatrix4fv(uModelMatrix,      false, modelMatrix);
    gl.uniformMatrix4fv(uViewMatrix,       false, view);
    gl.uniformMatrix4fv(uProjectionMatrix, false, projection);

    for (const { vao, indexCount } of scene) {
      gl.bindVertexArray(vao);
      gl.drawElements(gl.TRIANGLES, indexCount, gl.UNSIGNED_SHORT, 0);
    }
    gl.bindVertexArray(null);

    requestAnimationFrame(render);
  }

  requestAnimationFrame(render);

  // Controls
  let drag = { active: false, button: -1, lastX: 0, lastY: 0 };

  canvas.addEventListener("contextmenu", e => e.preventDefault());

  canvas.addEventListener("mousedown", e => {
    if (e.button === 2 || e.button === 1) {
      drag = { active: true, button: e.button, lastX: e.clientX, lastY: e.clientY };
      canvas.classList.add("orbiting");
      e.preventDefault();
    }
  });

  window.addEventListener("mouseup", e => {
    if (drag.active && e.button === drag.button) {
      drag.active = false;
      canvas.classList.remove("orbiting");
    }
  });

  window.addEventListener("mousemove", e => {
    if (!drag.active) return;
    const dx = e.clientX - drag.lastX;
    const dy = e.clientY - drag.lastY;
    drag.lastX = e.clientX;
    drag.lastY = e.clientY;

    if (drag.button === 2) {
      // Orbit: dx -> azimuth, dy -> elevation
      cam.azimuth   -= dx * 0.007;
      cam.elevation += dy * 0.007;
      cam.elevation  = Math.max(cam.elevMin, Math.min(cam.elevMax, cam.elevation));
    } else if (drag.button === 1) {
      // Pan
      const panSpeed = cam.radius * 0.0015;
      const az = cam.azimuth;
      cam.target[0] += Math.cos(az) * dx * panSpeed;
      cam.target[2] -= Math.sin(az) * dx * panSpeed;
      cam.target[0] -= Math.sin(az) * dy * panSpeed;
      cam.target[2] -= Math.cos(az) * dy * panSpeed;
    }
  });

  canvas.addEventListener("wheel", e => {
    // Exponential zoom so it feels consistent near and far
    cam.radius *= 1 + e.deltaY * 0.001;
    cam.radius  = Math.max(cam.radMin, Math.min(cam.radMax, cam.radius));
    e.preventDefault();
  }, { passive: false });
}

// GPU buffers for one tile
// prettier-ignore
// Yes I use this extension
function makeTile(gl, { x, z, w, d, h, top, side }) {
  const x1 = x, x2 = x + w;
  const y1 = 0, y2 = h;
  const z1 = z, z2 = z + d;

  const [tr, tg, tb] = top;
  const [sr, sg, sb] = side;

  // Face brightness multipliers — directional light without shader
  // WILL ADD DIFFUSE MODEL LATER (?)
  const FRONT  = 0.90;  // z+ face (facing camera at start)
  const BACK   = 0.70;  // z- face
  const LEFT   = 0.80;  // x- face
  const RIGHT  = 0.80;  // x+ face

  // 20 vertices x 7 floats each (no need for face on bottom)
  const verts = new Float32Array([
    // Top face   (y2): bright
    x1, y2, z1,   tr,       tg,       tb,       1.0,  // 0
    x2, y2, z1,   tr,       tg,       tb,       1.0,  // 1
    x2, y2, z2,   tr,       tg,       tb,       1.0,  // 2
    x1, y2, z2,   tr,       tg,       tb,       1.0,  // 3

    // Front face (z2): medium bright
    x1, y1, z2,   sr*FRONT, sg*FRONT, sb*FRONT, 1.0,  // 4
    x2, y1, z2,   sr*FRONT, sg*FRONT, sb*FRONT, 1.0,  // 5
    x2, y2, z2,   sr*FRONT, sg*FRONT, sb*FRONT, 1.0,  // 6
    x1, y2, z2,   sr*FRONT, sg*FRONT, sb*FRONT, 1.0,  // 7

    // Back face  (z1): darkest
    x2, y1, z1,   sr*BACK,  sg*BACK,  sb*BACK,  1.0,  // 8
    x1, y1, z1,   sr*BACK,  sg*BACK,  sb*BACK,  1.0,  // 9
    x1, y2, z1,   sr*BACK,  sg*BACK,  sb*BACK,  1.0,  // 10
    x2, y2, z1,   sr*BACK,  sg*BACK,  sb*BACK,  1.0,  // 11

    // Left face  (x1): medium
    x1, y1, z1,   sr*LEFT,  sg*LEFT,  sb*LEFT,  1.0,  // 12
    x1, y1, z2,   sr*LEFT,  sg*LEFT,  sb*LEFT,  1.0,  // 13
    x1, y2, z2,   sr*LEFT,  sg*LEFT,  sb*LEFT,  1.0,  // 14
    x1, y2, z1,   sr*LEFT,  sg*LEFT,  sb*LEFT,  1.0,  // 15

    // Right face (x2): medium
    x2, y1, z2,   sr*RIGHT, sg*RIGHT, sb*RIGHT, 1.0,  // 16
    x2, y1, z1,   sr*RIGHT, sg*RIGHT, sb*RIGHT, 1.0,  // 17
    x2, y2, z1,   sr*RIGHT, sg*RIGHT, sb*RIGHT, 1.0,  // 18
    x2, y2, z2,   sr*RIGHT, sg*RIGHT, sb*RIGHT, 1.0,  // 19
  ]);

  // 5 faces x 2 triangles x 3 indices = 30 indicies
  // Just draw this out
  // Extra note: Tell GPU to use CCW or else faces dissapear cuz culling removes CC order
  const indices = new Uint16Array([
     0,  3,  2,   0,  2,  1,  // top     (CCW looking down)
     4,  5,  6,   4,  6,  7,  // front   (CCW looking toward +Z)
     8,  9, 10,   8, 10, 11,  // back    (CCW looking toward -Z)
    12, 13, 14,  12, 14, 15,  // left    (CCW looking toward -X)
    16, 17, 18,  16, 18, 19,  // right   (CCW looking toward +X)
  ]);

  // Tell GPU how to read vertex buffer
  const FLOATS_PER_VERT = 7;
  const BYTES_PER_FLOAT = 4;
  const STRIDE = FLOATS_PER_VERT * BYTES_PER_FLOAT; // 28 bytes

  // Vertex Array Object
  // GPU record of which buffer holds vertex data, how attributes map onto the buffers, and which index buffer is active
  // Basically instructions for short
  const vao = gl.createVertexArray();
  gl.bindVertexArray(vao);

  // Vertex Buffer Object
  // Actually data storage
  const vbo = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
  gl.bufferData(gl.ARRAY_BUFFER, verts, gl.STATIC_DRAW); // Make animated later maybe (?)

  // aPostion in slot 0: 3 floats, stride=28, offset=0
  gl.vertexAttribPointer(0, 3, gl.FLOAT, false, STRIDE, 0);
  gl.enableVertexAttribArray(0);

  // aColor in slot 1: 4 floats, stride=28, offset=12
  gl.vertexAttribPointer(1, 4, gl.FLOAT, false, STRIDE, 3 * BYTES_PER_FLOAT);
  gl.enableVertexAttribArray(1);

  // Same for element (index) buffer
  const ebo = gl.createBuffer();
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ebo);
  gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, indices, gl.STATIC_DRAW);

  gl.bindVertexArray(null); // End VAO instructions

  return { vao, indexCount: indices.length };
}

function buildViewMatrix(cam) {
  const { radius, azimuth, elevation, target } = cam;
  const cosEl = Math.cos(elevation);

  // Spherical shape transforms
  const eye = [
    target[0] + radius * cosEl * Math.sin(azimuth),
    target[1] + radius * Math.sin(elevation),
    target[2] + radius * cosEl * Math.cos(azimuth),
  ];

  const view = mat4.create();
  // invert the camera transform (moves the world not camera)
  mat4.lookAt(view, eye, target, [0, 1, 0]);
  return view;
}

// Converts tile coords into random float with range [0, 1] for smooth noise later
// CHANGE CHANGE LATER
function hash2(ix, iy) {
  const s = Math.sin(ix * 127.1 + iy * 311.7) * 43758.5453; // prime ish units
  return s - Math.floor(s);
}

// Smooth noise function to blend terrain
function smoothNoise(x, y) {
  const ix = Math.floor(x);
  const iy = Math.floor(y);
  const fx = x - ix;
  const fy = y - iy;

  // This is to remove linear interpolation artefacts
  // f(x) = 3t^2 - 2t^3
  const ux = fx * fx * (3 - 2 * fx);
  const uy = fy * fy * (3 - 2 * fy);

  const a = hash2(ix, iy);
  const b = hash2(ix+1, iy);
  const c = hash2(ix, iy+1);
  const d = hash2(ix+1, iy+1);

  return a + (b - a) * ux + (c - a) * uy + (d - b - c + a) * ux * uy;
}

// Fractional Brownian Motion, replace with scipy Perlin later
function fbm(x, y, octaves = 5) {
  let value = 0, amplitude = 0.5, frequency = 1.0;
  for (let i = 0; i < octaves; i++) {
    value     += smoothNoise(x * frequency, y * frequency) * amplitude;
    amplitude *= 0.5;
    frequency *= 2.0;
  }
  return value; // [0, 1] range
}

// Gonna redo this one with actual randomness
// prettier-ignore
function buildMap(size) {
  const map = [];
  for (let row = 0; row < size; row++) {
    map[row] = [];
    for (let col = 0; col < size; col++) {
      // Normalize tile coords to ~[0, 3.5] range so ppl can actualy see the terrain patches
      const nx = (col + 0.5) / size * 3.5;
      const ny = (row + 0.5) / size * 3.5;

      // Change later with ramps instead of varying heights
      const height = fbm(nx, ny, 5);

      // Biome diversity
      const temp = fbm(nx + 8.3, ny + 6.1, 3);

      let terrain;
      if      (height < 0.29)                    terrain = TERRAIN.OCEAN;
      else if (height < 0.36 && temp < 0.4)      terrain = TERRAIN.TUNDRA;
      else if (height < 0.36 && temp > 0.65)     terrain = TERRAIN.DESERT;
      else if (height < 0.38)                    terrain = TERRAIN.PLAINS;
      else if (height < 0.50 && temp > 0.58)     terrain = TERRAIN.DESERT;
      else if (height < 0.50)                    terrain = TERRAIN.PLAINS;
      else if (height < 0.58 && temp < 0.38)     terrain = TERRAIN.TUNDRA;
      else if (height < 0.60)                    terrain = TERRAIN.GRASS;
      else if (height < 0.70 && temp > 0.42)     terrain = TERRAIN.FOREST;
      else if (height < 0.72)                    terrain = TERRAIN.GRASS;
      else if (height < 0.82)                    terrain = TERRAIN.HILLS;
      else                                       terrain = TERRAIN.MOUNTAIN;

      map[row][col] = terrain;
    }
  }
  return map;
}

function initShaderProgram(gl, vsSource, fsSource) {
  const vs = compileShader(gl, gl.VERTEX_SHADER,   vsSource);
  const fs = compileShader(gl, gl.FRAGMENT_SHADER, fsSource);
  if (!fs || !vs) return null;

  const program = gl.createProgram();
  gl.attachShader(program, vs);
  gl.attachShader(program, fs);
  gl.linkProgram(program);

  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    const info = gl.getProgramInfoLog(program);
    console.error("Shader link error:", info);
    gl.deleteProgram(program);
    return null;
  }

  gl.detachShader(program, vs);
  gl.detachShader(program, fs);
  gl.deleteShader(vs);
  gl.deleteShader(fs);

  return program;
}

function compileShader(gl, type, source) {
  const shader = gl.createShader(type);
  gl.shaderSource(shader, source); // Shader data To GPU
  gl.compileShader(shader); // Convert GLSL shader to WebGLProgram data

  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    const label = type === gl.VERTEX_SHADER ? "Vertex" : "Fragment";
    console.error(`${label} shader compile error:`, gl.getShaderInfoLog(shader));
    gl.deleteShader(shader);
    return null;
  }

  return shader;
}

main();