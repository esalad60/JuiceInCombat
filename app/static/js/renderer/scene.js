import * as THREE from 'three';

export function initScene(container) {
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a1030);
    scene.fog = new THREE.FogExp2(0x0a1030, 0.008);
    
    const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.set(15, 20, 15);
    camera.lookAt(8, 0, 8);
    
    const existingCanvas = document.getElementById('glCanvas');
    const renderer = new THREE.WebGLRenderer({
        canvas: existingCanvas || undefined,
        antialias: true,
    });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.shadowMap.enabled = true; // for future units
    renderer.setPixelRatio(window.devicePixelRatio);
    if (!existingCanvas) {
        document.body.appendChild(renderer.domElement);
    }
    
    const ambientLight = new THREE.AmbientLight(0x404060);
    scene.add(ambientLight);
    const dirLight = new THREE.DirectionalLight(0xffffff, 1);
    dirLight.position.set(5, 10, 7);
    dirLight.castShadow = true;
    scene.add(dirLight);
    const fillLight = new THREE.PointLight(0x556688, 0.3);
    fillLight.position.set(-3, 5, 4);
    scene.add(fillLight);
    
    const gridHelper = new THREE.GridHelper(50, 20, 0x88aaff, 0x335588);
    gridHelper.position.y = -0.2;
    scene.add(gridHelper);
    
    return { scene, camera, renderer };
}