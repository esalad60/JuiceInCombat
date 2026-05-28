// frontend/static/js/network/socket_client.js
import { io } from "https://cdn.socket.io/4.5.4/socket.io.esm.min.js";
import { setMySlot, updateGameState, getMatchId, setMatchId } from '../game/client_state.js';

let socket = null;
let currentMatchId = null;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;

let callbacks = {};


export function connectSocket(matchId, handlers) {
    currentMatchId = matchId;
    callbacks = handlers;

    socket = io('/game', {
        path: '/socket.io',
        transports: ['websocket'],
        reconnection: true,
        reconnectionAttempts: MAX_RECONNECT_ATTEMPTS,
        reconnectionDelay: 1000,
    });

    socket.on('connect', () => {
        console.log('Socket connected, joining match', currentMatchId);
        reconnectAttempts = 0;
        socket.emit('join_match', { match_id: currentMatchId });
    });

    socket.on('joined', (data) => {
        console.log('Joined match:', data);
        setMySlot(data.player_slot);
        // don't try to render until the match actually starts (game_started or game_state)
        if (data.game_state && callbacks.onGameState) {
            callbacks.onGameState(data.game_state);
        }
    });

    socket.on('game_state', (data) => {
        updateGameState(data);
        if (callbacks.onGameState) callbacks.onGameState(data);
    });

    socket.on('action_applied', (result) => {
        if (callbacks.onActionApplied) callbacks.onActionApplied(result);
    });

    socket.on('turn_changed', (payload) => {
        // payload contains next_slot (and sometimes turn)
        if (callbacks.onTurnChanged) callbacks.onTurnChanged(payload.next_slot);
    });

    socket.on('game_ended', (payload) => {
        if (callbacks.onGameEnded) callbacks.onGameEnded(payload.winner_slot);
    });

    socket.on('game_started', (payload) => {
        if (callbacks.onGameStarted) callbacks.onGameStarted(payload.game_state);
    });

    socket.on('match_created', (data) => {
        console.log('Match created:', data);
        // Could redirect to game page; handled by lobby page instead.
    });

    socket.on('error', (err) => {
        console.error('Server error:', err);
        if (callbacks.onError) callbacks.onError(err);
    });

    socket.on('disconnect', (reason) => {
        console.warn('Socket disconnected:', reason);
        if (callbacks.onError) callbacks.onError({ message: 'Disconnected from server' });
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
        socket.emit('action', { match_id: currentMatchId, action });
    } else {
        console.warn('Cannot send action: socket not connected');
        if (callbacks.onError) callbacks.onError({ message: 'Not connected to server' });
    }
}


export function sendEndTurn() {
    if (socket && socket.connected) {
        socket.emit('end_turn', { match_id: currentMatchId });
    } else {
        console.warn('Cannot end turn: socket not connected');
        if (callbacks.onError) callbacks.onError({ message: 'Not connected to server' });
    }
}


export function createMatch(mapId, timeControl) {
    if (socket && socket.connected) {
        socket.emit('create_match', { map_id: mapId, time_control: timeControl });
    } else {
        console.error('Cannot create match: socket not connected');
    }
}

export function joinMatch(matchId) {
    if (socket && socket.connected) {
        socket.emit('join_match', { match_id: matchId });
        currentMatchId = matchId;
        setMatchId(matchId);
    } else {
        console.error('Cannot join match: socket not connected');
    }
}

export function disconnect() {
    if (socket) {
        socket.disconnect();
        socket = null;
    }
}