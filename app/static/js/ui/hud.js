import { getUnit, getMySlot, getMyResources, getGameState, isMyTurn } from '../game/client_state.js';
import { getSelectedUnit } from '../game/selection.js';

let cb = {};   // callbacks from main.js
let turnIndicatorEl, cashEl, timerEl, endTurnBtn, panelEl, statsEl, actionsEl;

export function initHUD(callbacks) {
    cb = callbacks || {};
    turnIndicatorEl = document.getElementById('turn-indicator');
    cashEl          = document.getElementById('cash');
    timerEl         = document.getElementById('turn-timer');
    endTurnBtn      = document.getElementById('end-turn-btn');
    panelEl         = document.getElementById('selected-unit-panel');
    statsEl         = document.getElementById('unit-stats');
    actionsEl       = document.getElementById('unit-actions');

    if (endTurnBtn) {
        endTurnBtn.addEventListener('click', () => {
            if (isMyTurn() && cb.onEndTurn) cb.onEndTurn();
        });
    }
}

export function updateHUD(gameState) {
    if (!gameState) return;
    const currentSlot = gameState.current_player_slot;
    if (turnIndicatorEl) turnIndicatorEl.textContent = isMyTurn() ? `Your Turn • Round ${gameState.turn}` : `Enemy Turn • P${currentSlot + 1}`;
    const res = getMyResources();
    if (cashEl) cashEl.textContent = `$${res.cash || 0}`;
    if (endTurnBtn) endTurnBtn.disabled = !isMyTurn();
}

export function showUnitPanel(unit) {
    if (!panelEl || !unit) return;
    panelEl.classList.remove('hidden');
    panelEl.style.display = 'block';

    statsEl.innerHTML = `
        <div><strong>${unit.type}</strong></div>
        <div>HP: ${unit.hp}</div>
        <div>Armor: ${unit.armor}</div>
        <div>Move: ${unit.movement_remaining}/${unit.max_movement}</div>
        <div>Fired: ${unit.has_fired_weapon ? 'Yes' : 'No'}</div>
    `;
    actionsEl.innerHTML = '';

    if (!unit.has_fired_weapon) {
        for (const weapon of (unit.weapons || [])) {
            const btn = document.createElement('button');
            btn.textContent = `${weapon.name} (rng ${weapon.range})`;
            btn.className = 'bg-red-700/90 hover:bg-red-600 border border-red-400/20 px-3 py-2 rounded-xl text-xs font-semibold';
            btn.addEventListener('click', () => {
                if (cb.onWeaponSelected) cb.onWeaponSelected(unit.id, weapon.name);
            });
            actionsEl.appendChild(btn);
        }
    } else {
        const note = document.createElement('div');
        note.className = 'text-xs text-gray-400';
        note.textContent = 'Already fired this turn';
        actionsEl.appendChild(note);
    }
}

export function showRecruitList(units) {
    if (!panelEl) return;
    panelEl.classList.remove('hidden');
    panelEl.style.display = 'block';

    const res = getMyResources();
    const cash = res.cash || 0;

    statsEl.innerHTML = `<div><strong>Recruit a unit</strong></div>
        <div class="text-xs text-gray-400">Cash: ${cash}</div>`;
    actionsEl.innerHTML = '';
    actionsEl.style.flexDirection = 'column';

    if (!units || units.length === 0) {
        const d = document.createElement('div');
        d.className = 'text-xs text-gray-400';
        d.textContent = 'No units available';
        actionsEl.appendChild(d);
        return;
    }

    for (const u of units) {
        const affordable = cash >= u.cost;
        const btn = document.createElement('button');
        btn.textContent = `${u.name} - $${u.cost}`;
        btn.className = affordable ? 'bg-emerald-700 hover:bg-emerald-600 px-3 py-2 rounded-xl text-xs mb-1 font-semibold' : 'bg-gray-700 px-3 py-2 rounded-xl text-xs mb-1 opacity-50 cursor-not-allowed';
        btn.disabled = !affordable;
        btn.addEventListener('click', () => {
            if (affordable && cb.onRecruitUnitChosen) cb.onRecruitUnitChosen(u.unit_type);
        });
        actionsEl.appendChild(btn);
    }
}

export function hidePanels() {
    if (panelEl) {
        panelEl.classList.add('hidden');
        panelEl.style.display = 'none';
    }
    if (actionsEl) actionsEl.style.flexDirection = 'row';
}

export function showMessage(msg, isError = false) {
    const el = document.getElementById('message-area');
    if (!el) return;
    el.textContent = msg;
    el.style.color = isError ? '#ff8888' : '#ffd966';
    setTimeout(() => { if (el.textContent === msg) el.textContent = ''; }, 3000);
}

export function setEndTurnEnabled(enabled) {
    if (endTurnBtn) endTurnBtn.disabled = !enabled;
}