/**
 * dashboard.js — RTI Tracking Dashboard
 * Loads analytics, shows RTI list, handles status checks and appeals
 */
import Api from './api.js';

const $ = id => document.getElementById(id);

// ── Demo RTI data (shown when API is not connected) ────────
const DEMO_RTIS = [
  {
    ref_number: 'RTI2024-00001',
    applicant_name: 'Priya Sharma',
    department: 'Ministry of Railways',
    subject: 'Status of pending refund for cancelled train ticket',
    status: 'acknowledged',
    filed_date: new Date(Date.now() - 10 * 86400000).toISOString()
  },
  {
    ref_number: 'RTI2024-00002',
    applicant_name: 'Ramesh Yadav',
    department: 'PWD Delhi',
    subject: 'Road repair timeline for Sector 15, Rohini',
    status: 'filed',
    filed_date: new Date(Date.now() - 3 * 86400000).toISOString()
  },
  {
    ref_number: 'RTI2024-00003',
    applicant_name: 'Sunita Devi',
    department: 'Department of Food and PD',
    subject: 'Status of BPL ration card application',
    status: 'responded',
    filed_date: new Date(Date.now() - 25 * 86400000).toISOString()
  }
];

// ── Load Analytics ────────────────────────────────────────
async function loadAnalytics() {
  try {
    const { data } = await Api.getAnalytics();
    const updates = {
      'statTotalRtis': data.total_rtis + ' RTIs',
      'statResponseRate': data.response_rate + '%',
      'statStates': data.states_covered + ' States',
      'statAvgDays': data.avg_response_days + ' Days'
    };
    Object.entries(updates).forEach(([id, val]) => {
      const el = $(id);
      if (el) { el.textContent = val; el.classList.add('loaded'); }
    });
  } catch (e) {
    console.log('Using demo analytics data.');
    const demo = { 'statTotalRtis':'1,24,892 RTIs','statResponseRate':'72%','statStates':'28 States','statAvgDays':'18 Days' };
    Object.entries(demo).forEach(([id,v]) => { const el=$(id); if(el) el.textContent=v; });
  }
}

// ── Render RTI Table ──────────────────────────────────────
function renderRTITable(rtis) {
  const tbody = $('rtiTableBody');
  if (!tbody) return;

  tbody.innerHTML = rtis.map(rti => {
    const days = Math.floor((Date.now() - new Date(rti.filed_date)) / 86400000);
    const remaining = 30 - days;
    const statusBadge = getStatusBadge(rti.status);
    return `
      <tr>
        <td><strong style="color:var(--blue)">${rti.ref_number}</strong></td>
        <td>${rti.subject?.slice(0, 45)}...</td>
        <td>${rti.department?.slice(0, 30)}</td>
        <td>${statusBadge}</td>
        <td>${days} days ago</td>
        <td>
          <span style="color:${remaining > 10 ? 'var(--green)' : remaining > 0 ? 'var(--saffron)' : '#ef4444'};font-weight:600">
            ${remaining > 0 ? remaining + ' days' : 'Overdue'}
          </span>
        </td>
        <td>
          <button class="btn btn-sm btn-outline" onclick="viewRTI('${rti.ref_number}')">View</button>
          ${days >= 25 ? `<button class="btn btn-sm btn-saffron mt-1" onclick="checkAppeal('${rti.ref_number}')">Appeal?</button>` : ''}
        </td>
      </tr>
    `;
  }).join('');
}

function getStatusBadge(status) {
  const map = {
    filed:        '<span class="badge badge-filed">● Filed</span>',
    acknowledged: '<span class="badge badge-acknowledged">● Acknowledged</span>',
    processing:   '<span class="badge" style="background:#f3e8ff;color:#7e22ce">● Processing</span>',
    responded:    '<span class="badge badge-responded">● Responded</span>',
    appeal_filed: '<span class="badge badge-appeal">● Appeal Filed</span>',
  };
  return map[status] || `<span class="badge">${status}</span>`;
}

