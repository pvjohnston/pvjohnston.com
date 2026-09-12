// Home-only progressive enhancement. The reel owns its content and sizing;
// this module only sets transforms and reveals below-fold sections once.
(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    var masthead = document.querySelector('#main > .masthead-home');
    if (!masthead) return;
    var main = masthead.parentElement;
    var featured = main.querySelector('.featured');
    var grid = featured && featured.querySelector('.featured-grid');
    var reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
    var fine = window.matchMedia('(hover: hover) and (pointer: fine)');
    var active = false;
    var inView = true;
    var frame = 0;
    var observer;

    function updateFigure() {
      frame = 0;
      // Measure the untransformed grid, never the moving figure itself.
      var rect = grid.getBoundingClientRect();
      var progress = (window.innerHeight - rect.top) / (window.innerHeight + rect.height);
      var offset = 8 * Math.max(0, Math.min(1, progress));
      featured.style.setProperty('--home-figure-y', offset.toFixed(2) + 'px');
    }

    function schedule() {
      if (active && inView && !frame) frame = window.requestAnimationFrame(updateFigure);
    }

    function reveal(section) {
      section.classList.remove('is-waiting');
      if (observer) observer.unobserve(section);
    }

    if ('IntersectionObserver' in window) {
      observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.target === featured) {
            inView = entry.isIntersecting;
            schedule();
          } else if (entry.isIntersecting) {
            reveal(entry.target);
          }
        });
      });
      if (featured) observer.observe(featured);

      if (!reduced.matches) {
        main.querySelectorAll(':scope > .latest, :scope > .process-feature').forEach(function (section) {
          // Never hide content already visible, including restored scroll positions.
          if (section.getBoundingClientRect().top < window.innerHeight) return;
          observer.observe(section);
          section.classList.add('home-reveal', 'is-waiting');
        });
      }
    }

    main.addEventListener('focusin', function (event) {
      var section = event.target.closest('.home-reveal');
      if (section) reveal(section);
    });

    function configure() {
      active = !!grid && !reduced.matches && fine.matches;
      if (active) {
        window.addEventListener('scroll', schedule, { passive: true });
        window.addEventListener('resize', schedule);
        schedule();
      } else {
        window.removeEventListener('scroll', schedule);
        window.removeEventListener('resize', schedule);
        window.cancelAnimationFrame(frame);
        frame = 0;
        if (featured) featured.style.removeProperty('--home-figure-y');
      }
      if (reduced.matches) {
        main.querySelectorAll('.home-reveal.is-waiting').forEach(reveal);
      }
    }

    reduced.addEventListener('change', configure);
    fine.addEventListener('change', configure);
    configure();
  });
})();
