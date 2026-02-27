/**
 * wizard.js — RTI Filing Wizard (5-step process)
 * Orchestrates all 5 AI agents through the backend API
 */
import Api from './api.js';
import VoiceInput from './voice.js';
import { t, getCurrentLang } from './translator.js';

// ── State ──────────────────────────────────────────────────
const state = {
  currentStep: 1,
  totalSteps: 5,
  question: '',
  analysis: null,
  routing: null,
  draft: null,
  filing: null,
  prediction: null,
  applicant: {}
};

// ── DOM helpers ────────────────────────────────────────────
const $ = id => document.getElementById(id);
const show = id => { const el = $(id); if (el) el.classList.remove('hidden'); };
const hide = id => { const el = $(id); if (el) el.classList.add('hidden'); };
const setText = (id, text) => { const el = $(id); if (el) el.textContent = text; };
const setHTML = (id, html) => { const el = $(id); if (el) el.innerHTML = html; };

// ── Voice Input Setup ──────────────────────────────────────
let voiceInput = null;

function initVoice() {
  const voiceBtn = $('voiceBtn');
  const transcript = $('voiceTranscript');
  const questionInput = $('questionInput');

  if (!voiceBtn) return;

  voiceInput = new VoiceInput({
    language: getCurrentLang() === 'hi' ? 'hi-IN' : 'en-IN',
    onResult: ({ final, interim, isFinal }) => {
      if (transcript) transcript.textContent = final || interim;
      if (isFinal && questionInput) {
        questionInput.value = final;
        state.question = final;
      }
    },
    onStart: () => {
      voiceBtn.classList.add('listening');
      voiceBtn.textContent = '⏹';
      if (transcript) { transcript.textContent = 'Listening...'; show('voiceTranscript'); }
    },
    onStop: () => {
      voiceBtn.classList.remove('listening');
      voiceBtn.textContent = '🎤';
    },
    onError: (err) => {
      showAlert('voiceError',
        err === 'not_supported'
          ? 'Voice input not supported in this browser. Please type your question.'
          : 'Microphone error. Please type your question.',
        'error'
      );
    }
  });

  voiceBtn.addEventListener('click', () => voiceInput.toggle());
}

