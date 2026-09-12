// Decorative home field. Colors come from the live theme; the notebook,
// navigation, and featured reel remain ordinary, independent document content.
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
    var scale = 0;
    var frame = 0;
    var lastPaint = null;
    var elapsed = 0;
    var scrollPosition = window.scrollY || 0;
    var nextPhoton = random(.4, 1);
    var active = false;
    var away = false;
    var palette = [];
    var colorTokens = ['--accent', '--accent-deep', '--sky-mid', '--mint', '--terracotta', '--forest'];
    var washes = [];
    var photons = [];
    var pointer = { x: 0, y: 0, visible: false };
    var glowX = 0;
    var glowY = 0;
    var tau = Math.PI * 2;

    function random(low, high) { return low + Math.random() * (high - low); }

    function randomColor() { return Math.floor(random(0, colorTokens.length)); }
    function signedSpeed(low, high) { return random(low, high) * (Math.random() < .5 ? -1 : 1); }

    // Each visit gets a fresh field, with independent sizes, drift, and phases.
    // Smaller washes can mingle with broad ones instead of filling fixed corners.
    var blobs = Array.from({ length: 16 }, function () {
      return {
        x: random(.02, .98), y: random(.02, .98), color: randomColor(),
        radius: random(.085, .25), opacity: random(.58, .8),
        depth: random(.1, .2),
        vx: signedSpeed(.002, .009), vy: signedSpeed(.002, .008),
        phase: random(0, tau), pulseSpeed: random(.12, .38)
      };
    });
    var orbitals = Array.from({ length: 10 }, function () {
      var radius = random(.075, .23);
      return {
        x: random(.06, .94), y: random(.08, .92),
        rx: radius, ry: radius * random(.22, .65),
        angle: random(0, tau), speed: signedSpeed(.015, .065),
        color: randomColor(), opacity: random(.7, .95), lineWidth: random(.95, 1.4),
        depth: random(.22, .36),
        phase: random(0, tau), dotSpeed: signedSpeed(.18, .6), dotRadius: random(1.8, 2.8),
        driftSpeed: random(.07, .18), driftX: random(.01, .04), driftY: random(.01, .04)
      };
    });

    function makePhoton(initial) {
      return {
        x: random(.03, .97), y: initial ? random(.03, .97) : 1.02,
        vx: random(-.008, .008), speed: random(.03, .075),
        age: initial ? random(1, 6) : 0, life: random(20, 32),
        depth: random(.38, .5),
        color: randomColor(), radius: random(1.4, 2.4), trail: random(5, 15)
      };
    }
    // Populate the first frame as well as the lower edge during animation.
    photons = Array.from({ length: window.innerWidth < 600 ? 6 : 12 }, function () {
      return makePhoton(true);
    });

    function readPalette() {
      var style = getComputedStyle(document.documentElement);
      palette = colorTokens.map(function (token) {
        return style.getPropertyValue(token).trim();
      });
      // Rasterize the soft washes only on a theme change, not on every frame.
      washes = palette.map(function (color) {
        var wash = document.createElement('canvas');
        wash.width = wash.height = 192;
        var brush = wash.getContext('2d');
        var gradient = brush.createRadialGradient(96, 96, 0, 96, 96, 96);
        gradient.addColorStop(0, color);
        gradient.addColorStop(.16, color);
        gradient.addColorStop(1, 'transparent');
        brush.fillStyle = gradient;
        brush.fillRect(0, 0, 192, 192);
        return wash;
      });
    }

    function resize() {
      if (!active) return;
      width = window.innerWidth;
      height = window.innerHeight;
      scale = Math.min(width, height);
      // Bound fill cost on large / high-density displays; all geometry is CSS px.
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

    // The foreground travels at full scroll speed. These depths move the field
    // upward at 10–50% of that speed; wrap only beyond each shape's visible edge.
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

    function draw(stamp) {
      frame = 0;
      if (!active) return;
      frame = window.requestAnimationFrame(draw);
      // Time-based movement at at most 30 paints/sec, independent of refresh rate.
      if (lastPaint !== null && stamp - lastPaint < 1000 / 30) return;
      var dt = lastPaint === null ? 0 : Math.min((stamp - lastPaint) / 1000, .08);
      lastPaint = stamp;
      elapsed += dt;
      scrollPosition += ((window.scrollY || 0) - scrollPosition) * (1 - Math.exp(-dt * 12));
      ctx.clearRect(0, 0, width, height);

      var compact = width < 600;
      blobs.slice(0, compact ? 8 : 16).forEach(function (blob) {
        blob.x += blob.vx * dt;
        blob.y += blob.vy * dt;
        var padding = blob.radius * scale * 1.06;
        if (pointer.visible) {
          var dx = blob.x * width - pointer.x;
          var dy = parallaxY(blob.y * height, blob.depth, padding) - pointer.y;
          var distance = Math.hypot(dx, dy);
          // A bounded force avoids a singularity when the pointer hits the center.
          if (distance > .1 && distance < 180) {
            var push = (1 - distance / 180) * 18 * dt / distance;
            blob.x += dx * push / width;
            blob.y += dy * push / height;
          }
        }
        if (blob.x < -.35) blob.x = 1.35;
        if (blob.x > 1.35) blob.x = -.35;
        var pulse = Math.sin(elapsed * blob.pulseSpeed + blob.phase);
        var radius = blob.radius * scale * (1 + .06 * pulse);
        ctx.globalAlpha = blob.opacity + .08 * pulse;
        ctx.drawImage(washes[blob.color], blob.x * width - radius,
          parallaxY(blob.y * height, blob.depth, padding) - radius, radius * 2, radius * 2);
      });

      orbitals.slice(0, compact ? 5 : 10).forEach(function (orbit) {
        ctx.save();
        var drift = elapsed * orbit.driftSpeed + orbit.phase;
        ctx.translate((orbit.x + Math.sin(drift) * orbit.driftX) * width,
          parallaxY((orbit.y + Math.cos(drift * .8) * orbit.driftY) * height,
            orbit.depth, orbit.rx * scale + orbit.dotRadius));
        ctx.rotate(orbit.angle + elapsed * orbit.speed);
        ctx.strokeStyle = ctx.fillStyle = palette[orbit.color];
        ctx.globalAlpha = orbit.opacity;
        ctx.lineWidth = orbit.lineWidth;
        ctx.beginPath();
        ctx.ellipse(0, 0, orbit.rx * scale, orbit.ry * scale, 0, 0, tau);
        ctx.stroke();
        var phase = elapsed * orbit.dotSpeed + orbit.phase;
        ctx.globalAlpha = 1;
        ctx.beginPath();
        ctx.arc(Math.cos(phase) * orbit.rx * scale,
          Math.sin(phase) * orbit.ry * scale, orbit.dotRadius, 0, tau);
        ctx.fill();
        ctx.restore();
      });

      nextPhoton -= dt;
      if (nextPhoton <= 0) {
        if (photons.length < (compact ? 10 : 18)) {
          photons.push(makePhoton(false));
        }
        nextPhoton = random(.65, 1.25);
      }
      for (var i = photons.length - 1; i >= 0; i--) {
        var photon = photons[i];
        photon.age += dt;
        photon.x += photon.vx * dt;
        photon.y -= photon.speed * dt;
        if (photon.x < -.03 || photon.x > 1.03 || photon.age >= photon.life) {
          photons.splice(i, 1);
          continue;
        }
        var alpha = Math.min(1, photon.age, (photon.life - photon.age) / 2);
        var y = parallaxY(photon.y * height, photon.depth, photon.trail + photon.radius);
        ctx.fillStyle = ctx.strokeStyle = palette[photon.color];
        ctx.globalAlpha = alpha * .6;
        ctx.lineWidth = .9;
        ctx.beginPath();
        ctx.moveTo(photon.x * width, y + 2);
        ctx.lineTo(photon.x * width, y + photon.trail);
        ctx.stroke();
        ctx.globalAlpha = alpha;
        ctx.beginPath();
        ctx.arc(photon.x * width, y, photon.radius, 0, tau);
        ctx.fill();
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
        if (fine.matches) window.addEventListener('pointermove', movePointer, { passive: true });
        frame = window.requestAnimationFrame(draw);
      }
    }

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
