/* ════════════════════════════════════════════════════════════════════════
   V5 UNIFIED INTRO OVERLAY — orchestration

   Picks a random image from the shared 13-photo pool in
   /assets/imgs/intro/ and runs:
   - First visit per session: photo dwell ~1.1s + wash 720ms = ~1.4s total
   - Subsequent navigations: 320ms wash only
   - prefers-reduced-motion: skip photo, brief 180ms fade

   Adds `body.is-loaded` once the overlay clears so reveal animations
   tied to that hook fire on cue.

   To override the random pick on a specific page, set
   `data-intro-image="..."` on the .v5-intro element — that wins.
   ════════════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  // Shared pool — 13 abyss-tinted photos, served from absolute path so
  // the same JS works for root pages and /thoughts/* alike.
  const INTRO_POOL = [
    '/assets/imgs/intro/001.webp',
    '/assets/imgs/intro/002.webp',
    '/assets/imgs/intro/003.webp',
    '/assets/imgs/intro/004.webp',
    '/assets/imgs/intro/005.webp',
    '/assets/imgs/intro/006.webp',
    '/assets/imgs/intro/007.webp',
    '/assets/imgs/intro/008.webp',
    '/assets/imgs/intro/009.webp',
    '/assets/imgs/intro/010.webp',
    '/assets/imgs/intro/011.webp',
    '/assets/imgs/intro/012.webp',
    '/assets/imgs/intro/013.webp'
  ];
  const LAST_KEY = 'jxm_intro_last';

  function pickIntroImage() {
    // Avoid repeating the last-shown image back-to-back when the pool
    // has more than one option.
    let last = null;
    try { last = sessionStorage.getItem(LAST_KEY); } catch (e) {}
    let pool = INTRO_POOL;
    if (last && INTRO_POOL.length > 1) {
      pool = INTRO_POOL.filter(p => p !== last);
    }
    const pick = pool[Math.floor(Math.random() * pool.length)];
    try { sessionStorage.setItem(LAST_KEY, pick); } catch (e) {}
    return pick;
  }

  const SESSION_KEY = 'jxm_intro_seen';
  const intro = document.getElementById('v5Intro');
  if (!intro) return;
  const body = document.body;

  // Page can override the random pick via data-intro-image; otherwise
  // pull from the shared pool.
  const customImage = intro.getAttribute('data-intro-image');
  const chosen = customImage || pickIntroImage();
  intro.style.backgroundImage = `url('${chosen}')`;

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

  // ── Quick mode: in-session navigation, brief photo dwell + fast wash ──
  if (seen) {
    intro.classList.add('v5-intro--quick');
    setTimeout(() => {
      intro.classList.add('v5-intro--washing');
      setTimeout(() => {
        intro.classList.add('v5-intro--gone');
        markDone();
      }, 520);
    }, 500);
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
