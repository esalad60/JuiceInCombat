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
    if (selectedUnit !== null) {
        sendActionFn({ type: 'move', unit_id: selectedUnit, to: [x, y] });
        // Optionally clear selection after move?
        // clearSelection(); // Usually keep selected until next turn or another click
    } else {
        console.log("No unit selected, cannot move");
    }
}