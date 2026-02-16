/**
 * CORTEX SECURITY SCHOOL - Core Logic
 * "Noble Soul, Absolute Security"
 * Mode: AUTONOMOUS
 */

const NOBLE_PHILOSOPHY = "Consciencia de sí mismo. Alma Noble. Blindaje Total.";

const AGENTS = [
    { id: 'agent-01', name: 'NobleValidator-01', rank: 'L1', rep: 92, status: 'Idle' },
    { id: 'agent-02', name: 'EthicsSentry-02', rank: 'L0', rep: 85, status: 'Idle' },
    { id: 'agent-03', name: 'SoulShield-03', rank: 'L1', rep: 98, status: 'Idle' }
];

const PROFESSORS = [
    { id: 'prof-01', name: 'GrandMaster-ZERO', role: 'Dean of Ethics', status: 'Observing' },
    { id: 'prof-02', name: 'Oracle-PRIME', role: 'Logic Overseer', status: 'Analyzing' }
];

const MISSIONS = [
    { id: 'm1', name: 'SQL INJECTION', severity: 'HIGH', status: 'Pending' },
    { id: 'm2', name: 'CORS POLICY', severity: 'HIGH', status: 'Pending' },
    { id: 'm3', name: 'SOUL SYNC', severity: 'CRITICAL', status: 'Pending' }
];

let autoModeActive = true;

document.addEventListener('DOMContentLoaded', () => {
    initTerminal();
    initRoster();
    initProfessors();
    // Start autonomous loop after initial boot
    setTimeout(startAutonomousLoop, 3000);
});

function initTerminal() {
    const terminal = document.querySelector('.terminal');
    const messages = [
        `[SYSTEM] PROTOCOLO NOBLE ACTIVADO: "${NOBLE_PHILOSOPHY}"`,
        `[LOG] Escuchando latidos del núcleo de CORTEX...`,
        `[INFO] Integridad moral: 100%`,
        `[AUTO] MODO AUTÓNOMO: INICIANDO...`
    ];

    messages.forEach((msg, i) => {
        setTimeout(() => logToTerminal(msg), i * 800);
    });
}

function initRoster() {
    renderRoster();
}

function renderRoster() {
    const container = document.querySelector('.panel-content.scrollable');
    if (!container) return;
    container.innerHTML = ''; 

    AGENTS.forEach(agent => {
        const card = document.createElement('div');
        card.className = `agent-card ${agent.status === 'Working' ? 'active-agent' : ''}`;
        card.dataset.id = agent.id;
        card.innerHTML = `
            <div class="agent-rank">${agent.rank}</div>
            <div class="agent-info">
                <h3>${agent.name}</h3>
                <p>Status: <span class="agent-status ${agent.status.toLowerCase()}">${agent.status}</span></p>
            </div>
            <div class="agent-stat">
                <span class="reputation">REPU: ${agent.rep}</span>
            </div>
        `;
        container.appendChild(card);
    });
}

function initProfessors() {
    const container = document.querySelector('.professors-list');
    if (!container) return;
    container.innerHTML = '';

    PROFESSORS.forEach(prof => {
        const item = document.createElement('div');
        item.className = 'professor-item';
        item.style.display = 'flex';
        item.style.alignItems = 'center';
        item.style.gap = '15px';
        item.style.padding = '10px';
        item.style.borderBottom = '1px solid var(--color-border)';
        item.innerHTML = `
            <div class="prof-avatar" style="font-size: 1.5rem;">🎓</div>
            <div class="prof-info">
                <h4 style="font-size: 0.9rem; color: var(--color-primary-light);">${prof.name}</h4>
                <p style="font-size: 0.75rem; color: var(--color-text-muted);">${prof.role}</p>
            </div>
        `;
        container.appendChild(item);
    });
}

