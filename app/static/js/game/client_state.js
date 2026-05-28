let matchId = null;
let gameState = null;
let mySlot = null;          // 0 or 1, set by server on join
let listeners = [];         // functions to call when state changes

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
    gameState = newState;
    // Notify listeners (e.g., for UI updates)
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

export function subscribe(listener) {
    listeners.push(listener);
    if (gameState) listener(gameState);
    return () => {
        listeners = listeners.filter(l => l !== listener);
    };
}