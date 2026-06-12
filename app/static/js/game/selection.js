import {
    canInteractWithTile,
    getTile,
    getUnit,
    getMySlot,
    isMyTurn,
} from './client_state.js';

let selectedUnitId = null;
let listeners = []; // functions to call when selection changes


export function selectUnit(unitId) {
    if (selectedUnitId === unitId) return;

    selectedUnitId = unitId;

    for (const fn of listeners) {
        fn(selectedUnitId);
    }
}


export function clearSelection() {
    if (selectedUnitId !== null) {
        selectedUnitId = null;

        for (const fn of listeners) {
            fn(null);
        }
    }
}


export function getSelectedUnit() {
    return selectedUnitId;
}


export function onSelectionChange(listener) {
    listeners.push(listener);
    listener(selectedUnitId);

    return () => {
        listeners = listeners.filter(l => l !== listener);
    };
}


export function handleTileClick(x, y, selectedUnit, sendActionFn) {
    if (!isMyTurn()) {
        console.log("Not your turn");
        return;
    }

    if (selectedUnit === null) {
        console.log("No unit selected, cannot move");
        return;
    }

    const unit = getUnit(selectedUnit);
    const mySlot = getMySlot();

    if (!unit) {
        console.log("Selected unit does not exist");
        clearSelection();
        return;
    }

    if (unit.owner_slot !== mySlot) {
        console.log("Cannot move enemy unit");
        clearSelection();
        return;
    }

    const tile = getTile(x, y);

    if (!tile) {
        console.log("Invalid tile");
        return;
    }

    if (!canInteractWithTile(x, y)) {
        console.log("Cannot interact with hidden tile");
        return;
    }

    sendActionFn({
        type: "move",
        unit_id: selectedUnit,
        to: [x, y],
    });
}