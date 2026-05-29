import * as THREE from 'three';
import { initScene } from './renderer/scene.js';
import { initCamera } from './renderer/camera.js';
import { createTileMesh, updateTileColors, highlightTile, unhighlightTile, highlightTileAttack } from './renderer/tile_renderer.js';
import { createUnitMesh, updateUnitPosition, removeUnitMesh, setUnitIdOnMesh } from './renderer/unit_renderer.js';
import { createBuildingMesh, updateBuildingMesh } from './renderer/building_renderer.js';
import { setMatchId, updateGameState, getCurrentPlayerSlot, getMySlot, getUnit, isMyTurn,
         getMyResources, getGameState, getTile, getRecruitableUnits } from './game/client_state.js';
import { selectUnit, getSelectedUnit, clearSelection, onSelectionChange } from './game/selection.js';
import { initHUD, updateHUD, showMessage, setEndTurnEnabled,
         showRecruitList, showUnitPanel, showEnemyUnitPanel,
         showBuildingPanel, showWeaponInfo, hidePanels } from './ui/hud.js';
import { connectSocket, sendAction, sendEndTurn } from './network/socket_client.js';

let scene, camera, renderer;
let tileMeshes = [];
let unitMeshes = new Map();
let buildingMeshes = new Map();
let raycaster = new THREE.Raycaster();
let mouse = new THREE.Vector2();
let controls;

let mode = 'idle';
let highlightSet = new Map();
let pendingWeaponName = null;
let pendingRecruitType = null;
let recruitBuildingXY = null;

async function init() {
    const matchId = window.MATCH_ID || new URLSearchParams(window.location.search).get('id');
    if (!matchId) {
        alert('No match ID provided');
        window.location.href = '/lobby';
        return;
    }
    setMatchId(matchId);

    initHUD({
        onEndTurn: () => { sendEndTurn(); enterIdle(); },
        onWeaponSelected: (unitId, weaponName) => enterFireMode(unitId, weaponName),
        onRecruitRequested: (bx, by) => openRecruitList(bx, by),
        onRecruitUnitChosen: (unitType) => enterRecruitMode(unitType),
    });

    connectSocket(matchId, {
        onGameState: (gs) => {
            updateGameState(gs); rebuildWorld(gs); updateHUD(gs);
            setEndTurnEnabled(isMyTurn());
            enterIdle();
        },
        onActionApplied: () => {},
        onTurnChanged: (nextSlot) => {
            showMessage(`It is now Player ${nextSlot + 1}'s turn`);
            enterIdle();
            setEndTurnEnabled(getMySlot() === nextSlot);
        },
        onGameEnded: (winnerSlot) => {
            showMessage(winnerSlot === getMySlot() ? "YOU WIN! Captured enemy HQ." : "You lose...");
            setEndTurnEnabled(false); enterIdle();
        },
        onGameStarted: (gs) => {
            updateGameState(gs); rebuildWorld(gs); updateHUD(gs);
            setEndTurnEnabled(isMyTurn());
            showMessage("Game started!");
        },
        onError: (err) => showMessage(`Error: ${err.message}`, true),
    });

    try {
        const { scene: s, camera: c, renderer: r } = initScene(document.body);
        scene = s;
        camera = c;
        renderer = r;

        renderer.domElement.addEventListener('click', onClick, false);

        controls = initCamera(camera, renderer.domElement);
        animate();
    } catch (e) {
        console.error('3D scene failed to initialize:', e);
        showMessage('3D view failed to load — check console (F12). HUD still works.', true);
    }
}

function animate() {
    if (!renderer || !scene || !camera) return;
    requestAnimationFrame(animate);
    if (controls) controls.update();
    renderer.render(scene, camera);
}

function enterIdle() {
    mode = 'idle';
    pendingWeaponName = null;
    pendingRecruitType = null;
    recruitBuildingXY = null;
    clearSelection();
    clearHighlights();
    hidePanels();
}

function enterMoveMode(unitId) {
    mode = 'move';
    pendingWeaponName = null;
    clearHighlights();
    const unit = getUnit(unitId);
    if (!unit) return;
    highlightSet = computeReachable(unit);
    paintHighlights('move');
    showUnitPanel(unit);
}

