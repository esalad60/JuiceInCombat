import {
    connectSocket,
    createMatch,
    joinMatch,
} from './network/socket_client.js';


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


connectSocket(null, {
    onMatchCreated: (data) => {
        showLobbyMessage(
            `Match #${data.match_id} created. Waiting for another player...`
        );
    },

    onMatchReady: (payload) => {
        console.log("MATCH READY RECEIVED IN LOBBY:", payload);

        const matchId = payload.match_id;

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

        joinMatch(matchId);
    });
});