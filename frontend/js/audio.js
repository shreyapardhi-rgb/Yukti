// ==AUDIO==
// Yukti Acoustic Prosody & Interactive Sound Engine (Web Audio API)
// Provides authentic Vedic prosodic timing: Laghu = 1 matra (~120ms), Guru = 2 matras (~240ms)
// plus pentatonic harmonic chimes for Meru combinations.

const YuktiAudio = (() => {
  let ctx = null;
  let enabled = true;

  function getCtx() {
    if (!ctx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) ctx = new AudioCtx();
    }
    if (ctx && ctx.state === "suspended") {
      ctx.resume().catch(() => {});
    }
    return ctx;
  }

  function isEnabled() {
    const s = localStorage.getItem("yukti-sound");
    return s === null ? true : s === "1";
  }

  function setEnabled(v) {
    enabled = Boolean(v);
    localStorage.setItem("yukti-sound", enabled ? "1" : "0");
    const btns = document.querySelectorAll(".sound-toggle-btn");
    btns.forEach(b => {
      b.innerHTML = enabled 
        ? `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/></svg> Sound: ON`
        : `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/></svg> Sound: OFF`;
      b.setAttribute("aria-label", enabled ? "Mute audio" : "Unmute audio");
    });
  }

  // Play a soft click on UI interaction
  function click(freq = 600, duration = 0.04) {
    if (!isEnabled()) return;
    try {
      const c = getCtx();
      if (!c) return;
      const osc = c.createOscillator();
      const gain = c.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(freq, c.currentTime);
      gain.gain.setValueAtTime(0.08, c.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, c.currentTime + duration);
      osc.connect(gain);
      gain.connect(c.destination);
      osc.start();
      osc.stop(c.currentTime + duration);
    } catch (e) {}
  }

  // Play Laghu tone (1 matra = ~120ms, higher pitch ~520Hz)
  function playLaghu() {
    if (!isEnabled()) return;
    try {
      const c = getCtx();
      if (!c) return;
      const t = c.currentTime;
      const osc = c.createOscillator();
      const gain = c.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(523.25, t); // C5
      gain.gain.setValueAtTime(0.15, t);
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.12);
      osc.connect(gain);
      gain.connect(c.destination);
      osc.start(t);
      osc.stop(t + 0.13);
    } catch (e) {}
  }

  // Play Guru tone (2 matras = ~240ms, resonant lower pitch ~329Hz with harmonic)
  function playGuru() {
    if (!isEnabled()) return;
    try {
      const c = getCtx();
      if (!c) return;
      const t = c.currentTime;
      // Fundamental
      const osc1 = c.createOscillator();
      const osc2 = c.createOscillator();
      const gain = c.createGain();
      osc1.type = "sine";
      osc1.frequency.setValueAtTime(329.63, t); // E4
      osc2.type = "triangle";
      osc2.frequency.setValueAtTime(659.25, t); // E5 harmonic
      gain.gain.setValueAtTime(0.18, t);
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.24);
      osc1.connect(gain);
      osc2.connect(gain);
      gain.connect(c.destination);
      osc1.start(t);
      osc2.start(t);
      osc1.stop(t + 0.25);
      osc2.stop(t + 0.25);
    } catch (e) {}
  }

  // Play harmonic chime for 3D Meru node (pentatonic scale based on n, k)
  function playMeruChime(n, k) {
    if (!isEnabled()) return;
    try {
      const c = getCtx();
      if (!c) return;
      const t = c.currentTime;
      // Pentatonic frequencies (C4, D4, E4, G4, A4, C5, D5, E5)
      const scale = [261.63, 293.66, 329.63, 392.00, 440.00, 523.25, 587.33, 659.25, 783.99, 880.00];
      const idx = (n * 2 + k) % scale.length;
      const freq = scale[idx];
      const osc = c.createOscillator();
      const gain = c.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(freq, t);
      gain.gain.setValueAtTime(0.2, t);
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.45);
      osc.connect(gain);
      gain.connect(c.destination);
      osc.start(t);
      osc.stop(t + 0.46);
    } catch (e) {}
  }

  // Play an entire sequence of syllables e.g. "LGLLG" or "1001"
  function playPattern(pattern, onStep, onEnd) {
    if (!isEnabled()) {
      if (onEnd) onEnd();
      return;
    }
    const c = getCtx();
    if (!c) {
      if (onEnd) onEnd();
      return;
    }
    const chars = Array.from(pattern);
    let curTime = 0;
    chars.forEach((ch, idx) => {
      const isGuru = (ch === "1" || ch === "G" || ch === "g");
      const duration = isGuru ? 260 : 140;
      setTimeout(() => {
        if (isGuru) playGuru(); else playLaghu();
        if (onStep) onStep(idx, ch);
      }, curTime);
      curTime += duration + 40;
    });
    setTimeout(() => {
      if (onEnd) onEnd();
    }, curTime + 50);
  }

  return {
    click,
    playLaghu,
    playGuru,
    playMeruChime,
    playPattern,
    isEnabled,
    setEnabled,
    toggle: () => setEnabled(!isEnabled())
  };
})();