function enterFireMode(unitId, weaponName) {
    const unit = getUnit(unitId);
    if (!unit) return;
    const weapon = (unit.weapons || []).find(w => w.name === weaponName);
    if (!weapon) return;
    mode = 'fire';
    pendingWeaponName = weaponName;
    clearHighlights();
    highlightSet = computeFireTargets(unit, weapon);
    paintHighlights('fire');
    showWeaponInfo(weapon);   // pop the weapon stats box beside the unit panel
    showMessage(`Firing ${weaponName} - click an enemy in range`);
}

function openRecruitList(bx, by) {
    if (!isMyTurn()) { showMessage("Not your turn", true); return; }
    recruitBuildingXY = [bx, by];
    const faction = factionOfSlot(getMySlot());
    showRecruitList(getRecruitableUnits(faction));
}

function enterRecruitMode(unitType) {
    if (!recruitBuildingXY) return;
    mode = 'recruit';
    pendingRecruitType = unitType;
    clearHighlights();
    highlightSet = computeRecruitTiles(recruitBuildingXY);
    paintHighlights('move');
    showMessage(`Placing ${unitType} - click a highlighted tile`);
}

function factionOfSlot(slot) {
    const gs = getGameState();
    const p = gs && gs.players && gs.players[slot];
    return p ? p.faction : null;
}

function computeReachable(unit) {
    const result = new Map();
    const gs = getGameState();
    if (!gs || !gs.game_map) return result;
    const map = gs.game_map;
    const maxMove =
        unit.movement ??
        unit.move_range ??
        unit.max_movement ??
        unit.movement_remaining ??
        0;

    if ((unit.movement_remaining ?? maxMove) < maxMove) {
        return result;
    }

    const budget = maxMove;
    const occupied = new Set();
    for (const u of Object.values(gs.units || {})) {
        if (u.id !== unit.id) occupied.add(`${u.x},${u.y}`);
    }
    const costs = new Map([[`${unit.x},${unit.y}`, 0]]);
    let frontier = [[unit.x, unit.y, 0]];
    const dirs = [[0,-1],[1,0],[0,1],[-1,0]];
    while (frontier.length) {
        frontier.sort((a,b) => a[2]-b[2]);
        const [cx, cy, cc] = frontier.shift();
        if (cc > (costs.get(`${cx},${cy}`) ?? Infinity)) continue;
        for (const [dx,dy] of dirs) {
            const nx = cx+dx, ny = cy+dy;
            if (nx<0||ny<0||ny>=map.height||nx>=map.width) continue;
            const tile = map.tiles[ny] && map.tiles[ny][nx];
            if (!tile || tile.base === 'ocean') continue;
            const key = `${nx},${ny}`;
            if (occupied.has(key)) continue;
            const nc = cc + 1;
            if (nc > budget) continue;
            if (nc < (costs.get(key) ?? Infinity)) {
                costs.set(key, nc); result.set(key, nc);
                frontier.push([nx, ny, nc]);
            }
        }
    }
    return result;
}

function computeFireTargets(unit, weapon) {
    const result = new Map();
    const gs = getGameState();

    if (!gs || !gs.game_map) return result;

    const map = gs.game_map;
    const range = weapon.range ?? 1;

    for (let y = 0; y < map.height; y++) {
        for (let x = 0; x < map.width; x++) {

            const dist = Math.max(
                Math.abs(x - unit.x),
                Math.abs(y - unit.y)
            );

            if (dist >= 1 && dist <= range) {
                result.set(`${x},${y}`, dist);
            }
        }
    }

    return result;
}

