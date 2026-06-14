import { getUnit, getMySlot, getMyResources, getGameState, isMyTurn } from '../game/client_state.js';
import { getSelectedUnit } from '../game/selection.js';

let cb = {};
let turnIndicatorEl, cashEl, timerEl, endTurnBtn, panelEl, statsEl, actionsEl, panelTitleEl;
let weaponPanelEl, weaponTitleEl, weaponStatsEl;

export function initHUD(callbacks) {
    cb = callbacks || {};
    turnIndicatorEl = document.getElementById('turn-indicator');
    cashEl          = document.getElementById('cash');
    timerEl         = document.getElementById('turn-timer');
    endTurnBtn      = document.getElementById('end-turn-btn');
    panelEl         = document.getElementById('selected-unit-panel');
    statsEl         = document.getElementById('unit-stats');
    actionsEl       = document.getElementById('unit-actions');
    panelTitleEl    = document.getElementById('panel-title');
    weaponPanelEl   = document.getElementById('weapon-info-panel');
    weaponTitleEl   = document.getElementById('weapon-info-title');
    weaponStatsEl   = document.getElementById('weapon-info-stats');

    if (endTurnBtn) {
        endTurnBtn.addEventListener('click', () => {
            if (isMyTurn() && cb.onEndTurn) cb.onEndTurn();
        });
    }
}

export function updateHUD(gameState) {
    if (!gameState) return;
    const currentSlot = gameState.current_player_slot;
    if (turnIndicatorEl)
        turnIndicatorEl.textContent = isMyTurn()
            ? `Your Turn // Round ${gameState.turn}`
            : `Enemy Turn // P${currentSlot + 1}`;
    const res = getMyResources();
    if (cashEl) cashEl.textContent = `$${res.cash || 0}`;
    if (endTurnBtn) endTurnBtn.disabled = !isMyTurn();
}

function showPanel() {
    if (!panelEl) return;
    panelEl.classList.remove('hidden');
}

function statRow(label, value) {
    return `<div class="stat"><span class="jic-label">${label}</span><span class="jic-value">${value}</span></div>`;
}

const EFFECT_ICONS = {
    mark:        { glyph: '', label: 'Marked', desc: 'Takes increased damage' },
    incendiary:  { glyph: '', label: 'Burning', desc: 'Loses HP each turn' },
    cripple:     { glyph: '', label: 'Crippled', desc: 'Movement reduced' },
    sacrafice:   { glyph: '', label: 'Sacrifice', desc: 'Detonates on attack' },
    explosive:   { glyph: '', label: 'Explosive', desc: 'Explosive payload' },
    regen:       { glyph: '', label: 'Regen', desc: 'Heals each turn', trait: true },
    radio:       { glyph: '', label: 'Radio', desc: 'Comms support', trait: true },
    salvage:     { glyph: '', label: 'Salvage', desc: 'Gets resources', trait: true },
    climb:       { glyph: '', label: 'Climb', desc: 'Ignores cliffs', trait: true },
};

function effectChip(type, { duration = null, trait = false } = {}) {
    const key = String(type || '').toLowerCase();
    const info = EFFECT_ICONS[key] || { glyph: '•', label: type, desc: '' };
    const tip = `${info.label}${info.desc ? ' — ' + info.desc : ''}` +
                (duration != null ? ` (${duration}t)` : '');
    const counter = duration != null
        ? `<span class="status-count">${duration}</span>`
        : '';
    const cls = (trait || info.trait) ? 'status-chip status-trait' : 'status-chip';
    return `<span class="${cls}" title="${tip}">${info.glyph}${counter}</span>`;
}

function statusIconsRow(unit) {
    const chips = [];

    for (const eff of (unit.status_effects || [])) {
        chips.push(effectChip(eff.type, { duration: eff.duration }));
    }
    for (const t of (unit.traits || [])) {
        chips.push(effectChip(t.type, { trait: true }));
    }

    if (chips.length === 0) return '';
    return `<div class="status-row">${chips.join('')}</div>`;
}

export function showUnitPanel(unit, readOnly = false, capturable = null) {
    if (!panelEl || !unit) return;
    showPanel();
    if (panelTitleEl)
        panelTitleEl.innerHTML = readOnly
            ? `${unit.type} <span class="recon-tag">View</span>`
            : `${unit.type}`;

    statsEl.innerHTML =
        statRow('HP', unit.hp) +
        statRow('Armor', unit.armor) +
        statRow('Move', `${unit.movement_remaining}/${unit.max_movement}`) +
        statRow('Fired', unit.has_fired_weapon ? 'Yes' : 'No') +
        statusIconsRow(unit);

    actionsEl.innerHTML = '';
    actionsEl.style.flexDirection = 'row';

    if (readOnly) {
        for (const weapon of (unit.weapons || [])) {
            const btn = document.createElement('button');
            btn.textContent = `${weapon.name} (R${weapon.range})`;
            btn.className = 'jic-btn jic-btn-rust';
            btn.style.fontSize = '11px';
            btn.style.padding = '6px 10px';
            btn.disabled = true;          // can't fire off-turn
            // still let the player inspect the weapon's stats
            btn.addEventListener('click', () => showWeaponInfo(weapon));
            actionsEl.appendChild(btn);
        }
        return;
    }

    if (!unit.has_fired_weapon) {
        for (const weapon of (unit.weapons || [])) {
            const btn = document.createElement('button');
            btn.textContent = `${weapon.name} (R${weapon.range})`;
            btn.className = 'jic-btn jic-btn-rust';
            btn.style.fontSize = '11px';
            btn.style.padding = '6px 10px';
            btn.addEventListener('click', () => {
                if (cb.onWeaponSelected) cb.onWeaponSelected(unit.id, weapon.name);
            });
            actionsEl.appendChild(btn);
        }
    } else {
        const note = document.createElement('div');
        note.className = 'jic-label';
        note.textContent = 'Already fired this turn';
        actionsEl.appendChild(note);
    }

    // Capture button — shown when the unit is adjacent to a capturable building
    // and hasn't moved this turn.
    if (capturable && !unit.has_moved) {
        const capBtn = document.createElement('button');
        capBtn.textContent = 'Capture';
        capBtn.className = 'jic-btn jic-btn-gold';
        capBtn.style.fontSize = '11px';
        capBtn.style.padding = '6px 10px';
        capBtn.addEventListener('click', () => {
            if (cb.onCaptureRequested) cb.onCaptureRequested(unit.id, capturable.id);
        });
        actionsEl.appendChild(capBtn);
    }
}

