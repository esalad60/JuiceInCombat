import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

export function initCamera(camera, domElement) {
    const controls = new OrbitControls(camera, domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.rotateSpeed = 1.0;
    controls.zoomSpeed = 1.2;
    controls.panSpeed = 0.8;
    controls.screenSpacePanning = true; // no panning up/down
    controls.maxPolarAngle = Math.PI / 2.4;
    controls.target.set(8, 0, 8);
    controls.update();
    return controls;
}