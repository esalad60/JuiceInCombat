import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const loader = new GLTFLoader();
const cache = new Map(); // url -> Promise<THREE.Object3D>

const FEATURE_MODELS = {
    forest:   '/static/models/terrain/forest/forest.gltf',
    mountain: '/static/models/terrain/mountain/mountain.gltf',
};

export function featureHasModel(feature) {
    return !!FEATURE_MODELS[feature];
}

function loadModel(url) {
    if (!cache.has(url)) {
        cache.set(url, new Promise((resolve, reject) => {
            loader.load(url, (gltf) => resolve(gltf.scene), undefined, reject);
        }));
    }
    return cache.get(url).then((scene) => scene.clone(true));
}

function prepareFeatureModel(model, tileHeight, targetSize = 0.9) {
    const box = new THREE.Box3().setFromObject(model);
    const size = new THREE.Vector3();
    box.getSize(size);
    const maxDim = Math.max(size.x, size.y, size.z) || 1;
    model.scale.setScalar(targetSize / maxDim);

    const box2 = new THREE.Box3().setFromObject(model);
    const center = new THREE.Vector3();
    box2.getCenter(center);
    model.position.x -= center.x;
    model.position.z -= center.z;
    model.position.y -= box2.min.y;   

    model.traverse((c) => { if (c.isMesh) { c.castShadow = true; } });
    return model;
}

export function createFeatureMesh(feature, x, z, tileHeight) {
    const url = FEATURE_MODELS[feature];
    if (!url) return null;

    const group = new THREE.Group();
    group.position.set(x, tileHeight, z); 
    group.userData = { type: 'feature', feature, x, z };

    loadModel(url)
        .then((model) => {
            prepareFeatureModel(model, tileHeight);
            group.add(model);
        })
        .catch((err) => {
            console.warn(`Feature model failed (${feature}): ${url}`, err);
        });

    return group;
}