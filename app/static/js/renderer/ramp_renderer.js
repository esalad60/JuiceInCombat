import * as THREE from 'three';

const TILE_SIZE = 1.0;

export function createRampPrism(x, z, lowHeight, highHeight, dirX, dirZ, color = 0x8a7d5a) {
    const s    = TILE_SIZE - 0.05;
    const half = s / 2;

    const yLow  = lowHeight;
    const yHigh = highHeight;
    const yBase = 0; 

    const v = [
        [-half, yLow,  -half],  // 0  top-low-left
        [ half, yLow,  -half],  // 1  top-low-right
        [ half, yHigh,  half],  // 2  top-high-right
        [-half, yHigh,  half],  // 3  top-high-left
        [-half, yBase, -half],  // 4  bot-low-left
        [ half, yBase, -half],  // 5  bot-low-right
        [ half, yBase,  half],  // 6  bot-high-right
        [-half, yBase,  half],  // 7  bot-high-left
    ];

    const idx = [
        // sloped top face (two tris)
        0, 1, 2,   0, 2, 3,
        // low end wall 
        0, 1, 4,   1, 5, 4,
        // high end wall
        3, 6, 2,   3, 7, 6,
        // left side wall
        0, 3, 7,   0, 7, 4,
        // right side wall
        1, 5, 6,   1, 6, 2,
        // bottom face
        4, 7, 6,   4, 6, 5,
    ];

    const positions = [];
    for (const i of idx) positions.push(...v[i]);

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    geometry.computeVertexNormals();

    const material = new THREE.MeshStandardMaterial({
        color,
        roughness: 0.95,
        metalness: 0.0,
        flatShading: true,
    });

    const mesh = new THREE.Mesh(geometry, material);
    mesh.castShadow    = true;
    mesh.receiveShadow = true;

    let yaw = 0;
    if      (dirX ===  1 && dirZ ===  0) yaw = -Math.PI / 2;
    else if (dirX === -1 && dirZ ===  0) yaw =  Math.PI / 2;
    else if (dirX ===  0 && dirZ ===  1) yaw =  0;
    else if (dirX ===  0 && dirZ === -1) yaw =  Math.PI;

    mesh.rotation.y = yaw;
    mesh.position.set(x, 0, z);
    mesh.userData = { type: 'ramp', x, z };
    return mesh;
}