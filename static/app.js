/**
 * Indoor Localization & Navigation System - Frontend Logic
 * Handles floor plan rendering, API calls, navigation animation
 */

const API_BASE = '';
let graphData = null;
let currentLocation = null;
let navigationPath = null;
let animFrame = null;
let pathAnimProgress = 0;

document.addEventListener('DOMContentLoaded', async () => {
    await loadGraphData();
    await loadRooms();
    drawFloorPlan();
    window.addEventListener('resize', drawFloorPlan);
});

async function loadGraphData() {
    try {
        const res = await fetch(`${API_BASE}/api/graph`);
        graphData = await res.json();
    } catch (e) { showToast('Failed to load floor plan data', 'error'); }
}

async function loadRooms() {
    try {
        const res = await fetch(`${API_BASE}/api/rooms`);
        const data = await res.json();
        const rooms = data.rooms;
        ['currentLocationSelect', 'destinationSelect'].forEach(id => {
            const sel = document.getElementById(id);
            if (!sel) return;
            const ph = sel.options[0];
            sel.innerHTML = '';
            sel.appendChild(ph);
            const groups = { 'Landmarks': [], 'A-Wing': [], 'B-Wing': [], 'Other': [] };
            rooms.forEach(r => {
                const key = r.wing === 'A' ? 'A-Wing' : r.wing === 'B' ? 'B-Wing' :
                    r.wing === null && r.id !== 'Gallery_16' ? 'Landmarks' : 'Other';
                groups[key].push(r);
            });
            Object.entries(groups).forEach(([gn, gr]) => {
                if (!gr.length) return;
                const og = document.createElement('optgroup');
                og.label = gn;
                gr.forEach(r => { const o = document.createElement('option'); o.value = r.id; o.textContent = r.name; og.appendChild(o); });
                sel.appendChild(og);
            });
        });
    } catch (e) { showToast('Failed to load room list', 'error'); }
}

// ---- Localization ----
async function simulateLocalization() {
    const sel = document.getElementById('currentLocationSelect');
    if (!sel.value) { showToast('Please select your current location', 'info'); return; }
    const btn = document.getElementById('localizeBtn');
    const stepInput = document.getElementById('stepCountInput');
    const stepCount = stepInput ? parseInt(stepInput.value) || 0 : 0;
    btn.classList.add('loading');
    try {
        const res = await fetch(`${API_BASE}/api/simulate-localize`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ location: sel.value, step_count: stepCount })
        });
        const data = await res.json();
        handleLocalizationResult(data);
        showToast(`Localized to: ${data.room_name}`, 'success');
    } catch (e) { showToast('Localization failed', 'error'); }
    finally { btn.classList.remove('loading'); }
}

function handleLocalizationResult(data) {
    currentLocation = data;
    const method = data.method || 'wifi-only';
    const methodLabel = method === 'wifi+steps' ? '📡+🚶 WiFi + Steps' : '📡 WiFi Only';
    const methodClass = method === 'wifi+steps' ? 'wifi-steps' : 'wifi-only';
    document.getElementById('locationDisplay').innerHTML = `
        <div class="location-label">Your Current Location</div>
        <div class="location-value">${data.room_name}</div>
        <div class="confidence">Confidence: ${(data.confidence * 100).toFixed(1)}%</div>
        <div class="method-badge ${methodClass}">${methodLabel}</div>`;
    const ml = document.getElementById('topMatches');
    if (data.top_matches && data.top_matches.length)
        ml.innerHTML = data.top_matches.map(m => {
            const name = m.location.replace('_left','').replace('_Right','');
            const extra = m.step_diff !== undefined ? ` <span style="opacity:0.5;font-size:0.7rem">(±${m.step_diff} steps)</span>` : '';
            return `<li class="match-item"><span class="name">${name}${extra}</span><span class="prob">${(m.probability*100).toFixed(1)}%</span></li>`;
        }).join('');
    drawFloorPlan();
}

// ---- Navigation ----
async function startNavigation() {
    const dest = document.getElementById('destinationSelect').value;
    if (!dest) { showToast('Please select a destination', 'info'); return; }
    if (!currentLocation) { showToast('Please localize first', 'info'); return; }
    const btn = document.getElementById('navigateBtn');
    btn.classList.add('loading');
    try {
        const res = await fetch(`${API_BASE}/api/navigate`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ start: currentLocation.predicted_location, end: dest })
        });
        const data = await res.json();
        if (data.error) { showToast(data.error, 'error'); return; }
        navigationPath = data;
        displayDirections(data);
        animateNavigationPath();
        showToast(`Route found: ${data.distance} steps`, 'success');
    } catch (e) { showToast('Navigation request failed', 'error'); }
    finally { btn.classList.remove('loading'); }
}