// ── View RTI Detail Modal ─────────────────────────────────
window.viewRTI = async function(refNumber) {
  show('detailModal');
  $('modalRefNumber').textContent = refNumber;
  $('modalBody').innerHTML = '<div class="spinner"></div>';

  try {
    const { data } = await Api.getRTI(refNumber);
    const days = Math.floor((Date.now() - new Date(data.filed_date)) / 86400000);
    const remaining = Math.max(0, 30 - days);
    const fillWidth = Math.min(100, (days / 30) * 100);
    const barClass = fillWidth < 50 ? 'safe' : fillWidth < 80 ? 'warn' : 'danger';

    $('modalBody').innerHTML = `
      <div style="margin-bottom:1.25rem">
        <strong>${data.subject}</strong>
        <div style="color:var(--gray);font-size:0.9rem;margin-top:0.3rem">${data.department}</div>
      </div>
      <div class="status-timeline">
        ${['Filed', 'Acknowledged', 'Processing', 'Responded'].map((s, i) => `
          <div class="status-node ${i < 2 ? 'done' : i === 2 ? 'active' : ''}">
            <div class="status-dot">${i < 2 ? '✓' : i === 2 ? '⚡' : '○'}</div>
            <div class="status-node-label">${s}</div>
          </div>
        `).join('')}
      </div>
      <div class="deadline-bar-wrap">
        <div style="display:flex;justify-content:space-between;font-size:0.85rem;margin-bottom:0.4rem">
          <span>Day ${days} of 30</span>
          <span style="color:${remaining > 10 ? 'var(--green)' : 'var(--saffron)'}">${remaining} days remaining</span>
        </div>
        <div class="deadline-bar-track">
          <div class="deadline-bar-fill ${barClass}" style="width:${fillWidth}%"></div>
        </div>
      </div>
      <div style="margin-top:1rem;display:flex;gap:0.75rem;flex-wrap:wrap">
        <button class="btn btn-primary btn-sm" onclick="Api.downloadPDF('${data.ref_number}')">⬇️ Download PDF</button>
        <button class="btn btn-outline btn-sm" onclick="checkAppeal('${data.ref_number}')">🔔 Check Appeal Status</button>
      </div>
    `;
  } catch (e) {
    $('modalBody').innerHTML = `<div class="alert alert-error">Could not load RTI details: ${e.message}</div>`;
  }
};

// ── Check Appeal ─────────────────────────────────────────
window.checkAppeal = async function(refNumber) {
  try {
    const { data } = await Api.checkAppeal(refNumber);
    const container = $('appealContainer');
    if (!container) return;

    if (data.action === 'first_appeal') {
      container.innerHTML = `
        <div class="appeal-banner">
          <div class="icon">⚠️</div>
          <div>
            <h3>First Appeal Required!</h3>
            <p>30 days have passed with no response. An appeal has been auto-generated.</p>
            <button class="btn btn-sm" style="background:#991b1b;color:white;margin-top:0.75rem" onclick="downloadAppeal()">
              ⬇️ Download First Appeal
            </button>
          </div>
        </div>
      `;
      show('appealContainer');
    } else {
      alert(`RTI Status: ${data.message}`);
    }
  } catch (e) {
    alert('Could not check appeal status. Make sure the backend is running.');
  }
};

// ── Track by Ref Number ──────────────────────────────────
function initTrackForm() {
  const btn = $('trackSubmitBtn');
  const input = $('trackInput');
  if (!btn || !input) return;
  btn.addEventListener('click', async () => {
    const ref = input.value.trim().toUpperCase();
    if (!ref) return;
    await viewRTI(ref);
  });
}

// ── Modal Close ──────────────────────────────────────────
function initModal() {
  const overlay = $('detailModal');
  const closeBtn = $('modalClose');
  if (closeBtn) closeBtn.onclick = () => hide('detailModal');
  if (overlay) overlay.onclick = (e) => { if (e.target === overlay) hide('detailModal'); };
}

// ── Helper: show/hide ────────────────────────────────────
function show(id) { const el = $(id); if (el) el.classList.remove('hidden'); }
function hide(id) { const el = $(id); if (el) el.classList.add('hidden'); }

// ── Init ─────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  loadAnalytics();
  initTrackForm();
  initModal();

  const params = new URLSearchParams(window.location.search);
  const ref = params.get('ref');
  if (ref && $('trackInput')) {
    $('trackInput').value = ref;
    setTimeout(() => viewRTI(ref), 500);
  }

  renderRTITable(DEMO_RTIS);
});