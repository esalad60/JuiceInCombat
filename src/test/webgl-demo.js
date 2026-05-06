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

function main() {
  const canvas = document.querySelector("#glCanvas");
  const gl = canvas.getContext("webgl2", {
    antialias:    true,
    depth:        true, // ambient occulsion
    powerPreference: "high-performance",
  });

  if (!gl) {
    const msg = document.createElement("p");
    msg.style.cssText = "color: black";
    msg.textContent = "WebGL2 not available";
    canvas.parentNode.insertAdjacentElement("afterend", msg);
    return;
  }

  const vsSource = `

    uniform mat4 uModelMatrix; // Actual Model rotation, position, etc. Just one now extend to many later
    uniform mat4 uViewMatrix; // Position of camera in world (3d world relative to camera)
    uniform mat4 uProjectionMatrix; // Actual field of objects through camera -> screen (clip space) 

    out vec4 vColor;  // passed to fragment shader 

    void main() {
      gl_Position = uModelMatrix * uViewMatrix * uProjectionMatrix * vec4(aPosition, 1.0);
      vColor = aColor;
    }
  `;

  const fsSource = `
    precision mediump float; // float16 (?) precision. Balance effiency and detail

    in vec4 vColor; // Apply gradient or smoothing
    out vec4 fragColor;

    void main() {
      fragColor = vColor;
    }
  `;

  const projection = mat4.create()
  mat4.perspective(
    projection, 
    (55.0 * Math.PI) / 180.0, // 55 degrees above azimuth
    canvas.clientWidth / canvas.clientHeight, 
    0.1, // near clip plane
    200.0, // far clip plane
  )

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
  }

  gl.enable(gl.DEPTH_TEST); // Check depth buffer
  gl.enable(gl.CULL_FACE); // Backface culling


  function render() {
    const view = buildViewMatrix(cam);
    gl.clearColor(0.04, 0.05, 0.08, 1.0); // polytopia bg
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);

    gl.uniformMatrix4fv(uViewMatrix, false, view);
    gl.uniformMatrix4fv(uProjectionMatrix, false, projection);
  }

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
    throw new Error(`Could not compile WebGL program. \n\n${info}`);
    return null
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

  return shader;
}

main();
