import * as THREE from 'three';
import { initScene } from './renderer/scene.js';
import { initCamera } from './renderer/camera.js';
import { createTileMesh, updateTileColors } from './renderer/tile_renderer.js';
import { createUnitMesh, updateUnitPosition, removeUnitMesh, setUnitIdOnMesh } from './renderer/unit_renderer.js';
import { setMatchId, updateGameState, getCurrentPlayerSlot, getMySlot, getUnit, isMyTurn, getMyResources } from './game/client_state.js';
import { selectUnit, getSelectedUnit, clearSelection } from './game/selection.js';
import { initHUD, updateHUD, showMessage, setEndTurnEnabled, showRecruitPanel } from './ui/hud.js';
import { connectSocket, sendAction, sendEndTurn } from './network/socket_client.js';

window.sendAction = sendAction;

let scene, camera, renderer;
let tileMeshes = [];      // 2D array of { mesh, x, y, height }
let unitMeshes = new Map(); // unitId -> mesh
let raycaster = new THREE.Raycaster();
let mouse = new THREE.Vector2();
let controls;

async function init() {
    const pathParts = window.location.pathname.split('/');
    const matchId = pathParts[pathParts.length - 1];
    if (!matchId) {
        alert('No match ID provided');
        window.location.href = '/lobby';
        return;
    }
    setMatchId(matchId);

    const container = document.body;
    const { scene: s, camera: c, renderer: r } = initScene(container);
    scene = s;
    camera = c;
    renderer = r;
    
    controls = initCamera(camera, renderer.domElement);
    
    initHUD({
        onEndTurn: () => sendEndTurn(),
        onRecruit: (unitType, x, y) => {
            sendAction({ type: 'recruit', unit_type: unitType, to: [x, y] });
        }
    });
    
    connectSocket(matchId, {
        onGameState: (gameState) => {
            updateGameState(gameState);
            rebuildWorld(gameState);
            updateHUD(gameState);
            const mySlot = getMySlot();
            const current = getCurrentPlayerSlot();
            setEndTurnEnabled(isMyTurn());
        },
        onActionApplied: (result) => {
            showMessage(`Action executed: ${JSON.stringify(result)}`);
            // Could refresh selection or highlight
        },
        onTurnChanged: (nextSlot) => {
            showMessage(`It is now Player ${nextSlot + 1}'s turn`);
            clearSelection();
            setEndTurnEnabled(isMyTurn());
        },
        onGameEnded: (winnerSlot) => {
            const mySlot = getMySlot();
            if (winnerSlot === mySlot) {
                showMessage("🏆 YOU WIN! Captured enemy HQ.");
            } else {
                showMessage("💀 You lose...");
            }
            setEndTurnEnabled(false);
        },
        onGameStarted: (gameState) => {
            updateGameState(gameState);
            rebuildWorld(gameState);
            showMessage("Game started!");
        },
        onError: (err) => {
            showMessage(`Error: ${err.message}`, true);
        }
    });
    
    window.addEventListener('click', onClick, false);
    
    animate();
}

function animate() {
    requestAnimationFrame(animate);
    controls.update(); // update camera controls
    renderer.render(scene, camera);
}

function onClick(event) {
    if (!isMyTurn()) {
        showMessage("Not your turn", true);
        return;
    }
    
    // Compute mouse position in normalized coordinates (-1 to +1)
    mouse.x = (event.clientX / renderer.domElement.clientWidth) * 2 - 1;
    mouse.y = -(event.clientY / renderer.domElement.clientHeight) * 2 + 1;
    
    raycaster.setFromCamera(mouse, camera);
    
    // First, try to select a unit
    const unitObjects = Array.from(unitMeshes.values());
    const unitIntersects = raycaster.intersectObjects(unitObjects);
    if (unitIntersects.length > 0) {
        const hit = unitIntersects[0].object;
        const unitId = hit.userData.unitId;
        const unit = getUnit(unitId);
        if (unit && unit.owner_slot === getMySlot()) {
            selectUnit(unitId);
            showMessage(`Selected ${unit.type}`);
            return;
        } else {
            showMessage("You can't select enemy units", true);
            return;
        }
    }
    

    const tileObjects = [];
    for (let row of tileMeshes) {
        for (let entry of row) {
            tileObjects.push(entry.mesh);
        }
    }
    const tileIntersects = raycaster.intersectObjects(tileObjects);
    if (tileIntersects.length > 0) {
        const hitTile = tileIntersects[0].object;
        const { x, z } = hitTile.userData; // x and z are grid coordinates
        const y = z; // because grid is square, but store as z, actual y coordinate is grid row
    
        const selectedUnitId = getSelectedUnit();
        if (selectedUnitId !== null) {
            sendAction({ type: 'move', unit_id: selectedUnitId, to: [x, y] });
            clearSelection();
        } else {
            showMessage("Select a unit first (click on it)");
        }
    }
}

function rebuildWorld(gameState) {
    const gameMap = gameState.game_map;
    const width = gameMap.width;
    const height = gameMap.height;
    const units = gameState.units;
    
    // Create or update tiles
    if (tileMeshes.length === 0) {
        for (let y = 0; y < height; y++) {
            tileMeshes[y] = [];
            for (let x = 0; x < width; x++) {
                const tile = gameMap.tiles[y][x];
                const mesh = createTileMesh(x, y, tile.height, tile.base);
                mesh.userData = { type: 'tile', x, z: y };
                scene.add(mesh);
                tileMeshes[y][x] = { mesh, x, y, height: tile.height };
            }
        }
    } else {
        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                const tile = gameMap.tiles[y][x];
                const entry = tileMeshes[y][x];
                if (!entry) continue;
                if (entry.height !== tile.height) {
                    // Recreate mesh for height change
                    scene.remove(entry.mesh);
                    const newMesh = createTileMesh(x, y, tile.height, tile.base);
                    newMesh.userData = { type: 'tile', x, z: y };
                    scene.add(newMesh);
                    entry.mesh = newMesh;
                    entry.height = tile.height;
                } else {
                    updateTileColors(entry.mesh, tile.base);
                }
            }
        }
    }
    
    const currentUnitIds = new Set(Object.keys(units).map(Number));
    for (let [uid, mesh] of unitMeshes.entries()) {
        if (!currentUnitIds.has(uid)) {
            scene.remove(mesh);
            unitMeshes.delete(uid);
        }
    }
    for (let [uid, unit] of Object.entries(units)) {
        uid = parseInt(uid);
        const x = unit.x;
        const z = unit.y; // because Three.js uses XZ plane
        const tile = gameMap.tiles[z][x];
        const groundHeight = tile.height;
        if (!unitMeshes.has(uid)) {
            const mesh = createUnitMesh(unit.type, unit.owner_slot, { x, z }, groundHeight);
            setUnitIdOnMesh(mesh, uid);
            scene.add(mesh);
            unitMeshes.set(uid, mesh);
        } else {
            const mesh = unitMeshes.get(uid);
            updateUnitPosition(mesh, { x, z }, groundHeight);
        }
    }
}

init().catch(console.error);