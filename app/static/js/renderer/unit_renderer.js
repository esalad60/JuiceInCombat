import * as THREE from 'three';

const UNIT_SIZE = 0.7;
const PLAYER_COLORS = ['#367055', '#CBBD93']; // Presia green, Doon tan

export function createUnitMesh(unitType, ownerSlot, position, groundHeight) {
    const color = PLAYER_COLORS[ownerSlot] || '#aaaaaa';

    const geometry = new THREE.BoxGeometry(UNIT_SIZE, UNIT_SIZE, UNIT_SIZE);

    const material = new THREE.MeshStandardMaterial({
        color: color,
        emissive: 0x222222,
    });

    const cube = new THREE.Mesh(geometry, material);

    cube.position.set(position.x, groundHeight + UNIT_SIZE / 2, position.z);

    cube.userData = {
        type: 'unit',
        unitType,
        ownerSlot,
    };

    cube.castShadow = true;
    cube.receiveShadow = false;

    return cube;
}

export function updateUnitPosition(mesh, position, groundHeight) {
    mesh.position.set(position.x, groundHeight + UNIT_SIZE / 2, position.z);
}

export function setUnitIdOnMesh(mesh, unitId) {
    mesh.userData.unitId = unitId;
}

export function setUnitMeshVisible(mesh, visible) {
    mesh.visible = visible;
}

export function removeUnitMesh(mesh, scene) {
    scene.remove(mesh);

    if (mesh.geometry) {
        mesh.geometry.dispose();
    }

    if (mesh.material) {
        mesh.material.dispose();
    }
}