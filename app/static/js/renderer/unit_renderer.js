import * as THREE from 'three';
import { loadModelInto } from './model_loader.js';

const UNIT_SIZE = 0.7;
const PLAYER_COLORS = ['#367055', '#CBBD93']; // Presia green, Doon tan

// Placeholder model
function makePlaceholderBox(ownerSlot) {
    const color = PLAYER_COLORS[ownerSlot] || '#aaaaaa';
    const geometry = new THREE.BoxGeometry(UNIT_SIZE, UNIT_SIZE, UNIT_SIZE);
    const material = new THREE.MeshStandardMaterial({ color, emissive: 0x222222 });
    const box = new THREE.Mesh(geometry, material);

    box.position.y = UNIT_SIZE / 2;
    box.castShadow = true;
    box.userData.isPlaceholder = true;
    return box;
}

export function createUnitMesh(unitType, ownerSlot, position, groundHeight, model = null) {
    const group = new THREE.Group();
    group.position.set(position.x, groundHeight, position.z);
    group.userData = { type: 'unit', unitType, ownerSlot, modelLoaded: false };

    group.add(makePlaceholderBox(ownerSlot));

    if (model) {
        loadModelInto(group, model, ownerSlot);
    }

    return group;
}

export function updateUnitPosition(mesh, position, groundHeight) {
    mesh.position.set(position.x, groundHeight, position.z);
}

export function setUnitIdOnMesh(mesh, unitId) {
    mesh.userData.unitId = unitId;
}

export function setUnitMeshVisible(mesh, visible) {
    mesh.visible = visible;
}

export function removeUnitMesh(mesh, scene) {
    scene.remove(mesh);
    mesh.traverse((child) => {
        if (child.geometry) child.geometry.dispose();
        if (child.material) {
            if (Array.isArray(child.material)) child.material.forEach((m) => m.dispose());
            else child.material.dispose();
        }
    });
}