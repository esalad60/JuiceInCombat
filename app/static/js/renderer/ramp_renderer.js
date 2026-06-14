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

function terrainColor(t) {
    return COLORS[t] || COLORS.plains;
}

export function createRampMesh(fromTile, toTile, terrainType, rampType) {
    if (!fromTile || !toTile) return null;

    const ax = fromTile.x, az = fromTile.y, ah = fromTile.height ?? 1;
    const bx = toTile.x,   bz = toTile.y,   bh = toTile.height ?? 1;

    const dx = bx - ax;
    const dz = bz - az;
    if (Math.abs(dx) + Math.abs(dz) !== 1) return null;

    const color = terrainColor(
        terrainType || (bh >= ah ? toTile.base : fromTile.base)
    );

    const lowH  = Math.min(ah, bh);
    const highH = Math.max(ah, bh);
    const rise  = highH - lowH;
    const run   = 1.0; 

    const slabLength = Math.sqrt(run * run + rise * rise);
    const thickness  = 0.08;
    const width      = TILE_SIZE - 0.05;

    const geometry = new THREE.BoxGeometry(width, thickness, slabLength);
    const material = new THREE.MeshStandardMaterial({
        color,
        roughness: 0.9,
        metalness: 0.0,
    });
    const ramp = new THREE.Mesh(geometry, material);
    ramp.castShadow = true;
    ramp.receiveShadow = true;

    const midX = (ax + bx) / 2;
    const midZ = (az + bz) / 2;
    const midY = (ah + bh) / 2; 

    ramp.position.set(midX, midY, midZ);

    const slopeAngle = Math.atan2(rise, run);

    if (dx !== 0) {
        ramp.rotation.y = Math.PI / 2;
        const dir = (bh > ah) ? Math.sign(dx) : -Math.sign(dx);
        ramp.rotation.z = -dir * slopeAngle;
    } else {
        const dir = (bh > ah) ? Math.sign(dz) : -Math.sign(dz);
        ramp.rotation.x = dir * slopeAngle;
    }

    ramp.userData = {
        type: 'ramp',
        rampType: rampType || null,
        a: [ax, az],
        b: [bx, bz],
    };

    return ramp;
}