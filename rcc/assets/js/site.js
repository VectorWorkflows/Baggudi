/* Reliance Coaching Centre. Plain JavaScript, no dependencies.
   Everything here is an enhancement: the page reads fine without it. */
(function () {
  'use strict';

  var doc = document;

  function each(list, fn) {
    Array.prototype.forEach.call(list, fn);
  }

  /* ---- phone action bar: stays away until the hero has been scrolled past ---- */
  var bar = doc.querySelector('.actionbar');
  if (bar) {
    var hero = doc.querySelector('.hero');
    if (hero && 'IntersectionObserver' in window) {
      new IntersectionObserver(function (entries) {
        bar.classList.toggle('is-shown', !entries[entries.length - 1].isIntersecting);
      }).observe(hero);
    } else {
      bar.classList.add('is-shown');
    }
  }

  /* ---- red-pen and highlighter marks: draw each one once, when it scrolls into view ---- */
  var marks = doc.querySelectorAll('.mark:not(.mark--static), .hl');
  var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (reduced || !('IntersectionObserver' in window)) {
    each(marks, function (mark) { mark.classList.add('is-drawn'); });
  } else {
    var pen = new IntersectionObserver(function (entries) {
      var order = 0;
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        // Marks that arrive together are drawn one after another, like a hand moving down the page.
        entry.target.style.setProperty('--mark-delay', (order * 70) + 'ms');
        order += 1;
        entry.target.classList.add('is-drawn');
        pen.unobserve(entry.target);
      });
    }, { rootMargin: '0px 0px -10% 0px', threshold: 0.5 });
    // Start watching once the page has painted, so the marks already on
    // screen are drawn in front of the reader rather than before the first frame.
    window.requestAnimationFrame(function () {
      window.setTimeout(function () {
        each(marks, function (mark) { pen.observe(mark); });
      }, 180);
    });
  }

  /* ---- phone menu ---- */
  var menuButton = doc.querySelector('.menu-btn');
  var nav = doc.getElementById('site-nav');
  if (menuButton && nav) {
    var setMenu = function (open) {
      nav.classList.toggle('is-open', open);
      menuButton.setAttribute('aria-expanded', open ? 'true' : 'false');
    };
    menuButton.addEventListener('click', function () {
      setMenu(!nav.classList.contains('is-open'));
    });
    doc.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && nav.classList.contains('is-open')) {
        setMenu(false);
        menuButton.focus();
      }
    });
  }

  /* ---- find your batch: class, then subject, then the matching cards ---- */
  var finder = doc.querySelector('[data-finder]');
  if (finder) {
    var cards = finder.querySelectorAll('.batch');
    var subjectOptions = finder.querySelectorAll('.chipopt[data-classes]');
    var allOption = finder.querySelector('.chipopt[data-all]');
    var notes = finder.querySelectorAll('.finder__note');
    var status = finder.querySelector('[data-finder-status]');
    var empty = finder.querySelector('[data-finder-empty]');

    var appliesTo = function (el, cls) {
      return (' ' + el.getAttribute('data-classes') + ' ').indexOf(' ' + cls + ' ') !== -1;
    };
    var setOff = function (el, off) {
      if (off) el.setAttribute('data-off', ''); else el.removeAttribute('data-off');
    };

    var update = function (classChanged) {
      var classInput = finder.querySelector('input[name="class"]:checked');
      if (!classInput) return;
      var cls = classInput.value;

      var available = [];
      each(subjectOptions, function (option) {
        var on = appliesTo(option, cls);
        setOff(option, !on);
        if (on) available.push(option);
      });
      // One subject: show it, chosen. Several: offer "All" first.
      var single = available.length === 1;
      if (allOption) setOff(allOption, single);
      var chosen = finder.querySelector('input[name="subject"]:checked');
      var chosenHidden = !chosen || chosen.parentNode.hasAttribute('data-off');
      if (classChanged || chosenHidden) {
        chosen = single ? available[0].querySelector('input') : (allOption && allOption.querySelector('input'));
        if (chosen) chosen.checked = true;
      }
      var subject = chosen ? chosen.value : '';

      var shown = 0;
      each(cards, function (card) {
        var on = appliesTo(card, cls) && (!subject || card.getAttribute('data-subject') === subject);
        setOff(card, !on);
        if (!on) return;
        shown += 1;
        var link = card.querySelector('[data-demo-link]');
        if (link) {
          link.setAttribute('href', link.getAttribute('href').replace(/([?&]class=)[^&]*/, '$1' + encodeURIComponent(cls)));
        }
      });
      each(notes, function (note) { setOff(note, !appliesTo(note, cls)); });

      if (empty) empty.hidden = shown > 0;
      if (status) {
        var template = status.getAttribute(shown === 1 ? 'data-one' : 'data-many');
        status.textContent = template.replace('{n}', shown).replace('{cls}', classInput.getAttribute('data-label'));
      }
    };

    finder.addEventListener('change', function (event) {
      update(event.target.name === 'class');
    });
    // The browser may restore earlier choices when the page is revisited.
    window.addEventListener('pageshow', function () { update(false); });
  }
})();
