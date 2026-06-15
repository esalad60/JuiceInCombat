import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

export function initCamera(camera, domElement) {
    const controls = new OrbitControls(camera, domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.rotateSpeed = 1.0;
    controls.zoomSpeed = 1.2;
    controls.panSpeed = 0.8;
    controls.screenSpacePanning = true;
    controls.maxPolarAngle = Math.PI / 2.4;
    controls.target.set(0, 0, 0);
    controls.update();
    return controls;
}

export function centerCameraOnMap(camera, controls, width, height) {
    const cx = (width - 1) / 2;
    const cz = (height - 1) / 2;

    const span = Math.max(width, height);
    const dist = span * 1.3 + 4;

    camera.position.set(cx + dist * 0.6, dist, cz + dist * 0.6);
    camera.lookAt(cx, 0, cz);

    if (controls) {
        controls.target.set(cx, 0, cz);
        controls.update();
    }
}