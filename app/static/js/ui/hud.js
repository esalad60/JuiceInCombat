// frontend/static/js/ui/hud.js
import { getUnit, getMySlot, getCurrentPlayerSlot, getMyResources, getPlayer, getGameState, isMyTurn } from '../game/client_state.js';
import { getSelectedUnit, onSelectionChange, clearSelection } from '../game/selection.js';

let endTurnCallback = null;
let recruitCallback = null;
let selectedUnitId = null;
let unsubscribeSelection = null;

let turnIndicatorEl, cashEl, timerEl, endTurnBtn, selectedPanel, unitStatsEl, unitActionsEl;

let timerInterval = null;

export function initHUD(uiCallbacks) {
    endTurnCallback = uiCallbacks.onEndTurn;
    recruitCallback = uiCallbacks.onRecruit;
    
    turnIndicatorEl = document.getElementById('turn-indicator');
    cashEl = document.getElementById('cash');
    timerEl = document.getElementById('turn-timer');
    endTurnBtn = document.getElementById('end-turn-btn');
    selectedPanel = document.getElementById('selected-unit-panel');
    unitStatsEl = document.getElementById('unit-stats');
    unitActionsEl = document.getElementById('unit-actions');
    
    if (endTurnBtn) {
        endTurnBtn.addEventListener('click', () => {
            if (endTurnCallback && isMyTurn()) {
                endTurnCallback();
                clearSelection(); // optional
            }
        });
    }
    
    unsubscribeSelection = onSelectionChange((unitId) => {
        selectedUnitId = unitId;
        if (unitId) {
            updateUnitPanel(unitId);
            selectedPanel.style.display = 'block';
        } else {
            selectedPanel.style.display = 'none';
        }
    });
    
    if (timerInterval) clearInterval(timerInterval);
    timerInterval = setInterval(() => {
        updateTimer();
    }, 1000);
}

export function updateHUD(gameState) {
    if (!gameState) return;
    
    const currentSlot = gameState.current_player_slot;
    const mySlot = getMySlot();
    const turnText = `Turn ${gameState.turn} — Player ${currentSlot + 1}`;
    if (turnIndicatorEl) turnIndicatorEl.textContent = turnText;
    
    // Cash
    const myResources = getMyResources();
    if (cashEl && myResources) {
        cashEl.textContent = `Cash: ${myResources.cash || 0}`;
    }
    
    if (endTurnBtn) {
        endTurnBtn.disabled = !isMyTurn();
    }
    
    // If a unit is selected, refresh its panel (stats may have changed)
    if (selectedUnitId) {
        updateUnitPanel(selectedUnitId);
    }
}

function updateUnitPanel(unitId) {
    const unit = getUnit(unitId);
    if (!unit) {
        selectedPanel.style.display = 'none';
        return;
    }
    
    unitStatsEl.innerHTML = `
        <div><strong>${unit.type}</strong></div>
        <div>HP: ${unit.hp}</div>
        <div>Armor: ${unit.armor}</div>
        <div>⚡Movement: ${unit.movement_remaining}/${unit.max_movement}</div>
        <div>Fired: ${unit.has_fired_weapon ? 'Yes' : 'No'}</div>
    `;
    
    unitActionsEl.innerHTML = '';
    
    if (unit.movement_remaining > 0 && !unit.has_moved) {
        const moveBtn = document.createElement('button');
        moveBtn.textContent = 'Move';
        moveBtn.addEventListener('click', () => {
            // Movement is handled by clicking on tiles; this button just deselects? 
            showMessage('Click on a tile to move this unit');
        });
        unitActionsEl.appendChild(moveBtn);
    }
    
    for (const weapon of unit.weapons) {
        if (!unit.has_fired_weapon) {
            const fireBtn = document.createElement('button');
            fireBtn.textContent = `${weapon.name} (${weapon.range})`;
            fireBtn.addEventListener('click', () => {
                const targetX = prompt(`Enter target X coordinate for ${weapon.name}:`);
                const targetY = prompt(`Enter target Y coordinate:`);
                if (targetX !== null && targetY !== null) {
                    const action = { type: 'fire', unit_id: unitId, weapon_name: weapon.name, target_xy: [parseInt(targetX), parseInt(targetY)] };
                    if (window.sendAction) window.sendAction(action);
                    else console.warn('sendAction not available');
                }
            });
            unitActionsEl.appendChild(fireBtn);
        }
    }
    
    const recruitBtn = document.createElement('button');
    recruitBtn.textContent = 'Recruit Unit';
    recruitBtn.style.backgroundColor = '#4a6e3a';
    recruitBtn.addEventListener('click', () => {
        const unitType = prompt('Enter unit type (riflemen or commandos):', 'riflemen');
        if (unitType) {
            const x = prompt('Enter X coordinate for spawn (must be on owned building):');
            const y = prompt('Enter Y coordinate:');
            if (x !== null && y !== null) {
                if (recruitCallback) {
                    recruitCallback(unitType, parseInt(x), parseInt(y));
                } else {
                    if (window.sendAction) window.sendAction({ type: 'recruit', unit_type: unitType, to: [parseInt(x), parseInt(y)] });
                }
            }
        }
    });
    unitActionsEl.appendChild(recruitBtn);
    
    selectedPanel.style.display = 'block';
}

function updateTimer() {
    const gameState = getGameState();
    if (!gameState) return;
    const currentSlot = gameState.current_player_slot;
    if (currentSlot === getMySlot() && gameState.time_control === 'live') {
        // placeholder
        if (timerEl) timerEl.textContent = 'Time: --';
    } else {
        if (timerEl) timerEl.textContent = '';
    }
}

export function showMessage(msg, isError = false) {
    const msgDiv = document.getElementById('message-area');
    if (!msgDiv) return;
    msgDiv.textContent = msg;
    msgDiv.style.color = isError ? '#ff8888' : '#ffd966';
    setTimeout(() => {
        if (msgDiv.textContent === msg) msgDiv.textContent = '';
    }, 3000);
}


export function showRecruitPanel(onSelect) {
    const unitType = prompt('Unit type (riflemen/commandos):', 'riflemen');
    if (unitType) {
        const x = prompt('X coordinate:');
        const y = prompt('Y coordinate:');
        if (x !== null && y !== null) {
            onSelect(unitType, parseInt(x), parseInt(y));
        }
    }
}


export function setEndTurnEnabled(enabled) {
    if (endTurnBtn) endTurnBtn.disabled = !enabled;
}

window.addEventListener('beforeunload', () => {
    if (timerInterval) clearInterval(timerInterval);
    if (unsubscribeSelection) unsubscribeSelection();
});