import * as THREE from 'three';

const TILE_SIZE = 1.0;
const COLORS = {
    plains: 0x6b8e23,
    grassland: 0x5a9e4e,
    forest: 0x2c5e2a,
    hills:  0xaa8c5e,
    mountains: 0xaa9988,
    desert: 0xe8cf9a,
    tundra: 0xc9d9e8,
    dirt:   0x8a6d4a,
    rocky:  0x9a9286,
    urban:  0x8c8c8c,
    ocean:  0x4a7b9d
};

export function createTileMesh(x, z, height, terrainType) {
    const color = COLORS[terrainType] || COLORS.plains;
    const geometry = new THREE.BoxGeometry(TILE_SIZE - 0.05, height, TILE_SIZE - 0.05);
    const material = new THREE.MeshStandardMaterial({ color: color, roughness: 0.7, metalness: 0.1 });
    const cube = new THREE.Mesh(geometry, material);
    cube.position.set(x, height / 2, z);
    cube.castShadow = true;
    cube.receiveShadow = true;
    cube.userData = { type: 'tile', x, z, height, baseColor: color, highlighted: false };
    return cube;
}

export function updateTileColors(mesh, terrainType) {
    const color = COLORS[terrainType] || COLORS.plains;
    mesh.userData.baseColor = color;
    if (!mesh.userData.highlighted) {
        mesh.material.color.setHex(color);
    }
}

export function highlightTile(mesh) {
    mesh.userData.highlighted = true;
    mesh.material.color.setHex(0x4fc3f7); // light blue
    mesh.material.emissive.setHex(0x16435c);
}

export function highlightTileAttack(mesh) {
    mesh.userData.highlighted = true;
    mesh.material.color.setHex(0xe74c3c); // red
    mesh.material.emissive.setHex(0x5c1a16);
}

export function unhighlightTile(mesh) {
    mesh.userData.highlighted = false;
    mesh.material.color.setHex(mesh.userData.baseColor || COLORS.plains);
    mesh.material.emissive.setHex(0x000000);
}