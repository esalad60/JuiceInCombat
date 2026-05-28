import * as THREE from 'three';

const PLAYER_COLORS = ['#367055', '#CBBD93']; // Presia green, Doon tan

export function createBuildingMesh(building, position, groundHeight) {
    const base = PLAYER_COLORS[building.owner_slot] || '#888888';
    const isCapital = building.is_capital;

    const h = isCapital ? 1.4 : 0.9;
    const w = isCapital ? 0.85 : 0.7;

    const geometry = new THREE.BoxGeometry(w, h, w);
    const material = new THREE.MeshStandardMaterial({
        color: base,
        emissive: isCapital ? 0x332200 : 0x000000,
        metalness: 0.3,
        roughness: 0.6,
    });
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.set(position.x, groundHeight + h / 2, position.z);
    mesh.castShadow = true;
    mesh.userData = { type: 'building', buildingId: building.id, ownerSlot: building.owner_slot };

    // flag-pole on capitals so they read as the objective
    if (isCapital) {
        const poleGeo = new THREE.CylinderGeometry(0.03, 0.03, 0.6, 6);
        const poleMat = new THREE.MeshStandardMaterial({ color: '#ffffff' });
        const pole = new THREE.Mesh(poleGeo, poleMat);
        pole.position.set(0, h / 2 + 0.3, 0);
        mesh.add(pole);
    }
    return mesh;
}

export function updateBuildingMesh(mesh, building, position, groundHeight) {
    const base = PLAYER_COLORS[building.owner_slot] || '#888888';
    mesh.material.color.set(base);
    mesh.userData.ownerSlot = building.owner_slot;
}