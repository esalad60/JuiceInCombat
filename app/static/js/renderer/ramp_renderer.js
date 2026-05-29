import * as THREE from 'three';

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

export function createRampMesh(fromTile, toTile, terrainType, rampType) {
    const color = COLORS[terrainType] || COLORS.plains;
}