export function showWeaponInfo(weapon) {
    if (!weaponPanelEl || !weapon) return;
    weaponPanelEl.classList.remove('hidden');
    if (weaponTitleEl) weaponTitleEl.textContent = weapon.name || 'Weapon';

    let html =
        statRow('Damage', weapon.damage) +
        statRow('AP', weapon.ap) +
        statRow('Range', weapon.range);
    if (weapon.type) html += statRow('Type', weapon.type);

    // if (weapon.perks && weapon.perks.length) {
    //     html += '<div class="jic-divider"></div>';
    //     html += '<div class="jic-label">Perks</div>';
    //     for (const p of weapon.perks) {
    //         html += statRow(p.type, p.duration ? `${p.duration}t` : '—');
    //     }
    // }

    weaponStatsEl.innerHTML = html;
}

export function hideWeaponInfo() {
    if (weaponPanelEl) weaponPanelEl.classList.add('hidden');
}

// ---- Read-only enemy unit panel (recon: stats only, no actions) ----
export function showEnemyUnitPanel(unit) {
    if (!panelEl || !unit) return;
    showPanel();
    if (panelTitleEl) panelTitleEl.innerHTML = `${unit.type} <span class="recon-tag">Recon</span>`;

    let html =
        statRow('HP', unit.hp) +
        statRow('Armor', unit.armor) +
        statRow('Move', `${unit.movement_remaining}/${unit.max_movement}`);
    for (const w of (unit.weapons || [])) {
        html += statRow(`Wpn: ${w.name}`, `DMG ${w.damage} / AP ${w.ap} / R${w.range}`);
    }
    html += statusIconsRow(unit);
    statsEl.innerHTML = html;
    actionsEl.innerHTML = '<div class="jic-label">Enemy unit — view only</div>';
}

export function showBuildingPanel(building, owned) {
    if (!panelEl || !building) return;
    showPanel();
    const label = building.is_capital ? 'Headquarters' : (building.type || 'Building');
    if (panelTitleEl)
        panelTitleEl.innerHTML = owned ? label : `${label} <span class="recon-tag">Recon</span>`;

    statsEl.innerHTML =
        statRow('HP', building.hp) +
        statRow('Armor', building.armor) +
        statRow('Type', building.is_capital ? 'Capital' : (building.type || '—'));

    actionsEl.innerHTML = '';
    actionsEl.style.flexDirection = 'row';

    if (owned) {
        const btn = document.createElement('button');
        btn.textContent = 'Recruit';
        btn.className = 'jic-btn';
        btn.style.fontSize = '12px';
        btn.addEventListener('click', () => {
            if (cb.onRecruitRequested) cb.onRecruitRequested(building.x, building.y);
        });
        actionsEl.appendChild(btn);
    } else {
        actionsEl.innerHTML = '<div class="jic-label">Enemy building — view only</div>';
    }
}

// ---- Recruit list ----
export function showRecruitList(units) {
    if (!panelEl) return;
    showPanel();
    if (panelTitleEl) panelTitleEl.textContent = 'Recruit Unit';

    const cash = (getMyResources().cash) || 0;
    statsEl.innerHTML = statRow('Available Cash', `$${cash}`);
    actionsEl.innerHTML = '';
    actionsEl.style.flexDirection = 'column';

    if (!units || units.length === 0) {
        actionsEl.innerHTML = '<div class="jic-label">No units available</div>';
        return;
    }

    for (const u of units) {
        const affordable = cash >= u.cost;
        const btn = document.createElement('button');
        btn.textContent = `${u.name} — $${u.cost}`;
        btn.className = affordable ? 'jic-btn jic-btn-block' : 'jic-btn jic-btn-block';
        btn.style.fontSize = '12px';
        btn.style.marginBottom = '6px';
        btn.disabled = !affordable;
        btn.addEventListener('click', () => {
            if (affordable && cb.onRecruitUnitChosen) cb.onRecruitUnitChosen(u.unit_type);
        });
        actionsEl.appendChild(btn);
    }
}

export function hidePanels() {
    if (panelEl) panelEl.classList.add('hidden');
    if (actionsEl) actionsEl.style.flexDirection = 'row';
    hideWeaponInfo();
}

export function showMessage(msg, isError = false) {
    const el = document.getElementById('message-area');
    if (!el) return;
    el.textContent = msg;
    el.style.display = 'block';
    el.style.color = isError ? '#e9b3a6' : 'var(--jic-cream)';
    clearTimeout(el._t);
    el._t = setTimeout(() => { if (el.textContent === msg) el.style.display = 'none'; }, 3000);
}

export function setEndTurnEnabled(enabled) {
    if (endTurnBtn) endTurnBtn.disabled = !enabled;
}