function displayDirections(navData) {
    document.getElementById('directionsContainer').innerHTML = `
        <div class="distance-badge">Total: ~${navData.distance} steps</div>
        <ul class="directions-list">${navData.directions.map((d, i) =>
            `<li class="direction-step ${i === 0 ? 'active' : ''}">${d}</li>`).join('')}</ul>`;
}

function animateNavigationPath() {
    pathAnimProgress = 0;
    if (animFrame) cancelAnimationFrame(animFrame);
    function step() {
        pathAnimProgress += 0.02;
        if (pathAnimProgress > 1) pathAnimProgress = 1;
        drawFloorPlan();
        if (pathAnimProgress < 1) animFrame = requestAnimationFrame(step);
    }
    animFrame = requestAnimationFrame(step);
}

// ============================================================
// Canvas Rendering — Improved clarity and spacing
// ============================================================
function drawFloorPlan() {
    const canvas = document.getElementById('floorPlanCanvas');
    if (!canvas || !graphData) return;
    const container = canvas.parentElement;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = container.clientWidth * dpr;
    canvas.height = container.clientHeight * dpr;
    canvas.style.width = container.clientWidth + 'px';
    canvas.style.height = container.clientHeight + 'px';
    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);
    const W = container.clientWidth, H = container.clientHeight;

    // Background
    ctx.fillStyle = '#0c1220';
    ctx.fillRect(0, 0, W, H);
    drawGrid(ctx, W, H);

    // Compute transform
    const pad = 50;
    const xs = graphData.nodes.map(n => n.x), ys = graphData.nodes.map(n => n.y);
    const minX = Math.min(...xs), maxX = Math.max(...xs);
    const minY = Math.min(...ys), maxY = Math.max(...ys);
    const gW = maxX - minX || 1, gH = maxY - minY || 1;
    const scale = Math.min((W - pad * 2) / gW, (H - pad * 2) / gH);
    const offX = (W - gW * scale) / 2 - minX * scale;
    const offY = (H - gH * scale) / 2 - minY * scale;
    const tx = x => x * scale + offX;
    const ty = y => y * scale + offY;

    // Draw corridor spine (thick line)
    const corr = graphData.nodes.filter(n => n.type === 'corridor').sort((a, b) => a.x - b.x);
    if (corr.length > 1) {
        ctx.strokeStyle = 'rgba(148,163,184,0.35)';
        ctx.lineWidth = 4;
        ctx.lineCap = 'round';
        ctx.beginPath();
        ctx.moveTo(tx(corr[0].x), ty(corr[0].y));
        corr.forEach(n => ctx.lineTo(tx(n.x), ty(n.y)));
        ctx.stroke();
    }

    // Draw stems — only room/landmark connections (corridor spine already drawn above)
    graphData.edges.forEach(e => {
        const fn = graphData.nodes.find(n => n.id === e.from);
        const tn = graphData.nodes.find(n => n.id === e.to);
        if (!fn || !tn) return;
        // Skip corridor-to-corridor edges (already shown as the spine)
        if (fn.type === 'corridor' && tn.type === 'corridor') return;
        // Draw colored stem for room connections
        const roomNode = fn.type === 'room' ? fn : (tn.type === 'room' ? tn : null);
        if (roomNode) {
            const color = getColor(roomNode);
            ctx.strokeStyle = color + '50';
            ctx.lineWidth = 1.5;
        } else {
            ctx.strokeStyle = 'rgba(148,163,184,0.2)';
            ctx.lineWidth = 1.5;
        }
        ctx.beginPath();
        ctx.moveTo(tx(fn.x), ty(fn.y));
        ctx.lineTo(tx(tn.x), ty(tn.y));
        ctx.stroke();
    });

    // Draw navigation path
    if (navigationPath && navigationPath.path_positions) {
        drawNavPath(ctx, tx, ty);
    }

    // Draw nodes (skip corridor waypoints - they're internal pathfinding nodes)
    graphData.nodes.forEach(node => {
        const x = tx(node.x), y = ty(node.y);
        if (node.type === 'corridor') {
            // Corridor waypoints are invisible — just navigation graph nodes
            return;
        } else if (node.type === 'landmark') {
            drawLandmark(ctx, x, y, node);
        } else {
            drawRoom(ctx, x, y, node);
        }
    });

    // User marker
    if (currentLocation && currentLocation.position) {
        drawUser(ctx, tx(currentLocation.position.x), ty(currentLocation.position.y));
    }

    // Title and wing labels
    ctx.fillStyle = 'rgba(241,245,249,0.5)';
    ctx.font = '600 13px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('4th Floor — R&D Building', W / 2, 22);

    // Wing labels
    const corrY = ty(380);
    ctx.font = '700 16px Inter, sans-serif';
    ctx.fillStyle = 'rgba(59,130,246,0.35)';
    ctx.textAlign = 'left';
    ctx.fillText('A-WING', tx(60), corrY - 55);
    ctx.fillStyle = 'rgba(16,185,129,0.35)';
    ctx.textAlign = 'right';
    ctx.fillText('B-WING', tx(1550), corrY - 55);
}