function computeRecruitTiles(buildingXY) {
    const result = new Map();
    const gs = getGameState();

    if (!gs || !gs.game_map) return result;

    const map = gs.game_map;
    const [bx, by] = buildingXY;

    const baseTile = map.tiles[by]?.[bx];
    const baseHeight = baseTile?.height ?? 1;

    const occupied = new Set(
        Object.values(gs.units || {})
            .map(u => `${u.x},${u.y}`)
    );

    const dirs = [
        [0,-1],
        [1,0],
        [0,1],
        [-1,0]
    ];

    for (const [dx, dy] of dirs) {
        const nx = bx + dx;
        const ny = by + dy;

        if (
            nx < 0 ||
            ny < 0 ||
            ny >= map.height ||
            nx >= map.width
        ) continue;

        const tile = map.tiles[ny]?.[nx];

        if (!tile) continue;
        if (tile.base === 'ocean') continue;
        if (tile.height !== baseHeight) continue;
        if (occupied.has(`${nx},${ny}`)) continue;

        result.set(`${nx},${ny}`, 0);
    }

    return result;
}

function clearHighlights() {
    for (let row of tileMeshes) {
        for (let entry of row) {
            if (entry && entry.mesh) unhighlightTile(entry.mesh);
        }
    }
    highlightSet = new Map();
}

function paintHighlights(kind) {
    for (const key of highlightSet.keys()) {
        const [x, y] = key.split(',').map(Number);
        const entry = tileMeshes[y] && tileMeshes[y][x];
        if (!entry || !entry.mesh) continue;
        if (kind === 'fire') highlightTileAttack(entry.mesh);
        else highlightTile(entry.mesh);
    }
}

function onClick(event) {
    if (!renderer || !camera) return;

    const rect = renderer.domElement.getBoundingClientRect();

    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);

    const unitHit = raycaster.intersectObjects(
        Array.from(unitMeshes.values()),
        true
    )[0];

    const buildingHit = raycaster.intersectObjects(
        Array.from(buildingMeshes.values()),
        true
    )[0];

    const tileObjects = [];
    for (let row of tileMeshes) {
        for (let entry of row) {
            if (entry?.mesh) tileObjects.push(entry.mesh);
        }
    }

    const tileHit = raycaster.intersectObjects(tileObjects, true)[0];

    if (mode === 'fire') {
        let cell = null;

        if (unitHit) {
            cell = cellOfUnit(unitHit);
        } else if (tileHit) {
            let clicked = tileHit.object;

            while (clicked && clicked.userData?.x === undefined) {
                clicked = clicked.parent;
            }

            if (clicked?.userData) {
                cell = {
                    x: clicked.userData.x,
                    y: clicked.userData.z
                };
            }
        }

        if (cell) {
            const key = `${cell.x},${cell.y}`;

            if (highlightSet.has(key)) {
                sendAction({
                    type: 'fire',
                    unit_id: getSelectedUnit(),
                    weapon_name: pendingWeaponName,
                    target_xy: [cell.x, cell.y]
                });

                enterIdle();
                return;
            }
        }

        showMessage("Click a highlighted enemy to fire", true);
        return;
    }

    if (mode === 'recruit') {
        if (tileHit) {
            const { x, z } = tileHit.object.userData;

            if (highlightSet.has(`${x},${z}`)) {
                sendAction({
                    type: 'recruit',
                    unit_type: pendingRecruitType,
                    to: [x, z]
                });

                enterIdle();
                return;
            }
        }

        showMessage("Click a highlighted tile to place the unit", true);
        return;
    }

    if (unitHit) {
        let clicked = unitHit.object;

        while (clicked && !clicked.userData?.unitId) {
            clicked = clicked.parent;
        }

        if (!clicked?.userData?.unitId) return;

        const unitId = clicked.userData.unitId;
        const unit = getUnit(unitId);

        if (unit && unit.owner_slot === getMySlot()) {
            if (!isMyTurn()) {
                enterIdle();
                selectUnit(unitId);
                showUnitPanel(unit, true);   // read-only
                showMessage("Viewing unit (not your turn)", false);
                return;
            }

            selectUnit(unitId);
            enterMoveMode(unitId);
            showMessage(`Selected ${unit.type}`);
            return;
        }

        if (unit) {
            enterIdle();
            showEnemyUnitPanel(unit);
            showMessage("Enemy unit — view only", false);
            return;
        }
    }

    if (buildingHit) {
        let clicked = buildingHit.object;

        while (clicked && !clicked.userData?.buildingId) {
            clicked = clicked.parent;
        }

        if (!clicked?.userData) return;

        const ud = clicked.userData;
        const b = getGameState().buildings[ud.buildingId];
        if (!b) return;

        if (ud.ownerSlot === getMySlot()) {
            enterIdle();
            showBuildingPanel(b, true);
            if (!isMyTurn()) showMessage("Not your turn (view only)", true);
            return;
        }

        enterIdle();
        showBuildingPanel(b, false);
        showMessage("Enemy building — view only", false);
        return;
    }

    if (mode === 'move' && tileHit) {
        let clicked = tileHit.object;

        while (clicked && clicked.userData?.x === undefined) {
            clicked = clicked.parent;
        }

        if (!clicked?.userData) return;

        const { x, z } = clicked.userData;
        const selUnit = getSelectedUnit();

        if (selUnit !== null && highlightSet.has(`${x},${z}`)) {
            sendAction({
                type: 'move',
                unit_id: selUnit,
                to: [x, z]
            });

            enterIdle();
            return;
        }

        if (selUnit !== null) {
            showMessage("Out of range", true);
            return;
        }
    }

    if (mode !== 'idle') {
        enterIdle();
    }
}

