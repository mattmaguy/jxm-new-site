/* V5 mobile nav — hamburger toggle + off-canvas overlay.
   Pairs with the .v5-mobile-toggle / .v5-mobile-menu markup and the
   styles in assets/css/v5-nav-stacked.css. Mirrors the V4 mobile-menu
   JS pattern from index.html so behavior is identical across pages. */
(function () {
  function init() {
    var toggle = document.getElementById('v5MobileToggle');
    var menu   = document.getElementById('v5MobileMenu');
    if (!toggle || !menu) return;
    var body = document.body;

    function open() {
      menu.classList.add('is-open');
      body.classList.add('is-mobile-open');
      menu.setAttribute('aria-hidden', 'false');
      toggle.setAttribute('aria-expanded', 'true');
      toggle.setAttribute('aria-label', 'Close menu');
    }
    function close() {
      menu.classList.remove('is-open');
      body.classList.remove('is-mobile-open');
      menu.setAttribute('aria-hidden', 'true');
      toggle.setAttribute('aria-expanded', 'false');
      toggle.setAttribute('aria-label', 'Open menu');
    }

    toggle.addEventListener('click', function () {
      menu.classList.contains('is-open') ? close() : open();
    });
    menu.addEventListener('click', function (e) {
      if (e.target.closest && e.target.closest('[data-close]')) close();
      else if (e.target.closest && e.target.closest('[data-close-after]')) close();
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && menu.classList.contains('is-open')) close();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