function drawGrid(ctx, W, H) {
    ctx.strokeStyle = 'rgba(148,163,184,0.03)';
    ctx.lineWidth = 1;
    for (let x = 0; x < W; x += 40) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
    for (let y = 0; y < H; y += 40) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }
}

function getColor(node) {
    if (node.wing === 'A' && node.side === 'left') return '#3b82f6';
    if (node.wing === 'A' && node.side === 'right') return '#f59e0b';
    if (node.wing === 'B' && node.side === 'left') return '#10b981';
    if (node.wing === 'B' && node.side === 'right') return '#ef4444';
    return '#8b5cf6';
}

function drawRoom(ctx, x, y, node) {
    const color = getColor(node);
    const isSouth = (node.wing === 'A' && node.side === 'left') || (node.wing === 'B' && node.side === 'right');

    // Outer glow ring
    ctx.shadowColor = color; ctx.shadowBlur = 15;
    ctx.strokeStyle = color; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.arc(x, y, 8, 0, Math.PI * 2); ctx.stroke();
    ctx.shadowBlur = 0;

    // Filled center
    ctx.fillStyle = color;
    ctx.beginPath(); ctx.arc(x, y, 5, 0, Math.PI * 2); ctx.fill();

    // White highlight
    ctx.fillStyle = 'rgba(255,255,255,0.6)';
    ctx.beginPath(); ctx.arc(x, y, 2, 0, Math.PI * 2); ctx.fill();

    // Label with background badge
    const label = node.description.replace('Room ', '');
    ctx.font = '700 8px Inter, sans-serif';
    const tw = ctx.measureText(label).width;
    const pad = 4;
    const bw = tw + pad * 2;
    const bh = 14;

    let ly;
    if (isSouth) {
        ly = y + 14; // label below dot
    } else {
        ly = y - 18; // label above dot
    }

    // Badge background
    ctx.fillStyle = 'rgba(15,23,42,0.85)';
    roundRect(ctx, x - bw/2, ly - bh/2, bw, bh, 3);
    ctx.fill();
    ctx.strokeStyle = color + '55'; ctx.lineWidth = 0.5;
    roundRect(ctx, x - bw/2, ly - bh/2, bw, bh, 3);
    ctx.stroke();

    // Label text
    ctx.fillStyle = 'rgba(241,245,249,0.95)';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText(label, x, ly);
    ctx.textBaseline = 'alphabetic';
}

// Rounded rectangle helper
function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r);
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
}

function drawLandmark(ctx, x, y, node) {
    if (node.id === 'G') {
        // Simple colored dot directly on the corridor
        ctx.fillStyle = '#f43f5e'; // distinct rose color
        ctx.beginPath(); ctx.arc(x, y, 4, 0, Math.PI * 2); ctx.fill();
        
        // White highlight
        ctx.fillStyle = '#ffffff';
        ctx.beginPath(); ctx.arc(x, y, 1.5, 0, Math.PI * 2); ctx.fill();

        // Arrow and name pointing to it
        ctx.fillStyle = '#fca5a5';
        ctx.font = '600 12px Inter, sans-serif';
        ctx.textAlign = 'center'; ctx.textBaseline = 'bottom';
        ctx.fillText('↓', x, y - 6);
        ctx.fillText('G', x, y - 18);
        return;
    }

    // Outer ring for other landmarks
    ctx.shadowColor = '#8b5cf6'; ctx.shadowBlur = 18;
    ctx.fillStyle = '#1e1b4b';
    ctx.strokeStyle = '#8b5cf6'; ctx.lineWidth = 2.5;
    ctx.beginPath(); ctx.arc(x, y, 14, 0, Math.PI * 2);
    ctx.fill(); ctx.stroke();
    ctx.shadowBlur = 0;
    // Icon
    ctx.fillStyle = '#c4b5fd'; ctx.font = '15px sans-serif';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    if (node.id === 'elevator') ctx.fillText('\u{1F6D7}', x, y);
    else if (node.id === 'door_elevator') ctx.fillText('\u{1F6AA}', x, y);
    else ctx.fillText('\u{1F4CD}', x, y);
    ctx.textBaseline = 'alphabetic';
    // Label
    ctx.fillStyle = 'rgba(196,181,253,0.9)';
    ctx.font = '600 9px Inter, sans-serif';
    ctx.fillText(node.description, x, y + 26);
}

