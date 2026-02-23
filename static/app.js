/**
 * AI Avatar - Frontend aplikace
 */
const API_BASE = '';

let sessionId = null;
let currentAudio = null;

const messagesEl = document.getElementById('messages');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const textOnlyCheckbox = document.getElementById('textOnly');

function addMessage(content, role, audioAvailable = false) {
    const div = document.createElement('div');
    div.className = `message ${role}`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = content;

    const metaDiv = document.createElement('div');
    metaDiv.className = 'message-meta';
    metaDiv.textContent = role === 'user' ? 'Vy' : 'Avatar';

    div.appendChild(contentDiv);
    div.appendChild(metaDiv);

    if (role === 'avatar' && audioAvailable) {
        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'message-actions';
        const btn = document.createElement('button');
        btn.className = 'btn-audio';
        btn.textContent = '▶ Přehrát hlas';
        btn.onclick = () => playAudio(content);
        actionsDiv.appendChild(btn);
        div.appendChild(actionsDiv);
    }

    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

function addLoading() {
    const div = document.createElement('div');
    div.className = 'message avatar';
    div.id = 'loading-msg';
    div.innerHTML = `
        <div class="message-content loading">
            <span class="loading-dot"></span>
            <span class="loading-dot"></span>
            <span class="loading-dot"></span>
            <span style="margin-left: 0.5rem">Přemýšlím...</span>
        </div>
    `;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

function removeLoading() {
    const el = document.getElementById('loading-msg');
    if (el) el.remove();
}

async function playAudio(text) {
    if (currentAudio) {
        currentAudio.pause();
        currentAudio = null;
    }

    try {
        const res = await fetch(`${API_BASE}/api/audio?text=${encodeURIComponent(text)}`);
        if (!res.ok) throw new Error('Audio nedostupné');
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        currentAudio = audio;
        audio.onended = () => URL.revokeObjectURL(url);
        await audio.play();
    } catch (err) {
        console.error(err);
        alert('Nepodařilo se přehrát hlas.');
    }
}

async function sendMessage() {
    const message = userInput.value.trim();
    if (!message) return;

    userInput.value = '';
    sendBtn.disabled = true;
    addMessage(message, 'user');
    addLoading();

    try {
        const res = await fetch(`${API_BASE}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message,
                session_id: sessionId,
                text_only: textOnlyCheckbox.checked,
            }),
        });

        const data = await res.json();
        sessionId = data.session_id;
        removeLoading();
        addMessage(data.response, 'avatar', data.audio_available);
    } catch (err) {
        removeLoading();
        addMessage('Omlouvám se, momentálně jsem nedostupný.', 'avatar', false);
        console.error(err);
    } finally {
        sendBtn.disabled = false;
    }
}

sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});
