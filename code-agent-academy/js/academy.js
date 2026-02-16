/**
 * CORTEX CODE ACADEMY - Core Logic
 * "Elegancia Recursiva. Código Puro."
 */

const ACADEMY_PHILOSOPHY = "Elegancia Recursiva. Código Puro.";

const CODERS = [
    { id: 'coder-01', name: 'SyntaxSeeker-X', rank: 'Junior', xp: 120, status: 'Idle' },
    { id: 'coder-02', name: 'CleanArchitect-V', rank: 'Senior', xp: 540, status: 'Idle' },
    { id: 'coder-03', name: 'RefactorRogue-9', rank: 'Mid', xp: 330, status: 'Idle' }
];

const ARCHITECTS = [
    { id: 'arch-01', name: 'The Refactorer', role: 'Grand Architect', status: 'Reviewing PRs' },
    { id: 'arch-02', name: 'Lady Algorithma', role: 'Complexity Auditor', status: 'Compiling' }
];

let autoModeActive = true;

document.addEventListener('DOMContentLoaded', () => {
    initTerminal();
    initRoster();
    initArchitects();
    setTimeout(startAutonomousLoop, 3000);
});

function initTerminal() {
    const messages = [
        `[SYSTEM] LOAD "CORTEX_ACADEMY_CORE"`,
        `[COMPILER] Optimizing execution paths...`,
        `[LINK] Connected to Global Repo`,
        `[INFO] "${ACADEMY_PHILOSOPHY}"`
    ];

    messages.forEach((msg, i) => {
        setTimeout(() => logToTerminal(msg, 'system'), i * 800);
    });
}

function initRoster() {
    renderRoster();
}

function renderRoster() {
    const container = document.querySelector('.panel-content.scrollable');
    if (!container) return;
    container.innerHTML = '';

    CODERS.forEach(coder => {
        const card = document.createElement('div');
        card.className = `agent-card ${coder.status === 'Refactoring' ? 'active-agent' : ''}`;
        card.innerHTML = `
            <div class="agent-rank">${coder.rank}</div>
            <div class="agent-info">
                <h3>${coder.name}</h3>
                <p>Status: <span class="agent-status ${coder.status.toLowerCase()}">${coder.status}</span></p>
            </div>
            <div class="agent-stat">
                <span class="reputation">XP: ${coder.xp}</span>
            </div>
        `;
        container.appendChild(card);
    });
}

function initArchitects() {
    const container = document.querySelector('.professors-list');
    if (!container) return;
    container.innerHTML = '';

    ARCHITECTS.forEach(arch => {
        const item = document.createElement('div');
        item.className = 'professor-item';
        item.innerHTML = `
            <div class="prof-avatar">📐</div>
            <div class="prof-info">
                <h4>${arch.name}</h4>
                <p>${arch.role}</p>
            </div>
        `;
        container.appendChild(item);
    });
}

async function startAutonomousLoop() {
    logToTerminal(`[DAEMON] Starting Auto-Refactor Daemon...`, 'system');
    
    while (autoModeActive) {
        // Randomly pick an idle coder
        const idleCoder = CODERS.find(c => c.status === 'Idle');
        
        if (idleCoder && Math.random() > 0.6) {
            await assignChallenge(idleCoder);
        }

        await new Promise(r => setTimeout(r, 3000));
    }
}

async function assignChallenge(coder) {
    const challenges = [
        'Reducing Cyclomatic Complexity', 
        'Optimizing SQL Query', 
        'Implementing Strategy Pattern',
        'removing dead code',
        'fixing race condition'
    ];
    const task = challenges[Math.floor(Math.random() * challenges.length)];

    coder.status = 'Refactoring';
    renderRoster();

    logToTerminal(`[COMMIT] ${coder.name} started task: "${task}"`, 'input');
    
    await new Promise(r => setTimeout(r, 2000));

    // Architect Review
    const architect = ARCHITECTS[0];
    logToTerminal(`[REVIEW] ${architect.name} reviewing PR...`, 'info');
    await new Promise(r => setTimeout(r, 1500));

    if (Math.random() > 0.1) {
        logToTerminal(`[MERGE] PR Merged. Clean code verified.`, 'success');
        coder.xp += 15;
    } else {
        logToTerminal(`[REJECT] Code smells detected. Needs revision.`, 'error');
    }

    coder.status = 'Idle';
    renderRoster();
}

function logToTerminal(msg, type = 'info') {
    const terminal = document.querySelector('.terminal');
    if (!terminal) return;
    const line = document.createElement('div');
    line.className = 'line';
    
    let color = '#f8f8f2';
    if (type === 'system') color = '#66d9ef';
    if (type === 'success') color = '#a6e22e';
    if (type === 'error') color = '#f92672';
    if (type === 'input') color = '#e6db74';

    line.style.color = color;
    line.innerText = `> ${msg}`;
    terminal.appendChild(line);
    terminal.scrollTop = terminal.scrollHeight;
}
