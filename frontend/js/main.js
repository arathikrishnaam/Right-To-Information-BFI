/**
 * main.js — Landing page logic
 * Handles: language switching, live counter animation, smooth scroll
 */
import { setLanguage } from './translator.js';
import Api from './api.js';

document.addEventListener('DOMContentLoaded', async () => {

  // ── Language Switcher ──────────────────────────────────────
  const langSelect = document.getElementById('langSelect');
  if (langSelect) {
    langSelect.addEventListener('change', (e) => setLanguage(e.target.value));
  }

  // ── Animate counters on scroll ────────────────────────────
  const counters = document.querySelectorAll('.counter');
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        animateCounter(entry.target);
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.5 });
  counters.forEach(c => observer.observe(c));

  function animateCounter(el) {
    const target = parseFloat(el.getAttribute('data-target'));
    const suffix = el.getAttribute('data-suffix') || '';
    const duration = 1800;
    const start = performance.now();
    const isDecimal = target % 1 !== 0;

    function update(now) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
      const current = target * eased;
      el.textContent = (isDecimal ? current.toFixed(1) : Math.floor(current)) + suffix;
      if (progress < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
  }

  // ── Load live stats from API ──────────────────────────────
  try {
    const { data } = await Api.getAnalytics();
    const totalEl = document.getElementById('statTotal');
    const statesEl = document.getElementById('statStates');
    if (totalEl) { totalEl.setAttribute('data-target', data.total_rtis || 10); animateCounter(totalEl); }
    if (statesEl) { statesEl.setAttribute('data-target', data.states_covered || 28); animateCounter(statesEl); }
  } catch (e) {
    console.log('API not connected — showing static stats.');
  }

  // ── Smooth scroll for anchor links ────────────────────────
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', e => {
      const target = document.querySelector(a.getAttribute('href'));
      if (target) { e.preventDefault(); target.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
    });
  });

  // ── Navbar scroll effect ──────────────────────────────────
  window.addEventListener('scroll', () => {
    const navbar = document.querySelector('.navbar');
    if (navbar) navbar.classList.toggle('scrolled', window.scrollY > 50);
  });
});