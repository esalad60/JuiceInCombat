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

const FOG_COLORS = {
    unexplored: 0x1c3a1c,
    exploredTint: 0.45,
};


function getTerrainColor(terrainType) {
    return COLORS[terrainType] || COLORS.plains;
}


function getFoggedColor(baseColor, fogState) {
    if (fogState === "unexplored") {
        return new THREE.Color(FOG_COLORS.unexplored);
    }

    if (fogState === "explored") {
        return new THREE.Color(baseColor).multiplyScalar(FOG_COLORS.exploredTint);
    }

    return new THREE.Color(baseColor);
}


export function createTileMesh(x, z, height, terrainType, fogState = "visible") {
    const baseColor = getTerrainColor(terrainType);
    const foggedColor = getFoggedColor(baseColor, fogState);

    const geometry = new THREE.BoxGeometry(
        TILE_SIZE - 0.05,
        height,
        TILE_SIZE - 0.05
    );

    const material = new THREE.MeshStandardMaterial({
        color: foggedColor,
        roughness: 0.7,
        metalness: 0.1
    });

    const cube = new THREE.Mesh(geometry, material);

    cube.position.set(x, height / 2, z);
    cube.castShadow = true;
    cube.receiveShadow = true;

    cube.userData = {
        type: 'tile',
        x,
        z,
        height,
        terrainType,
        fogState,
        baseColor,
        highlighted: false
    };

    return cube;
}


export function updateTileColors(mesh, terrainType, fogState = "visible") {
    const baseColor = getTerrainColor(terrainType);
    const foggedColor = getFoggedColor(baseColor, fogState);

    mesh.userData.terrainType = terrainType;
    mesh.userData.fogState = fogState;
    mesh.userData.baseColor = baseColor;

    if (!mesh.userData.highlighted) {
        mesh.material.color.copy(foggedColor);
        mesh.material.emissive.setHex(0x000000);
    }
}


export function applyFogToTile(mesh, fogState = "visible") {
    const baseColor = mesh.userData.baseColor || COLORS.plains;
    const foggedColor = getFoggedColor(baseColor, fogState);

    mesh.userData.fogState = fogState;

    if (!mesh.userData.highlighted) {
        mesh.material.color.copy(foggedColor);
        mesh.material.emissive.setHex(0x000000);
    }
}


export function highlightTile(mesh) {
    mesh.userData.highlighted = true;
    mesh.material.color.setHex(0x4fc3f7);
    mesh.material.emissive.setHex(0x16435c);
}


export function highlightTileAttack(mesh) {
    mesh.userData.highlighted = true;
    mesh.material.color.setHex(0xe74c3c);
    mesh.material.emissive.setHex(0x5c1a16);
}


export function unhighlightTile(mesh) {
    mesh.userData.highlighted = false;

    const baseColor = mesh.userData.baseColor || COLORS.plains;
    const fogState = mesh.userData.fogState || "visible";
    const foggedColor = getFoggedColor(baseColor, fogState);

    mesh.material.color.copy(foggedColor);
    mesh.material.emissive.setHex(0x000000);
}