// ── Step Navigation ────────────────────────────────────────
function goToStep(step) {
  document.querySelectorAll('.step-panel').forEach(p => p.classList.remove('active'));
  const panel = document.querySelector(`.step-panel[data-step="${step}"]`);
  if (panel) panel.classList.add('active');

  document.querySelectorAll('.step-indicator').forEach((el, i) => {
    el.classList.remove('active', 'done');
    if (i + 1 < step) el.classList.add('done');
    else if (i + 1 === step) el.classList.add('active');
  });
  const fill = $('progressFill');
  if (fill) fill.style.width = `${((step - 1) / (state.totalSteps - 1)) * 100}%`;

  state.currentStep = step;
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ── Step 1: Analyze Question ──────────────────────────────
async function analyzeQuestion() {
  const input = $('questionInput');
  if (!input || !input.value.trim()) {
    showAlert('step1Alert', 'Please enter your question or use voice input.', 'error');
    return;
  }
  state.question = input.value.trim();

  setLoading('analyzeBtn', true, 'Analyzing...');
  hide('analysisResult');
  clearAlert('step1Alert');

  try {
    const result = await Api.analyzeQuestion(state.question);
    state.analysis = result.data;
    renderAnalysis(state.analysis);
    show('analysisResult');
    show('nextStep1Btn');
  } catch (e) {
    showAlert('step1Alert', `Analysis failed: ${e.message}. Please check if the backend is running.`, 'error');
  } finally {
    setLoading('analyzeBtn', false, '🤖 Analyze with AI');
  }
}

function renderAnalysis(analysis) {
  if (!analysis) return;
  const cat = (analysis.category || 'other').replace(/_/g, ' ');
  setHTML('analysisCategory', `<span class="analysis-chip">📂 ${cat.toUpperCase()}</span>`);
  setText('analysisSubject', analysis.subject || analysis.extracted_info?.what_is_needed || '');
  setText('analysisLang', `Detected Language: ${analysis.detected_language || 'English'}`);

  const qs = analysis.suggested_questions || [];
  setHTML('suggestedQuestions', qs.map((q, i) =>
    `<li onclick="selectQuestion(this)" data-q="${escHtml(q)}">${i+1}. ${q}</li>`
  ).join(''));

  const urgency = analysis.urgency || 'medium';
  const urgencyColors = { low: '#d1fae5', medium: '#fff7ed', high: '#fee2e2' };
  setHTML('analysisUrgency',
    `<span style="background:${urgencyColors[urgency]};padding:0.2rem 0.6rem;border-radius:50px;font-size:0.8rem;font-weight:600;">${urgency.toUpperCase()} PRIORITY</span>`
  );
}

window.selectQuestion = function(el) {
  document.querySelectorAll('.suggested-questions li').forEach(li => li.style.background = '');
  el.style.background = 'var(--blue-bg)';
  const q = el.getAttribute('data-q');
  if ($('questionInput')) $('questionInput').value = q;
  state.question = q;
};

// ── Step 2: Applicant Details ─────────────────────────────
function validateStep2() {
  const fields = ['applicantName', 'applicantEmail', 'applicantMobile', 'applicantAddress', 'applicantState'];
  for (const f of fields) {
    const el = $(f);
    if (!el || !el.value.trim()) {
      showAlert('step2Alert', 'Please fill all required fields.', 'error');
      el?.focus();
      return false;
    }
  }
  if (!/^[6-9]\d{9}$/.test($('applicantMobile').value.trim())) {
    showAlert('step2Alert', 'Please enter a valid 10-digit mobile number.', 'error');
    return false;
  }
  state.applicant = {
    question: state.question,
    applicant_name: $('applicantName').value.trim(),
    applicant_email: $('applicantEmail').value.trim(),
    applicant_mobile: $('applicantMobile').value.trim(),
    applicant_address: $('applicantAddress').value.trim(),
    user_state: $('applicantState').value,
    is_bpl: $('bplToggle')?.checked || false,
    bpl_card_no: $('bplCardNo')?.value.trim() || '',
    language: getCurrentLang()
  };
  return true;
}

// ── Step 3: Draft RTI ─────────────────────────────────────
async function draftRTI() {
  if (!validateStep2()) return;
  clearAlert('step2Alert');

  setLoading('nextStep2Btn', true, 'Generating RTI Draft...');
  goToStep(3);
  show('draftLoading');
  hide('draftContent');

  try {
    const result = await Api.fileRTI(state.applicant);
    state.draft = result.draft;
    state.routing = result.routing;
    state.filing = result.filing;
    state.prediction = result.prediction;
    state.refNumber = result.ref_number;

    renderDraft(result);
    hide('draftLoading');
    show('draftContent');
  } catch (e) {
    hide('draftLoading');
    showAlert('step3Alert', `Draft generation failed: ${e.message}`, 'error');
    goToStep(2);
  } finally {
    setLoading('nextStep2Btn', false, 'Continue →');
  }
}

function renderDraft(result) {
  const { draft, routing, prediction } = result;

  setHTML('pioCard', `
    <div class="pio-header">
      <div class="pio-avatar">🏛️</div>
      <div>
        <div class="pio-name">${routing.pio_name || 'Public Information Officer'}</div>
        <div class="pio-dept">${routing.department}</div>
      </div>
    </div>
    <div class="pio-details">
      <div class="pio-detail-item"><span class="label">Email</span><span class="value">${routing.pio_email || 'N/A'}</span></div>
      <div class="pio-detail-item"><span class="label">Portal</span><span class="value"><a href="${routing.portal}" target="_blank">rtionline.gov.in</a></span></div>
      <div class="pio-detail-item"><span class="label">Jurisdiction</span><span class="value">${routing.jurisdiction?.toUpperCase()}</span></div>
      <div class="pio-detail-item"><span class="label">Filing Fee</span><span class="value">${state.applicant.is_bpl ? '₹0 (BPL Exempt)' : '₹10'}</span></div>
    </div>
  `);

  setText('rtiPreview', draft.full_text || '');

  if (prediction) {
    const pct = Math.round((prediction.success_probability || 0.78) * 100);
    renderPredictor(pct, prediction);
  }
}

function renderPredictor(pct, prediction) {
  const circumference = 2 * Math.PI * 52;
  const offset = circumference - (pct / 100) * circumference;
  const color = pct >= 75 ? 'var(--green)' : pct >= 50 ? 'var(--saffron)' : '#ef4444';

  setHTML('predictorWidget', `
    <div class="predictor-ring">
      <svg width="120" height="120" viewBox="0 0 120 120">
        <circle class="ring-bg" cx="60" cy="60" r="52"/>
        <circle class="ring-fill" cx="60" cy="60" r="52"
          style="stroke:${color};stroke-dasharray:${circumference};stroke-dashoffset:${offset}"/>
      </svg>
      <div class="predictor-pct">${pct}%</div>
    </div>
    <p style="text-align:center;color:var(--gray);font-size:0.85rem;">Success Probability</p>
    <div style="margin-top:0.75rem;">
      ${(prediction.tips || []).map(tip => `<div class="alert alert-info" style="font-size:0.85rem;margin-bottom:0.5rem;">💡 ${tip}</div>`).join('')}
    </div>
  `);
}

// ── Step 4: Final Confirm ─────────────────────────────────
function showConfirmStep() {
  goToStep(4);
  setText('confirmRefNumber', state.refNumber || '');
  setText('confirmDept', state.routing?.department || '');
  setText('confirmDeadline', state.draft?.deadline_date || '');
  setText('confirmFee', state.applicant.is_bpl ? '₹0 (BPL Exempt)' : '₹10');
}

// ── Step 5: Success ───────────────────────────────────────
function showSuccess() {
  goToStep(5);
  setText('successRefNumber', state.refNumber || '');
  setText('successDept', state.routing?.department || '');
  setText('successDeadline', state.draft?.deadline_date || 'Within 30 days');

  const pdfBtn = $('downloadPdfBtn');
  if (pdfBtn) pdfBtn.onclick = () => Api.downloadPDF(state.refNumber);

  const trackBtn = $('trackRtiBtn');
  if (trackBtn) trackBtn.onclick = () => {
    window.location.href = `dashboard.html?ref=${state.refNumber}`;
  };
}

// ── Utility Functions ─────────────────────────────────────
function showAlert(containerId, message, type = 'info') {
  const el = $(containerId);
  if (!el) return;
  el.className = `alert alert-${type}`;
  el.innerHTML = `<span>${type === 'error' ? '❌' : type === 'success' ? '✅' : 'ℹ️'}</span> ${message}`;
  el.classList.remove('hidden');
}
function clearAlert(id) { const el = $(id); if (el) el.classList.add('hidden'); }
function setLoading(btnId, loading, text) {
  const btn = $(btnId);
  if (!btn) return;
  btn.disabled = loading;
  btn.textContent = loading ? `⏳ ${text}` : text;
}
function escHtml(str) { return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

// ── BPL Toggle ────────────────────────────────────────────
function initBplToggle() {
  const toggle = $('bplToggle');
  const bplField = $('bplCardField');
  if (!toggle || !bplField) return;
  toggle.addEventListener('change', () => {
    bplField.classList.toggle('hidden', !toggle.checked);
  });
}

// ── Initialize ─────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initVoice();
  initBplToggle();
  goToStep(1);

  $('analyzeBtn')?.addEventListener('click', analyzeQuestion);
  $('nextStep1Btn')?.addEventListener('click', () => goToStep(2));
  $('backStep2Btn')?.addEventListener('click', () => goToStep(1));
  $('nextStep2Btn')?.addEventListener('click', draftRTI);
  $('backStep3Btn')?.addEventListener('click', () => goToStep(2));
  $('nextStep3Btn')?.addEventListener('click', showConfirmStep);
  $('backStep4Btn')?.addEventListener('click', () => goToStep(3));
  $('confirmFileBtn')?.addEventListener('click', showSuccess);
  $('fileNewBtn')?.addEventListener('click', () => window.location.href = 'file-rti.html');

  $('questionInput')?.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); analyzeQuestion(); }
  });

  document.getElementById('langSelect')?.addEventListener('change', e => {
    const lang = e.target.value;
    import('./translator.js').then(m => m.setLanguage(lang));
    if (voiceInput) voiceInput.setLanguage(lang === 'hi' ? 'hi-IN' : 'en-IN');
  });
});