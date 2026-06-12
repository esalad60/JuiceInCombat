import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const loader = new GLTFLoader();

const cache = new Map();

const PLAYER_TINT = [0x4a7c4a, 0xb8a96a]; 

function loadModel(url) {
    if (!cache.has(url)) {
        const p = new Promise((resolve, reject) => {
            loader.load(
                url,
                (gltf) => resolve(gltf.scene),
                undefined,
                (err) => reject(err)
            );
        });
        cache.set(url, p);
    }

    return cache.get(url).then((scene) => scene.clone(true));
}

function prepareModel(model, ownerSlot, targetSize = 0.9) {
    // Fit model into tile
    const box = new THREE.Box3().setFromObject(model);
    const size = new THREE.Vector3();
    box.getSize(size);
    const maxDim = Math.max(size.x, size.y, size.z) || 1;
    const scale = targetSize / maxDim;
    model.scale.setScalar(scale);

    const box2 = new THREE.Box3().setFromObject(model);
    const min = box2.min;
    const center = new THREE.Vector3();
    box2.getCenter(center);
    model.position.x -= center.x;
    model.position.z -= center.z;
    model.position.y -= min.y;

    const tint = PLAYER_TINT[ownerSlot];
    model.traverse((child) => {
        if (child.isMesh) {
            child.castShadow = true;
            child.receiveShadow = false;
            if (tint !== undefined && child.material) {

                child.material = child.material.clone();
                if (child.material.color) child.material.color.multiplyScalar(1);
                child.material.emissive = new THREE.Color(tint).multiplyScalar(0.15);
            }
        }
    });

    return model;
}

export function loadModelInto(group, url, ownerSlot, { onError } = {}) {
    return loadModel(url)
        .then((model) => {
            prepareModel(model, ownerSlot);

            group.userData.modelLoaded = true;

            for (const child of [...group.children]) {
                if (child.userData && child.userData.isPlaceholder) {
                    group.remove(child);
                    if (child.geometry) child.geometry.dispose();
                    if (child.material) child.material.dispose();
                }
            }
            group.add(model);
            return model;
        })
        .catch((err) => {
            console.warn(`Model load failed for ${url}:`, err);
            if (onError) onError(err);
        });
}

export function preloadModels(urls) {
    for (const url of urls) {
        if (url) loadModel(url).catch(() => {});
    }
}