/* ==========================================================================
   Issue form usability behaviour
   1. Section-nav pills: active-state tracking via IntersectionObserver.
      Smooth scroll is handled by CSS (scroll-behavior: smooth on html).
   Used by: comicsdb/templates/comicsdb/issue_form.html
   ========================================================================== */
(function () {
    'use strict';

    /* ---- Section nav: active pill via IntersectionObserver --------------- */
    function initSectionNav() {
        var nav = document.querySelector('.usab-nav');
        if (!nav) {
            return;
        }
        var links = Array.prototype.slice.call(nav.querySelectorAll('a[href^="#"]'));

        var sections = links
            .map(function (l) { return document.querySelector(l.getAttribute('href')); })
            .filter(Boolean);

        if (!('IntersectionObserver' in window) || !sections.length) {
            return;
        }

        var io = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    var id = '#' + entry.target.id;
                    links.forEach(function (l) {
                        l.classList.toggle('is-active', l.getAttribute('href') === id);
                    });
                }
            });
        }, { rootMargin: '-45% 0px -50% 0px', threshold: 0 });

        sections.forEach(function (s) { io.observe(s); });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSectionNav);
    } else {
        initSectionNav();
    }
})();
