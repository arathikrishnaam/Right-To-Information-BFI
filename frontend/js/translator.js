/**
 * translator.js — Voice Input using Web Speech API
 * Supports Hindi (hi-IN) and English (en-IN)
 * Falls back gracefully if browser doesn't support speech recognition
 */

class VoiceInput {
  constructor(options = {}) {
    this.onResult  = options.onResult  || (() => {});
    this.onStart   = options.onStart   || (() => {});
    this.onStop    = options.onStop    || (() => {});
    this.onError   = options.onError   || (() => {});
    this.language  = options.language  || 'hi-IN';
    this.isListening = false;
    this.recognition = null;
    this.supported = false;
    this._init();
  }

  _init() {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      console.warn('Web Speech API not supported in this browser.');
      return;
    }

    this.supported = true;
    this.recognition = new SpeechRecognition();
    this.recognition.continuous = false;
    this.recognition.interimResults = true;
    this.recognition.lang = this.language;
    this.recognition.maxAlternatives = 1;

    this.recognition.onresult = (event) => {
      let interim = '';
      let final = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) final += transcript;
        else interim += transcript;
      }

      this.onResult({ final, interim, isFinal: !!final });
    };

    this.recognition.onstart = () => {
      this.isListening = true;
      this.onStart();
    };

    this.recognition.onend = () => {
      this.isListening = false;
      this.onStop();
    };

    this.recognition.onerror = (e) => {
      this.isListening = false;
      this.onError(e.error);
    };
  }

  start(language = null) {
    if (!this.supported) {
      this.onError('not_supported');
      return;
    }
    if (language) this.setLanguage(language);
    this.recognition.start();
  }

  stop() {
    if (this.recognition && this.isListening) {
      this.recognition.stop();
    }
  }

  toggle(language = null) {
    this.isListening ? this.stop() : this.start(language);
  }

  setLanguage(lang) {
    this.language = lang;
    if (this.recognition) {
      this.recognition.lang = lang;
    }
  }
}

/* ---------- EXPORTS ---------- */

// Default export (class)
export default VoiceInput;

// Named export (for wizard.js)
export const getCurrentLang = () => {
  return "en";
};