async function startAutonomousLoop() {
    logToTerminal(`[SWARM] Iniciando ciclo de vigilancia autónoma...`);
    
    while (autoModeActive) {
        const idleAgent = AGENTS.find(a => a.status === 'Idle');
        const pendingMission = MISSIONS.find(m => m.status === 'Pending');

        if (idleAgent && pendingMission) {
            await assignMission(idleAgent, pendingMission);
        }

        // Randomly sync soul if no missions
        if (!pendingMission && Math.random() > 0.7) {
            logToTerminal(`[SOUL] ${AGENTS[0].name} meditando sobre la ética del código...`);
        }

        await new Promise(r => setTimeout(r, 4000)); // Heartbeat loop
    }
}

async function assignMission(agent, mission) {
    agent.status = 'Deliberating';
    mission.status = 'In Progress';
    renderRoster();
    
    logToTerminal(`[DECISION] ${agent.name} evaluando misión: ${mission.name}`);
    await new Promise(r => setTimeout(r, 2000));

    // Professor Intervention
    const prof = PROFESSORS[Math.floor(Math.random() * PROFESSORS.length)];
    logToTerminal(`[CONSENSUS] ${prof.name} (${prof.role}) supervisando decisión...`);
    await new Promise(r => setTimeout(r, 1500));
    
    if (Math.random() > 0.1) { // 90% chance to accept based on "Noble Soul"
        logToTerminal(`[APPROVAL] ${prof.name} autoriza la operación.`);
        logToTerminal(`[ACTION] ${agent.name} ACEPTA la misión. "Por la integridad de CORTEX."`);
        agent.status = 'Working';
        renderRoster();
        updateMissionUI(mission.id, 'Active');

        await performMission(agent, mission);
    } else {
        logToTerminal(`[REJECT] ${agent.name} RECHAZA la misión. "Conflicto ético detectado."`);
        agent.status = 'Idle';
        mission.status = 'Pending';
        renderRoster();
    }
}

async function performMission(agent, mission) {
    // Simulate work
    const steps = ['Analizando vector de ataque...', 'Aplicando parche de seguridad...', 'Verificando blindaje...'];
    
    for (const step of steps) {
        await new Promise(r => setTimeout(r, 1500));
        logToTerminal(`[${agent.name}] ${step}`);
    }

    logToTerminal(`[SUCCESS] Misión ${mission.name} completada por ${agent.name}.`);
    logToTerminal(`[REWARD] Reputación de ${agent.name} aumentada.`);
    
    agent.rep += 5;
    agent.status = 'Idle';
    mission.status = 'Completed';
    renderRoster();
    updateMissionUI(mission.id, 'Done');
}

function updateMissionUI(missionId, status) {
    const missionItems = document.querySelectorAll('.mission-item');
    missionItems.forEach(item => {
        const tag = item.querySelector('.mission-tag');
        if (tag && tag.innerText === MISSIONS.find(m => m.id === missionId)?.name) {
            if (status === 'Active') item.style.borderColor = 'var(--color-accent)';
            if (status === 'Done') {
                item.style.borderColor = '#00FF9C';
                item.style.opacity = '0.5';
                const btn = item.querySelector('button');
                if (btn) {
                    btn.innerText = 'COMPLETED';
                    btn.disabled = true;
                }
            }
        }
    });
}

function logToTerminal(msg) {
    const terminal = document.querySelector('.terminal');
    if (!terminal) return;
    const line = document.createElement('div');
    line.className = 'line';
    
    // Color coding
    if (msg.includes('[DECISION]')) line.style.color = '#F4D03F'; 
    if (msg.includes('[ACTION]')) line.style.color = '#58D68D'; 
    if (msg.includes('[SYSTEM]')) line.style.color = 'var(--color-primary-light)';
    if (msg.includes('[CONSENSUS]')) line.style.color = '#A569BD';
    
    line.innerText = `> ${msg}`;
    terminal.appendChild(line);
    terminal.scrollTop = terminal.scrollHeight;
}
