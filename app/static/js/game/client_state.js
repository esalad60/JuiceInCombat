let matchId = null;
let gameState = null;
let mySlot = null; 
let listeners = [];    
let unitCatalog = {};   

export function setUnitCatalog(catalog) {
    if (catalog) unitCatalog = catalog;
}

export function getUnitCatalog() {
    return unitCatalog;
}

export function getRecruitableUnits(faction) {
    return unitCatalog[faction] || [];
}

export function setMatchId(id) {
    matchId = id;
}

export function getMatchId() {
    return matchId;
}

export function setMySlot(slot) {
    mySlot = slot;
}

export function getMySlot() {
    return mySlot;
}

export function updateGameState(newState) {
    if (!newState) {
        gameState = newState;
        for (const fn of listeners) fn(gameState);
        return;
    }

    if (newState.viewer_slot !== undefined && newState.viewer_slot !== null) {
        mySlot = newState.viewer_slot;
    }

    if (
        newState.game_map &&
        Array.isArray(newState.game_map.tiles) &&
        (newState.game_map.tiles.length === 0 || !Array.isArray(newState.game_map.tiles[0]))
    ) {
        const gm = newState.game_map;
        const grid = [];

        for (let y = 0; y < gm.height; y++) {
            grid[y] = new Array(gm.width).fill(null);
        }

        for (const t of gm.tiles) {
            if (grid[t.y]) {
                grid[t.y][t.x] = t;
            }
        }

        gm.tiles = grid;
    }

    gameState = newState;

    for (const fn of listeners) {
        fn(gameState);
    }
}

export function getGameState() {
    return gameState;
}

export function getCurrentPlayerSlot() {
    return gameState?.current_player_slot ?? -1;
}

export function getTurn() {
    return gameState?.turn ?? 0;
}

export function getWinnerSlot() {
    return gameState?.winner_slot;
}

export function getPlayer(slot) {
    return gameState?.players?.[slot];
}

export function getUnit(unitId) {
    return gameState?.units?.[unitId];
}

export function getUnitsForPlayer(slot) {
    if (!gameState?.units) return [];
    return Object.values(gameState.units).filter(u => u.owner_slot === slot);
}

export function getBuilding(buildingId) {
    return gameState?.buildings?.[buildingId];
}

export function getMap() {
    return gameState?.game_map;
}

export function getTile(x, y) {
    const map = getMap();
    if (!map || !map.tiles[y] || !map.tiles[y][x]) return null;
    return map.tiles[y][x];
}

export function isMyTurn() {
    if (mySlot === null || !gameState) return false;
    return gameState.current_player_slot === mySlot;
}

export function getResources(slot) {
    const player = getPlayer(slot);
    return player?.resources ?? {};
}

export function getMyResources() {
    if (mySlot === null) return {};
    return getResources(mySlot);
}

export function getMyIncome() {
    if (mySlot === null || !gameState) return {};
    const p = (gameState.players || []).find(pl => pl.slot === mySlot);
    return (p && p.income_per_turn) ? p.income_per_turn : {};
}

export function subscribe(listener) {
    listeners.push(listener);
    if (gameState) listener(gameState);
    return () => {
        listeners = listeners.filter(l => l !== listener);
    };
}

export function getTileFog(x, y) {
    const tile = getTile(x, y);
    return tile?.fog ?? "unexplored";
}

export function isTileVisible(x, y) {
    return getTileFog(x, y) === "visible";
}

export function isTileExplored(x, y) {
    const fog = getTileFog(x, y);
    return fog === "visible" || fog === "explored";
}

export function isTileUnexplored(x, y) {
    return getTileFog(x, y) === "unexplored";
}

export function canInteractWithTile(x, y) {
    return isTileVisible(x, y);
}