/* V5 marquee-hero — clones the original child unit into the left and
   right tiles until each tile is wider than 1.5x the viewport. Works
   for any number of children per tile (single-phrase span, two-word
   pair, etc.). Re-runs on resize so the marquee stays overflowing
   as the window widens. */
(function() {
  // Cache the original children of each tile on first run so resize
  // re-fills always clone from the canonical unit.
  var unitCache = new WeakMap();

  function fillTile(tile) {
    var unit = unitCache.get(tile);
    if (!unit) {
      unit = Array.prototype.slice.call(tile.children);
      if (!unit.length) return;
      unitCache.set(tile, unit);
    }
    // Reset back to just the unit
    while (tile.children.length > unit.length) tile.removeChild(tile.lastChild);
    var target = window.innerWidth * 1.5;
    var safety = 60;
    while (tile.scrollWidth < target && safety-- > 0) {
      for (var i = 0; i < unit.length; i++) {
        tile.appendChild(unit[i].cloneNode(true));
      }
    }
  }

  function fillAll() {
    var tiles = document.querySelectorAll('[data-mq-tile-left], [data-mq-tile-right]');
    Array.prototype.forEach.call(tiles, fillTile);
  }

  fillAll();

  var resizeTimer;
  window.addEventListener('resize', function() {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(fillAll, 120);
  });
})();
