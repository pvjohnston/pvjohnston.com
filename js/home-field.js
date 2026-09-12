// Decorative home field: soft boiling bubbles on cream paper.
// Colors come from the live theme; notebook content stays independent.
(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    if (!document.querySelector('#main > .masthead-home')) return;

    var reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
    var fine = window.matchMedia('(hover: hover) and (pointer: fine)');
    var forced = window.matchMedia('(forced-colors: active)');
    var print = window.matchMedia('print');
    var canvas = document.createElement('canvas');
    var ctx = canvas.getContext('2d');
    if (!ctx) return;

    var glow = document.createElement('div');
    canvas.className = 'home-field';
    glow.className = 'home-cursor-glow';
    canvas.setAttribute('aria-hidden', 'true');
    glow.setAttribute('aria-hidden', 'true');
    canvas.hidden = glow.hidden = true;
    document.body.prepend(canvas, glow);
    document.body.classList.add('has-home-field');

    var width = 0;
    var height = 0;
    var frame = 0;
    var lastPaint = null;
    var elapsed = 0;
    var scrollPosition = window.scrollY || 0;
    var nextBubble = 0.2;
    var active = false;
    var away = false;
    var palette = [];
    var colorTokens = ['--accent', '--sky-mid', '--mint', '--terracotta'];
    var bubbles = [];
    var pointer = { x: 0, y: 0, visible: false };
    var glowX = 0;
    var glowY = 0;
    var tau = Math.PI * 2;

    function random(low, high) { return low + Math.random() * (high - low); }
    function randomColor() { return Math.floor(random(0, colorTokens.length)); }

    // Softly boiling solution: round bubbles rise, sway, and fade near the surface.
    function makeBubble(initial) {
      var radius = random(3.5, 11);
      return {
        x: random(0.04, 0.96),
        y: initial ? random(0.05, 1.05) : 1.08 + random(0, 0.08),
        radius: radius,
        // Larger bubbles rise a little faster (Stokes-ish, not literal physics).
        speed: random(0.018, 0.038) * (0.7 + radius / 14),
        sway: random(0.012, 0.035),
        swaySpeed: random(0.35, 0.9),
        phase: random(0, tau),
        age: initial ? random(0, 8) : 0,
        life: random(10, 22),
        depth: random(0.12, 0.35),
        color: randomColor(),
        wobble: random(0.85, 1.15)
      };
    }

    function seedBubbles() {
      var count = window.innerWidth < 600 ? 14 : 26;
      bubbles = Array.from({ length: count }, function () { return makeBubble(true); });
    }

    function readPalette() {
      var style = getComputedStyle(document.documentElement);
      palette = colorTokens.map(function (token) {
        return style.getPropertyValue(token).trim();
      });
    }

    function resize() {
      if (!active) return;
      width = window.innerWidth;
      height = window.innerHeight;
      var ratio = Math.min(window.devicePixelRatio || 1, 1.5,
        Math.sqrt(3000000 / Math.max(1, width * height)));
      canvas.width = Math.round(width * ratio);
      canvas.height = Math.round(height * ratio);
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    }

    function hidePointer() {
      pointer.visible = false;
      glow.classList.remove('is-visible');
    }

    function parallaxY(y, depth, padding) {
      var span = height + padding * 2;
      return ((y - scrollPosition * depth + padding) % span + span) % span - padding;
    }

    function movePointer(event) {
      if (!active || !fine.matches || event.pointerType !== 'mouse') {
        hidePointer();
        return;
      }
      pointer.x = event.clientX;
      pointer.y = event.clientY;
      if (!pointer.visible) {
        glowX = pointer.x;
        glowY = pointer.y;
      }
      pointer.visible = true;
    }

    function drawBubble(b, cx, cy, alpha) {
      var r = b.radius * b.wobble;
      var color = palette[b.color] || palette[0];

      // Soft fill body
      ctx.globalAlpha = alpha * 0.14;
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, tau);
      ctx.fill();

      // Thin rim
      ctx.globalAlpha = alpha * 0.55;
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.1;
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, tau);
      ctx.stroke();

      // Specular highlight (upper-left), reads as a soap/solution bubble
      ctx.globalAlpha = alpha * 0.7;
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.ellipse(cx - r * 0.32, cy - r * 0.35, r * 0.22, r * 0.14, -0.5, 0, tau);
      ctx.fill();

      // Tiny secondary glint
      ctx.globalAlpha = alpha * 0.35;
      ctx.beginPath();
      ctx.arc(cx + r * 0.28, cy + r * 0.2, Math.max(0.8, r * 0.08), 0, tau);
      ctx.fill();
    }

    function draw(stamp) {
      frame = 0;
      if (!active) return;
      frame = window.requestAnimationFrame(draw);
      if (lastPaint !== null && stamp - lastPaint < 1000 / 30) return;
      var dt = lastPaint === null ? 0 : Math.min((stamp - lastPaint) / 1000, 0.08);
      lastPaint = stamp;
      elapsed += dt;
      scrollPosition += ((window.scrollY || 0) - scrollPosition) * (1 - Math.exp(-dt * 12));
      ctx.clearRect(0, 0, width, height);

      var compact = width < 600;
      var maxBubbles = compact ? 18 : 34;

      nextBubble -= dt;
      if (nextBubble <= 0) {
        if (bubbles.length < maxBubbles) bubbles.push(makeBubble(false));
        nextBubble = random(0.18, 0.55);
      }

      for (var i = bubbles.length - 1; i >= 0; i--) {
        var b = bubbles[i];
        b.age += dt;
        b.y -= b.speed * dt;
        // Gentle lateral sway — soft boil, not frantic
        var swayX = Math.sin(elapsed * b.swaySpeed + b.phase) * b.sway;
        // Slight breathing of radius
        b.wobble = 0.92 + 0.08 * Math.sin(elapsed * 1.4 + b.phase);

        // Mild pointer nudge (solution stirred, not repelled hard)
        var x = (b.x + swayX) * width;
        var y = parallaxY(b.y * height, b.depth, b.radius * 2);
        if (pointer.visible) {
          var dx = x - pointer.x;
          var dy = y - pointer.y;
          var distance = Math.hypot(dx, dy);
          if (distance > 0.1 && distance < 120) {
            var push = (1 - distance / 120) * 10 * dt / distance;
            b.x += dx * push / width;
            b.y += dy * push / height;
          }
        }

        // Pop / fade near the top or end of life
        var lifeFade = Math.min(1, b.age * 1.2, (b.life - b.age) / 1.8);
        var surfaceFade = b.y < 0.12 ? Math.max(0, b.y / 0.12) : 1;
        var alpha = lifeFade * surfaceFade;
        if (b.y < -0.06 || b.age >= b.life || alpha <= 0.02) {
          bubbles.splice(i, 1);
          continue;
        }

        x = (b.x + swayX) * width;
        y = parallaxY(b.y * height, b.depth, b.radius * 2);
        drawBubble(b, x, y, alpha);
      }
      ctx.globalAlpha = 1;

      if (pointer.visible) {
        var follow = 1 - Math.exp(-dt * 16);
        glowX += (pointer.x - glowX) * follow;
        glowY += (pointer.y - glowY) * follow;
        glow.style.transform = 'translate3d(' + glowX.toFixed(1) + 'px, ' +
          glowY.toFixed(1) + 'px, 0) translate(-50%, -50%)';
        glow.classList.add('is-visible');
      }
    }

    function configure() {
      active = !reduced.matches && !forced.matches && !print.matches && !document.hidden && !away;
      canvas.hidden = !active;
      glow.hidden = !active || !fine.matches;
      hidePointer();
      window.cancelAnimationFrame(frame);
      frame = 0;
      lastPaint = null;
      scrollPosition = window.scrollY || 0;
      window.removeEventListener('pointermove', movePointer);
      if (active) {
        readPalette();
        resize();
        if (!bubbles.length) seedBubbles();
        if (fine.matches) window.addEventListener('pointermove', movePointer, { passive: true });
        frame = window.requestAnimationFrame(draw);
      }
    }

    seedBubbles();

    new MutationObserver(function () {
      if (active) readPalette();
    }).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    [reduced, fine, forced, print].forEach(function (query) {
      query.addEventListener('change', configure);
    });
    window.addEventListener('resize', resize, { passive: true });
    window.addEventListener('blur', hidePointer);
    document.documentElement.addEventListener('pointerleave', hidePointer);
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Tab') hidePointer();
    });
    document.addEventListener('visibilitychange', configure);
    window.addEventListener('pagehide', function () { away = true; configure(); });
    window.addEventListener('pageshow', function () { away = false; configure(); });
    configure();
  });
})();
