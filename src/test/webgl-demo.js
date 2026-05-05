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