function drawNavPath(ctx, tx, ty) {
    const pos = navigationPath.path_positions;
    if (pos.length < 2) return;
    const dc = Math.floor(pathAnimProgress * (pos.length - 1)) + 1;

    // Glow line
    ctx.shadowColor = '#06b6d4'; ctx.shadowBlur = 14;
    ctx.strokeStyle = 'rgba(6,182,212,0.7)';
    ctx.lineWidth = 4.5; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    ctx.setLineDash([10, 5]);
    ctx.beginPath();
    ctx.moveTo(tx(pos[0][0]), ty(pos[0][1]));
    for (let i = 1; i <= Math.min(dc, pos.length - 1); i++)
        ctx.lineTo(tx(pos[i][0]), ty(pos[i][1]));
    ctx.stroke();
    ctx.setLineDash([]); ctx.shadowBlur = 0;

    // Destination marker
    if (pathAnimProgress >= 1) {
        const d = pos[pos.length - 1];
        const dx = tx(d[0]), dy = ty(d[1]);
        ctx.fillStyle = 'rgba(6,182,212,0.15)';
        ctx.beginPath(); ctx.arc(dx, dy, 20, 0, Math.PI * 2); ctx.fill();
        ctx.strokeStyle = '#06b6d4'; ctx.lineWidth = 2.5; ctx.stroke();
        ctx.fillStyle = '#06b6d4'; ctx.font = '18px sans-serif';
        ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.fillText('\u{1F3C1}', dx, dy);
        ctx.textBaseline = 'alphabetic';
    }
}

function drawUser(ctx, x, y) {
    const t = Date.now() / 1000;
    const pr = 22 + Math.sin(t * 3) * 6;
    // Pulse ring
    ctx.strokeStyle = 'rgba(59,130,246,0.25)'; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.arc(x, y, pr, 0, Math.PI * 2); ctx.stroke();
    // Solid circle
    ctx.shadowColor = '#3b82f6'; ctx.shadowBlur = 22;
    ctx.fillStyle = '#3b82f6';
    ctx.beginPath(); ctx.arc(x, y, 11, 0, Math.PI * 2); ctx.fill();
    ctx.shadowBlur = 0;
    // White center
    ctx.fillStyle = '#fff';
    ctx.beginPath(); ctx.arc(x, y, 5, 0, Math.PI * 2); ctx.fill();
    // Label
    ctx.fillStyle = '#93c5fd'; ctx.font = '700 10px Inter, sans-serif';
    ctx.textAlign = 'center'; ctx.fillText('YOU', x, y - 20);
    requestAnimationFrame(drawFloorPlan);
}

// ---- Utilities ----
function clearNavigation() {
    navigationPath = null; currentLocation = null; pathAnimProgress = 0;
    if (animFrame) cancelAnimationFrame(animFrame);
    document.getElementById('locationDisplay').innerHTML = '<div class="location-label">Not Localized</div><div class="location-value" style="font-size:1rem;opacity:0.5">—</div>';
    document.getElementById('topMatches').innerHTML = '';
    document.getElementById('directionsContainer').innerHTML = '<div class="empty-state"><div class="icon">\u{1F9ED}</div><p>Select your location and destination, then navigate.</p></div>';
    document.getElementById('currentLocationSelect').value = '';
    document.getElementById('destinationSelect').value = '';
    document.getElementById('stepCountInput').value = '';
    drawFloorPlan();
    showToast('Navigation cleared', 'info');
}

function showToast(msg, type = 'info') {
    const c = document.getElementById('toastContainer');
    const t = document.createElement('div');
    t.className = `toast ${type}`; t.textContent = msg;
    c.appendChild(t);
    setTimeout(() => { t.style.opacity = '0'; t.style.transform = 'translateX(50px)'; t.style.transition = 'all 0.3s'; setTimeout(() => t.remove(), 300); }, 3000);
}
