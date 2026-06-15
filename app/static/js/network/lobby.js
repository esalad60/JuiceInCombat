import {
    connectSocket,
    createMatch,
    joinMatch,
} from './network/socket_client.js';


let createdMatchId = null;


function showLobbyMessage(message, isError = false) {
    const box = document.getElementById('lobby-message');

    if (!box) {
        console.log(message);
        return;
    }

    box.textContent = message;
    box.classList.remove('hidden');
    box.classList.toggle('jic-flash-error', isError);
    box.classList.toggle('jic-flash-ok', !isError);
}


function addCreatedMatchRow(matchId) {
    const openMatchesPanel = document.getElementById('open-matches-list');

    if (!openMatchesPanel) {
        return;
    }

    const emptyText = openMatchesPanel.querySelector('[data-empty-matches]');
    if (emptyText) {
        emptyText.remove();
    }

    const row = document.createElement('div');
    row.className = 'jic-row';
    row.innerHTML = `
        <div class="text-sm">
            <span class="jic-value">#${matchId}</span> — Created match<br>
            <span class="jic-label">1/2 players — waiting for opponent</span>
        </div>
        <button type="button" class="jic-btn" disabled>
            Waiting...
        </button>
    `;

    openMatchesPanel.prepend(row);
}


connectSocket(null, {
    onMatchCreated: (data) => {
        createdMatchId = data.match_id;

        showLobbyMessage(
            `Match #${createdMatchId} created. Waiting for another player...`
        );

        addCreatedMatchRow(createdMatchId);
    },

    onMatchReady: (payload) => {
        const matchId = payload.match_id || createdMatchId;

        if (!matchId) {
            console.error("match_ready missing match_id:", payload);
            showLobbyMessage("Match is ready, but match ID is missing.", true);
            return;
        }

        window.location.href = `/game/${matchId}`;
    },

    onError: (err) => {
        console.error("Lobby socket error:", err);
        showLobbyMessage(err.message || "Socket error", true);
    },
});


const createForm = document.getElementById('create-match-form');

if (createForm) {
    createForm.addEventListener('submit', (event) => {
        event.preventDefault();

        const formData = new FormData(createForm);
        const mapId = formData.get('map_id');
        const timeControl = formData.get('time_control') || 'live';

        if (!mapId) {
            showLobbyMessage("Please choose a map.", true);
            return;
        }

        showLobbyMessage("Creating match...");

        createMatch(mapId, timeControl);
    });
}


document.querySelectorAll('.join-match-btn').forEach((button) => {
    button.addEventListener('click', () => {
        const matchId = button.dataset.matchId;

        if (!matchId) {
            showLobbyMessage("Missing match ID.", true);
            return;
        }

        showLobbyMessage(`Joining match #${matchId}...`);

        joinMatch(matchId);
    });
});