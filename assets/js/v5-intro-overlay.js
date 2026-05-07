/* ════════════════════════════════════════════════════════════════════════
   V5 UNIFIED INTRO OVERLAY — orchestration

   Reads <div class="v5-intro" data-intro-image="..."> and runs:
   - First visit per session: photo dwell ~1.1s + wash 720ms = ~1.4s total
   - Subsequent navigations: 320ms wash only
   - prefers-reduced-motion: skip photo, brief 180ms fade

   Adds `body.is-loaded` once the overlay clears so reveal animations
   tied to that hook fire on cue.
   ════════════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  const SESSION_KEY = 'jxm_intro_seen';
  const intro = document.getElementById('v5Intro');
  if (!intro) return;
  const body = document.body;

  // Apply per-page background image (in case the inline style wasn't set
  // by the build, or for runtime overrides via JS).
  const customImage = intro.getAttribute('data-intro-image');
  if (customImage && !intro.style.backgroundImage) {
    intro.style.backgroundImage = `url('${customImage}')`;
  }

  body.classList.add('is-loading');

  const seen = sessionStorage.getItem(SESSION_KEY) === '1';
  const reduced = window.matchMedia &&
                  window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function markDone() {
    sessionStorage.setItem(SESSION_KEY, '1');
    body.classList.remove('is-loading');
    body.classList.add('is-loaded');
    setTimeout(() => {
      if (intro && intro.parentNode) intro.parentNode.removeChild(intro);
    }, 260);
  }

  // ── Reduced motion: skip ritual, brief fade ──
  if (reduced) {
    requestAnimationFrame(() => {
      intro.classList.add('v5-intro--gone');
      markDone();
    });
    return;
  }

  // ── Quick mode: in-session navigation, no dwell ──
  if (seen) {
    intro.classList.add('v5-intro--quick');
    requestAnimationFrame(() => {
      intro.classList.add('v5-intro--washing');
      setTimeout(() => {
        intro.classList.add('v5-intro--gone');
        markDone();
      }, 520);
    });
    return;
  }

  // ── Full ritual: first visit of session ──
  // Logo fades in immediately
  requestAnimationFrame(() => {
    intro.classList.add('v5-intro--logo-in');
  });

  let pageLoaded = document.readyState === 'complete';
  let minElapsed = false;
  let washStarted = false;

  // Min display time so the brand moment registers even on very fast loads
  const MIN_DISPLAY_MS = 1100;
  setTimeout(() => {
    minElapsed = true;
    if (pageLoaded) startWash();
  }, MIN_DISPLAY_MS);

  if (!pageLoaded) {
    window.addEventListener('load', function onLoad() {
      pageLoaded = true;
      window.removeEventListener('load', onLoad);
      if (minElapsed) startWash();
    });
  }

  // Hard cap: never let the overlay linger past 4s
  setTimeout(() => {
    if (!washStarted) startWash();
  }, 4000);

  function startWash() {
    if (washStarted) return;
    washStarted = true;
    intro.classList.add('v5-intro--logo-out');
    intro.classList.add('v5-intro--washing');
    setTimeout(() => {
      intro.classList.add('v5-intro--gone');
      markDone();
    }, 720);
  }
})();
