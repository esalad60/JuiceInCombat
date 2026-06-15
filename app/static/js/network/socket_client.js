// frontend/static/js/network/socket_client.js
import { io } from "https://cdn.socket.io/4.5.4/socket.io.esm.min.js";

import {
    setMySlot,
    updateGameState,
    setMatchId,
    setUnitCatalog,
} from '../game/client_state.js';

let socket = null;
let currentMatchId = null;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;

let callbacks = {};


function handleIncomingGameState(state) {
    if (!state) return;

    updateGameState(state);

    if (callbacks.onGameState) {
        callbacks.onGameState(state);
    }
}


export function connectSocket(matchId, handlers) {
    currentMatchId = matchId;
    callbacks = handlers || {};

    if (currentMatchId !== null && currentMatchId !== undefined) {
        setMatchId(currentMatchId);
    }

    socket = io('/game', {
        path: '/socket.io',
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionAttempts: MAX_RECONNECT_ATTEMPTS,
        reconnectionDelay: 1000,
    });

    socket.on('connect', () => {
        console.log('Socket connected, joining match', currentMatchId);
        reconnectAttempts = 0;

        if (currentMatchId !== null && currentMatchId !== undefined) {
            socket.emit('join_match', { match_id: currentMatchId });
        }
    });

    socket.on('joined', (data) => {
        console.log('Joined match:', data);

        currentMatchId = data.match_id;
        setMatchId(data.match_id);
        setMySlot(data.player_slot);

        if (data.unit_catalog) {
            setUnitCatalog(data.unit_catalog);
        }

        if (data.game_state) {
            handleIncomingGameState(data.game_state);
        }
    });

		socket.on("game_started", (payload) => {
		const matchId = payload.match_id;

		if (!matchId) {
			console.error("game_started missing match_id:", payload);
			return;
		}

		window.location.href = `/game/${matchId}`;
	});

    socket.on('game_state', (data) => {
        handleIncomingGameState(data);
    });

    socket.on('action_applied', (result) => {
        if (callbacks.onActionApplied) {
            callbacks.onActionApplied(result);
        }
    });

    socket.on('turn_changed', (payload) => {
        if (callbacks.onTurnChanged) {
            callbacks.onTurnChanged(payload.next_slot);
        }
    });

    socket.on("game_ended", (payload) => {
		const winnerSlot = payload.winner_slot;
		const matchId = payload.match_id || currentMatchId;

		window.location.href = `/win/${matchId}/${winnerSlot}`;
	});

    socket.on('match_created', (data) => {
        console.log('Match created:', data);

        currentMatchId = data.match_id;
        setMatchId(data.match_id);

        if (callbacks.onMatchCreated) {
            callbacks.onMatchCreated(data);
        }
    });

    socket.on('error', (err) => {
        console.error('Server error:', err);

        if (callbacks.onError) {
            callbacks.onError(err);
        }
    });

    socket.on('disconnect', (reason) => {
        console.warn('Socket disconnected:', reason);

        if (callbacks.onError) {
            callbacks.onError({ message: 'Disconnected from server' });
        }
    });

    socket.on('connect_error', (err) => {
        console.error('Connection error:', err);
        reconnectAttempts++;

        if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS && callbacks.onError) {
            callbacks.onError({ message: 'Unable to connect to server' });
        }
    });
}


export function sendAction(action) {
    if (socket && socket.connected) {
        socket.emit('action', {
            match_id: currentMatchId,
            action,
        });
    } else {
        console.warn('Cannot send action: socket not connected');

        if (callbacks.onError) {
            callbacks.onError({ message: 'Not connected to server' });
        }
    }
}


export function sendEndTurn() {
    if (socket && socket.connected) {
        socket.emit('end_turn', {
            match_id: currentMatchId,
        });
    } else {
        console.warn('Cannot end turn: socket not connected');

        if (callbacks.onError) {
            callbacks.onError({ message: 'Not connected to server' });
        }
    }
}


export function createMatch(mapId, timeControl) {
    if (socket && socket.connected) {
        socket.emit('create_match', {
            map_id: mapId,
            time_control: timeControl,
        });
    } else {
        console.error('Cannot create match: socket not connected');

        if (callbacks.onError) {
            callbacks.onError({ message: 'Not connected to server' });
        }
    }
}


export function joinMatch(matchId) {
    currentMatchId = matchId;
    setMatchId(matchId);

    if (socket && socket.connected) {
        socket.emit('join_match', {
            match_id: matchId,
        });
    } else {
        console.error('Cannot join match: socket not connected');

        if (callbacks.onError) {
            callbacks.onError({ message: 'Not connected to server' });
        }
    }
}


export function disconnect() {
    if (socket) {
        socket.disconnect();
        socket = null;
    }
}