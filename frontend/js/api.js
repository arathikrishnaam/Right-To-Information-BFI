/**
 * api.js — Central API service for RTI-Saarthi frontend
 * All backend calls go through this module.
 * Base URL: http://localhost:8000 (change for production)
 */

const API_BASE = 'http://localhost:8000';

const Api = {
  /**
   * Analyze citizen's question using Agent 1
   * @param {string} question - Plain language question
   * @returns {Promise<Object>} Structured analysis
   */
  async analyzeQuestion(question) {
    const res = await fetch(`${API_BASE}/api/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question })
    });
    if (!res.ok) throw new Error(`Analysis failed: ${res.statusText}`);
    return res.json();
  },

  /**
   * File a complete RTI — runs all 5 agents
   * @param {Object} formData - RTI form data
   * @returns {Promise<Object>} Filed RTI with ref number
   */
  async fileRTI(formData) {
    const res = await fetch(`${API_BASE}/api/file-rti`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Filing failed');
    }
    return res.json();
  },

  /**
   * Get RTI details by reference number
   * @param {string} refNumber - e.g. "RTI2024-00001"
   * @returns {Promise<Object>} RTI details
   */
  async getRTI(refNumber) {
    const res = await fetch(`${API_BASE}/api/rti/${refNumber}`);
    if (!res.ok) throw new Error('RTI not found');
    return res.json();
  },

  /**
   * Download RTI application as PDF
   * @param {string} refNumber
   */
  downloadPDF(refNumber) {
    window.open(`${API_BASE}/api/rti/${refNumber}/pdf`, '_blank');
  },

  /**
   * Get analytics data for dashboard
   * @returns {Promise<Object>} Analytics metrics
   */
  async getAnalytics() {
    const res = await fetch(`${API_BASE}/api/analytics`);
    if (!res.ok) throw new Error('Analytics fetch failed');
    return res.json();
  },

  /**
   * Check if appeal is needed for an RTI
   * @param {string} refNumber
   * @returns {Promise<Object>} Appeal status
   */
  async checkAppeal(refNumber) {
    const res = await fetch(`${API_BASE}/api/check-appeal`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ref_number: refNumber })
    });
    return res.json();
  },

  /**
   * Get all departments and PIOs
   * @returns {Promise<Object>} Department directory
   */
  async getDepartments() {
    const res = await fetch(`${API_BASE}/api/departments`);
    return res.json();
  }
};

export default Api;