function cellOfUnit(unitHit) {
    const u = getUnit(unitHit.object.userData.unitId);
    return u ? { x: u.x, y: u.y } : null;
}

function rebuildWorld(gameState) {
    if (!gameState || !gameState.game_map) return;
    const gameMap = gameState.game_map;
    const width = gameMap.width, height = gameMap.height;
    const units = gameState.units || {};

    if (tileMeshes.length === 0) {
        for (let y = 0; y < height; y++) {
            tileMeshes[y] = [];
            for (let x = 0; x < width; x++) {
                const tile = gameMap.tiles[y][x];
                const mesh = createTileMesh(x, y, tile.height, tile.base);
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
                    scene.remove(entry.mesh);
                    const newMesh = createTileMesh(x, y, tile.height, tile.base);
                    scene.add(newMesh);
                    entry.mesh = newMesh; entry.height = tile.height;
                } else {
                    updateTileColors(entry.mesh, tile.base);
                }
            }
        }
    }

    const currentUnitIds = new Set(Object.keys(units).map(Number));
    for (let [uid, mesh] of unitMeshes.entries()) {
        if (!currentUnitIds.has(uid)) { scene.remove(mesh); unitMeshes.delete(uid); }
    }
    for (let [uid, unit] of Object.entries(units)) {
        uid = parseInt(uid);
        const x = unit.x, z = unit.y;
        const groundHeight = gameMap.tiles[z][x].height;
        if (!unitMeshes.has(uid)) {
            const mesh = createUnitMesh(unit.type, unit.owner_slot, { x, z }, groundHeight);
            setUnitIdOnMesh(mesh, uid);
            scene.add(mesh); unitMeshes.set(uid, mesh);
        } else {
            updateUnitPosition(unitMeshes.get(uid), { x, z }, groundHeight);
        }
    }

    const buildings = gameState.buildings || {};
    const currentBuildingIds = new Set(Object.keys(buildings).map(Number));
    for (let [bid, mesh] of buildingMeshes.entries()) {
        if (!currentBuildingIds.has(bid)) { scene.remove(mesh); buildingMeshes.delete(bid); }
    }
    for (let [bid, building] of Object.entries(buildings)) {
        bid = parseInt(bid);
        const x = building.x, z = building.y;
        const groundHeight = gameMap.tiles[z][x].height;
        if (!buildingMeshes.has(bid)) {
            const mesh = createBuildingMesh(building, { x, z }, groundHeight);
            scene.add(mesh); buildingMeshes.set(bid, mesh);
        } else {
            updateBuildingMesh(buildingMeshes.get(bid), building, { x, z }, groundHeight);
        }
    }

    if (highlightSet.size > 0) {
        paintHighlights(mode === 'fire' ? 'fire' : 'move');
    }
}

init().catch(console.error);