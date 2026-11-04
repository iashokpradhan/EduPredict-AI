/**
 * EduPredict AI — Tactile Motion & Live Interaction Layer
 * Provides Gen Z micro-interactions, haptics, synthesized sounds,
 * 3D tilt, count-up animations, and live status polling.
 */

(function () {
  'use strict';

  // --- 1. Sound Engine (Web Audio API - Synthesized, No External Files) ---
  let audioCtx = null;
  let soundEnabled = localStorage.getItem('edupredict_sound') === 'true';

  function initAudio() {
    if (!audioCtx && (window.AudioContext || window.webkitAudioContext)) {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
  }

  function playUiSound(type) {
    if (!soundEnabled) return;
    try {
      initAudio();
      if (!audioCtx) return;
      if (audioCtx.state === 'suspended') audioCtx.resume();

      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.connect(gain);
      gain.connect(audioCtx.destination);

      const now = audioCtx.currentTime;
      if (type === 'click') {
        osc.type = 'sine';
        osc.frequency.setValueAtTime(480, now);
        osc.frequency.exponentialRampToValueAtTime(320, now + 0.04);
        gain.gain.setValueAtTime(0.08, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.04);
        osc.start(now);
        osc.stop(now + 0.04);
      } else if (type === 'preset') {
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(540, now);
        osc.frequency.exponentialRampToValueAtTime(720, now + 0.06);
        gain.gain.setValueAtTime(0.09, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.06);
        osc.start(now);
        osc.stop(now + 0.06);
      } else if (type === 'success') {
        osc.type = 'sine';
        osc.frequency.setValueAtTime(440, now);
        osc.frequency.setValueAtTime(660, now + 0.07);
        osc.frequency.setValueAtTime(880, now + 0.14);
        gain.gain.setValueAtTime(0.12, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25);
        osc.start(now);
        osc.stop(now + 0.25);
      }
    } catch (_) {
      // Audio fails silently on unsupported environments
    }
  }

  // --- 2. Haptic Feedback ---
  function triggerHaptic(ms = 18) {
    if (localStorage.getItem('edupredict_reduced_effects') === 'true') return;
    if (typeof navigator !== 'undefined' && navigator.vibrate) {
      try { navigator.vibrate(ms); } catch (_) {}
    }
  }

  // --- 3. Custom Cursor (Desktop Only) ---
  function setupCustomCursor() {
    if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;
    if (localStorage.getItem('edupredict_reduced_effects') === 'true') return;

    document.body.classList.add('has-custom-cursor');
    const dot = document.createElement('div');
    dot.className = 'cursor-dot';
    const ring = document.createElement('div');
    ring.className = 'cursor-ring';
    document.body.appendChild(dot);
    document.body.appendChild(ring);

    let mouseX = window.innerWidth / 2, mouseY = window.innerHeight / 2;
    let ringX = mouseX, ringY = mouseY;

    window.addEventListener('mousemove', (e) => {
      mouseX = e.clientX;
      mouseY = e.clientY;
      dot.style.transform = `translate(${mouseX}px, ${mouseY}px)`;
    }, { passive: true });

    function renderRing() {
      ringX += (mouseX - ringX) * 0.22;
      ringY += (mouseY - ringY) * 0.22;
      ring.style.transform = `translate(${ringX}px, ${ringY}px)`;
      requestAnimationFrame(renderRing);
    }
    requestAnimationFrame(renderRing);

    const interactiveSelector = 'button, a, input, select, .tab-btn, .preset-btn, .kpi-tile, [data-preset]';
    document.addEventListener('mouseover', (e) => {
      if (e.target.closest(interactiveSelector)) ring.classList.add('active');
    }, { passive: true });

    document.addEventListener('mouseout', (e) => {
      if (e.target.closest(interactiveSelector)) ring.classList.remove('active');
    }, { passive: true });
  }

  // --- 4. Ripple Effect on Click ---
  function setupRipples() {
    document.addEventListener('click', (e) => {
      const btn = e.target.closest('button, .tab-btn, .preset-btn');
      if (!btn) return;
      btn.classList.add('ripple-host');
      const rect = btn.getBoundingClientRect();
      const circle = document.createElement('span');
      const diameter = Math.max(rect.width, rect.height);
      circle.className = 'ripple-effect';
      circle.style.width = circle.style.height = `${diameter}px`;
      circle.style.left = `${e.clientX - rect.left - diameter / 2}px`;
      circle.style.top = `${e.clientY - rect.top - diameter / 2}px`;
      btn.appendChild(circle);
      setTimeout(() => circle.remove(), 600);
      playUiSound('click');
      triggerHaptic(14);
    }, { passive: true });
  }

  // --- 5. 3D Tilt for Key Cards ---
  function setupCardTilt() {
    if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;
    if (localStorage.getItem('edupredict_reduced_effects') === 'true') return;

    document.querySelectorAll('.kpi-tile, .result-card, section').forEach((card) => {
      card.classList.add('tilt-card');
      const glare = document.createElement('div');
      glare.className = 'card-glare';
      card.appendChild(glare);

      card.addEventListener('mousemove', (e) => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        const centerX = rect.width / 2;
        const centerY = rect.height / 2;
        const rotateX = ((y - centerY) / centerY) * -4;
        const rotateY = ((x - centerX) / centerX) * 4;

        card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-2px)`;
        glare.style.opacity = '1';
        glare.style.background = `radial-gradient(circle at ${x}px ${y}px, rgba(255,255,255,0.18) 0%, transparent 65%)`;
      }, { passive: true });

      card.addEventListener('mouseleave', () => {
        card.style.transform = '';
        glare.style.opacity = '0';
      }, { passive: true });
    });
  }

  // --- 6. Count-Up Animation for Numbers ---
  window.animateValue = function (elem, start, end, duration = 800, decimals = 0, suffix = '') {
    if (!elem) return;
    if (localStorage.getItem('edupredict_reduced_effects') === 'true') {
      elem.textContent = Number(end).toFixed(decimals) + suffix;
      return;
    }
    const startTime = performance.now();
    function update(now) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out quad
      const eased = 1 - (1 - progress) * (1 - progress);
      const current = start + (end - start) * eased;
      elem.textContent = current.toFixed(decimals) + suffix;
      if (progress < 1) {
        requestAnimationFrame(update);
      } else {
        elem.textContent = Number(end).toFixed(decimals) + suffix;
      }
    }
    requestAnimationFrame(update);
  };

  // --- 7. Toast Notification Utility ---
  let toastContainer = null;
  window.showToast = function (message, type = 'info', icon = '✨') {
    if (!toastContainer) {
      toastContainer = document.createElement('div');
      toastContainer.id = 'toast-container';
      document.body.appendChild(toastContainer);
    }
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = `${icon} ${message}`;
    toastContainer.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('show'));

    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => toast.remove(), 350);
    }, 3200);
  };

  // --- 8. Confetti & Supportive Shake Triggers ---
  window.triggerSuccessCelebration = function () {
    playUiSound('success');
    triggerHaptic([30, 50, 30]);
    if (typeof confetti === 'function') {
      confetti({
        particleCount: 55,
        spread: 60,
        origin: { y: 0.65 },
        colors: ['#a78bfa', '#ff5cae', '#5eead4', '#ffb38a']
      });
    }
    window.showToast('High performance trajectory forecast!', 'success', '🎉');
  };

  window.triggerSupportiveWarning = function () {
    triggerHaptic([40, 60, 40]);
    const results = document.getElementById('results');
    if (results) {
      results.classList.add('shake-supportive');
      setTimeout(() => results.classList.remove('shake-supportive'), 500);
    }
    window.showToast('Academic support levers recommended.', 'info', '💡');
  };

  // --- 9. Dynamic Greeting & Header Tagline ---
  function setDynamicGreeting() {
    const greetingEl = document.getElementById('hero-greeting');
    if (!greetingEl) return;
    const hour = new Date().getHours();
    let text = 'Welcome back!';
    if (hour >= 5 && hour < 12) text = 'Good morning ☀️';
    else if (hour >= 12 && hour < 17) text = 'Good afternoon 🌤️';
    else if (hour >= 17 && hour < 22) text = 'Good evening 🌙';
    else text = 'Late night study session? ⚡';
    greetingEl.textContent = text;
  }

  // --- 10. Easter Egg: Party Mode on Logo Taps ---
  function setupPartyEasterEgg() {
    const brand = document.querySelector('.brand-pill') || document.querySelector('h1');
    if (!brand) return;
    let clicks = 0;
    let resetTimer = null;
    brand.addEventListener('click', () => {
      clicks++;
      clearTimeout(resetTimer);
      triggerHaptic(20);
      if (clicks >= 5) {
        document.body.classList.toggle('party-mode');
        const active = document.body.classList.contains('party-mode');
        window.showToast(active ? '🌈 Party Mode Activated!' : 'Party Mode Off', 'info', '✨');
        if (typeof confetti === 'function' && active) {
          confetti({ particleCount: 100, spread: 100, origin: { y: 0.5 } });
        }
        clicks = 0;
      } else {
        resetTimer = setTimeout(() => { clicks = 0; }, 1500);
      }
    });
  }

  // --- 11. Touch Gestures: Mobile Tab Swipe ---
  function setupMobileTabSwipe() {
    let startX = 0;
    let startY = 0;
    const tabs = ['student', 'analytics', 'diagnostics', 'history'];

    document.addEventListener('touchstart', (e) => {
      if (e.touches.length === 1) {
        startX = e.touches[0].clientX;
        startY = e.touches[0].clientY;
      }
    }, { passive: true });

    document.addEventListener('touchend', (e) => {
      if (!startX || !startY || e.changedTouches.length !== 1) return;
      const diffX = e.changedTouches[0].clientX - startX;
      const diffY = e.changedTouches[0].clientY - startY;

      // Only horizontal swipe with threshold
      if (Math.abs(diffX) > 60 && Math.abs(diffX) > Math.abs(diffY) * 1.5) {
        const activeBtn = document.querySelector('.tab-btn.active');
        if (!activeBtn) return;
        const currentId = activeBtn.id.replace('tab-', '');
        const currentIndex = tabs.indexOf(currentId);
        if (currentIndex === -1) return;

        if (diffX < 0 && currentIndex < tabs.length - 1) {
          // Swipe left -> next tab
          const nextBtn = document.getElementById(`tab-${tabs[currentIndex + 1]}`);
          if (nextBtn) nextBtn.click();
        } else if (diffX > 0 && currentIndex > 0) {
          // Swipe right -> prev tab
          const prevBtn = document.getElementById(`tab-${tabs[currentIndex - 1]}`);
          if (prevBtn) prevBtn.click();
        }
      }
      startX = 0;
      startY = 0;
    }, { passive: true });
  }

  // --- 12. Theme & Effect Toggles ---
  function setupToggles() {
    // Theme Toggle
    const themeBtn = document.getElementById('theme-toggle');
    const savedTheme = localStorage.getItem('edupredict_theme') ||
      (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
    document.documentElement.setAttribute('data-theme', savedTheme);
    if (themeBtn) {
      themeBtn.textContent = savedTheme === 'light' ? '🌙 Dark' : '☀️ Light';
      themeBtn.addEventListener('click', () => {
        const cur = document.documentElement.getAttribute('data-theme') || 'dark';
        const next = cur === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('edupredict_theme', next);
        themeBtn.textContent = next === 'light' ? '🌙 Dark' : '☀️ Light';
        triggerHaptic(16);
      });
    }

    // Sound Toggle
    const soundBtn = document.getElementById('sound-toggle');
    if (soundBtn) {
      soundBtn.textContent = soundEnabled ? '🔊 Sound On' : '🔇 Muted';
      soundBtn.addEventListener('click', () => {
        soundEnabled = !soundEnabled;
        localStorage.setItem('edupredict_sound', soundEnabled ? 'true' : 'false');
        soundBtn.textContent = soundEnabled ? '🔊 Sound On' : '🔇 Muted';
        triggerHaptic(16);
        if (soundEnabled) playUiSound('click');
      });
    }

    // Reduce Effects Toggle
    const effectsBtn = document.getElementById('effects-toggle');
    const isReduced = localStorage.getItem('edupredict_reduced_effects') === 'true';
    if (isReduced) document.body.classList.add('reduced-effects');
    if (effectsBtn) {
      effectsBtn.textContent = isReduced ? '✨ Enable Effects' : '⚡ Reduce Effects';
      effectsBtn.addEventListener('click', () => {
        const nowReduced = !document.body.classList.contains('reduced-effects');
        document.body.classList.toggle('reduced-effects', nowReduced);
        localStorage.setItem('edupredict_reduced_effects', nowReduced ? 'true' : 'false');
        effectsBtn.textContent = nowReduced ? '✨ Enable Effects' : '⚡ Reduce Effects';
        triggerHaptic(16);
      });
    }
  }

  // --- Initialize All on DOMContentLoaded ---
  document.addEventListener('DOMContentLoaded', () => {
    setupCustomCursor();
    setupRipples();
    setupCardTilt();
    setDynamicGreeting();
    setupPartyEasterEgg();
    setupMobileTabSwipe();
    setupToggles();
  });
})();
