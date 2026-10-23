/* The production template's one script. A classic script, so the site also works opened straight from disk.
   Every part looks for its own markup and does nothing where there is none; the page works without any of it. */
(function () {
  'use strict';

  var root = document.documentElement;
  var data = {};
  try { data = JSON.parse(document.getElementById('site-data').textContent); } catch (e) { data = {}; }
  var reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  var $ = function (sel, el) { return (el || document).querySelector(sel); };
  var $$ = function (sel, el) { return Array.prototype.slice.call((el || document).querySelectorAll(sel)); };
  var pad = function (n) { return n < 10 ? '0' + n : String(n); };

  // ------------------------------------------------------------------ open now, in the shop's own time
  var DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  var DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
  function clock(m) {
    m = ((m % 1440) + 1440) % 1440;
    var h = Math.floor(m / 60), mm = m % 60;
    if (h === 12 && mm === 0) return 'noon';
    if (h === 0 && mm === 0) return 'midnight';
    var ap = h < 12 ? 'am' : 'pm', h12 = h % 12 || 12;
    return mm ? h12 + ':' + pad(mm) + ' ' + ap : h12 + ' ' + ap;
  }
  function shopNow() {
    var parts = {};
    try {
      new Intl.DateTimeFormat('en-US', { timeZone: data.timezone || undefined, weekday: 'short', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })
        .formatToParts(new Date()).forEach(function (p) { parts[p.type] = p.value; });
    } catch (e) {
      var d = new Date();
      return { day: (d.getDay() + 6) % 7, min: d.getHours() * 60 + d.getMinutes() };
    }
    return { day: DAYS.indexOf(parts.weekday), min: (+parts.hour % 24) * 60 + +parts.minute };
  }
  function openState() {
    var week = data.week;
    if (!week || !week.length) return null;
    var now = shopNow(), d = now.day, t = now.min, i, s;
    var today = week[d] || [], yesterday = week[(d + 6) % 7] || [];
    for (i = 0; i < today.length; i++) { s = today[i]; if (t >= s[0] && t < s[1]) return { open: true, closes: s[1], left: s[1] - t, day: d }; }
    for (i = 0; i < yesterday.length; i++) { s = yesterday[i]; if (s[1] > 1440 && t < s[1] - 1440) return { open: true, closes: s[1] - 1440, left: s[1] - 1440 - t, day: d }; }
    for (i = 0; i < today.length; i++) { if (today[i][0] > t) return { open: false, opens: today[i][0], when: 'today', day: d }; }
    for (var k = 1; k <= 7; k++) {
      var dd = (d + k) % 7, spans = week[dd] || [];
      if (spans.length) return { open: false, opens: spans[0][0], when: k === 1 ? 'tomorrow' : DAYS[dd], day: d };
    }
    return { open: false, day: d };
  }
  function showOpen() {
    var st = openState();
    if (!st) return;
    var text, state;
    if (st.open) {
      state = st.left <= 60 ? 'closing' : 'open';
      text = st.left <= 60 ? 'Open · closes in ' + st.left + ' min' : 'Open now · until ' + clock(st.closes);
    } else {
      state = 'closed';
      text = st.opens == null ? 'Closed' : 'Closed · opens ' + (st.when === 'today' ? '' : st.when + ' ') + clock(st.opens);
    }
    $$('[data-open]').forEach(function (el) {
      el.setAttribute('data-state', state);
      var t = $('[data-open-text]', el);
      if (t) t.textContent = text;
    });
    $$('.hours tr[data-day]').forEach(function (tr) { tr.classList.toggle('is-today', +tr.getAttribute('data-day') === st.day); });
  }
  showOpen();
  setInterval(showOpen, 60000);

  // ------------------------------------------------------------------ the strip: the colours of what it is over
  var strip = $('[data-strip]'), frame = $('[data-frame]');
  var grounds = $$('main > [data-ground], footer[data-ground]');
  function chromeLine() { return strip ? strip.getBoundingClientRect().bottom - 2 : 80; }
  var ticking = false;
  function onScroll() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(function () {
      ticking = false;
      root.classList.toggle('is-under', window.scrollY > 6);
      var line = chromeLine(), under = null;
      for (var i = 0; i < grounds.length; i++) {
        var r = grounds[i].getBoundingClientRect();
        if (r.top <= line && r.bottom > line) { under = grounds[i]; break; }
      }
      var g = under ? under.getAttribute('data-ground') : 'dark';
      if (g === 'ink') g = 'dark';
      if (strip && strip.getAttribute('data-ground') !== g) strip.setAttribute('data-ground', g);
      if (frame && frame.getAttribute('data-ground') !== g) frame.setAttribute('data-ground', g);
    });
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll);
  onScroll();

  // the page's own link is marked
  var page = root.getAttribute('data-page');
  $$('[data-nav]').forEach(function (a) { if (a.getAttribute('data-nav') === page) a.setAttribute('aria-current', 'page'); });

  // the services menu in the strip
  $$('.has-menu').forEach(function (cell) {
    var btn = $('.cell-btn', cell), list = $('.dropdown', cell);
    if (!btn || !list) return;
    var set = function (open) { btn.setAttribute('aria-expanded', String(open)); list.hidden = !open; };
    btn.addEventListener('click', function (e) { e.stopPropagation(); set(list.hidden); });
    document.addEventListener('click', function (e) { if (!cell.contains(e.target)) set(false); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !list.hidden) { set(false); btn.focus(); } });
  });

  // the phone's menu
  var menuBtn = $('.menu-btn'), menu = $('#menu');
  if (menuBtn && menu) {
    var setMenu = function (open) {
      menuBtn.setAttribute('aria-expanded', String(open));
      menu.hidden = !open;
      root.classList.toggle('is-menu', open);
      var word = menuBtn.querySelector('span');
      if (word) word.textContent = open ? 'Close' : 'Menu';
      if (strip && open) strip.setAttribute('data-ground', 'dark');
      if (!open) onScroll();
    };
    menuBtn.addEventListener('click', function () { setMenu(menu.hidden); });
    menu.addEventListener('click', function (e) { if (e.target.closest('a')) setMenu(false); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !menu.hidden) { setMenu(false); menuBtn.focus(); } });
    matchMedia('(min-width: 1024px)').addEventListener('change', function (m) { if (m.matches) setMenu(false); });
  }

  // ------------------------------------------------------------------ display type, fitted to its measure
  // The widest a line may run and the tallest its capitals may stand, as fractions of the box it lives in. Of the
  // widths Archivo can be set at, the narrowest that still fits under the height is used: the biggest letters that fit.
  var STRETCHES = [62, 75, 88, 100, 112, 125];
  var probe = document.createElement('span');
  probe.setAttribute('aria-hidden', 'true');
  probe.style.cssText = 'position:absolute;left:-9999px;top:0;visibility:hidden;white-space:nowrap;font-family:Archivo,sans-serif;font-weight:860;text-transform:uppercase;letter-spacing:-0.022em;word-spacing:0.12em;line-height:1;font-size:100px';
  document.body.appendChild(probe);
  function fit() {
    $$('[data-fit]').forEach(function (el) {
      var cs = getComputedStyle(el);
      var fw = parseFloat(cs.getPropertyValue('--fit-w')) || 0.9, fh = parseFloat(cs.getPropertyValue('--fit-h')) || 0.3;
      var box = el.closest('.hero, .closing, .page-head') || el.parentElement;
      var bs = getComputedStyle(box);
      var width = box.clientWidth - parseFloat(bs.paddingLeft) - parseFloat(bs.paddingRight);
      if (el.classList.contains('closing-name')) width = box.clientWidth - 2 * parseFloat(cs.paddingLeft || 0);
      if (window.innerWidth < 1024 && el.closest('.hero')) { fw = el.classList.contains('hero-a') || el.closest('.hero-a') ? 0.7 : 1; fh = el.closest('.hero-b') ? 0.13 : 0.24; }
      var maxW = width * fw, maxH = window.innerHeight * fh, cap = 0.72;
      probe.textContent = el.textContent;
      var chosen = null;
      for (var i = 0; i < STRETCHES.length; i++) {
        probe.style.fontStretch = STRETCHES[i] + '%';
        var w = probe.getBoundingClientRect().width / 100;
        if (!w) continue;
        var size = maxW / w;
        if (size * cap <= maxH) { chosen = { s: STRETCHES[i], size: size }; break; }
      }
      if (!chosen) {
        probe.style.fontStretch = '125%';
        chosen = { s: 125, size: maxH / cap };
      }
      el.style.setProperty('--stretch', chosen.s + '%');
      el.style.fontSize = Math.floor(chosen.size * 10) / 10 + 'px';
    });
    root.classList.add('is-fitted');
    drawLeaders();
  }
  var fitTimer;
  window.addEventListener('resize', function () { clearTimeout(fitTimer); fitTimer = setTimeout(fit, 120); });
  // (fonts.ready can settle before the display face has even been asked for: it is asked for by name, and the type
  // is fitted again whenever a face arrives, so a line is never left measured in a stand-in)
  fit();
  if (document.fonts && document.fonts.load) {
    Promise.all([document.fonts.load('860 100px "Archivo"'), document.fonts.ready]).then(fit, fit);
    document.fonts.addEventListener('loadingdone', fit);
  }

  // ------------------------------------------------------------------ the hero's zones: leaders from each label to its point
  var stage = $('[data-stage]'), svg = $('[data-leaders]'), carBox = $('[data-car]');
  var livePoints = null;
  function drawLeaders() {
    if (!stage || !svg || !carBox || window.innerWidth < 1024) return;
    var sr = stage.getBoundingClientRect(), cr = carBox.getBoundingClientRect();
    var lines = [];
    $$('.zone-labels .zone-label', stage).forEach(function (label) {
      var key = label.getAttribute('data-zone');
      var dot = $('.zone-dot[data-zone="' + key + '"]', carBox);
      if (!dot) return;
      var lr = label.getBoundingClientRect();
      var right = label.parentElement.classList.contains('z-paint') || label.parentElement.classList.contains('z-leadingEdge');
      var ax = (right ? lr.right : lr.left) - sr.left, ay = lr.bottom - sr.top;
      var p = livePoints && livePoints[key];
      var dx = (p ? p.x : parseFloat(dot.style.getPropertyValue('--x')) / 100) * cr.width + cr.left - sr.left;
      var dy = (p ? p.y : parseFloat(dot.style.getPropertyValue('--y')) / 100) * cr.height + cr.top - sr.top;
      var hidden = dot.classList.contains('is-hidden');
      lines.push('<polyline' + (hidden ? ' class="is-hidden"' : '') + ' points="' + ax.toFixed(1) + ',' + ay.toFixed(1) + ' ' + dx.toFixed(1) + ',' + dy.toFixed(1) + '"/>');
    });
    svg.setAttribute('viewBox', '0 0 ' + sr.width.toFixed(1) + ' ' + sr.height.toFixed(1));
    svg.innerHTML = lines.join('');
  }
  window.addEventListener('load', drawLeaders);

  // a zone pointed at is marked everywhere it appears: the label, the dot and the index cell
  var showroom = null;
  function markZone(key, on) {
    $$('[data-zone="' + key + '"]').forEach(function (el) { el.classList.toggle('is-on', on); });
  }
  $$('[data-zone]').forEach(function (el) {
    if (el.classList.contains('zone-dot')) return;
    var key = el.getAttribute('data-zone');
    el.addEventListener('mouseenter', function () { markZone(key, true); if (showroom) showroom.turnTo(key, 900); });
    el.addEventListener('mouseleave', function () { markZone(key, false); });
    el.addEventListener('focus', function () { markZone(key, true); });
    el.addEventListener('blur', function () { markZone(key, false); });
  });

  // ------------------------------------------------------------------ the car, live, where it can be
  function canGoLive() {
    if (!carBox || !data.car || reduced) return false;
    if (location.protocol === 'file:') return false;
    var c = navigator.connection;
    if (c && (c.saveData || /2g/.test(c.effectiveType || ''))) return false;
    if (/[?&]still\b/.test(location.search)) return false;
    try {
      var test = document.createElement('canvas');
      var gl = test.getContext('webgl2');
      if (!gl) return false;
      var lose = gl.getExtension('WEBGL_lose_context');
      if (lose) lose.loseContext();
      return true;
    } catch (e) { return false; }
  }
  function goLive() {
    if (!canGoLive()) return;
    var canvas = $('.car-live', carBox);
    // (an import written out would stop an old browser reading this whole file; and from a classic script it would
    // resolve against this file's address, so the module's address is made whole against the page's first)
    var load;
    try { load = new Function('u', 'return import(u)'); } catch (e) { return; }
    load(new URL(data.car.module, document.baseURI).href).then(function (m) {
      return m.mountShowroom({
        canvas: canvas, grip: carBox, base: new URL(data.car.base, document.baseURI).href, field: data.car.field, paint: data.car.paint, zones: data.car.zones,
        onFrame: function (points) {
          livePoints = points;
          Object.keys(points).forEach(function (k) {
            var dot = $('.zone-dot[data-zone="' + k + '"]', carBox), p = points[k];
            if (!dot) return;
            dot.style.left = (p.x * 100).toFixed(3) + '%';
            dot.style.top = (p.y * 100).toFixed(3) + '%';
            dot.classList.toggle('is-hidden', p.hidden);
          });
          drawLeaders();
        },
      });
    }).then(function (s) {
      showroom = s;
      root.classList.add('is-live');
      carBox.setAttribute('tabindex', '0');
      carBox.setAttribute('role', 'img');
      carBox.setAttribute('aria-label', 'The car. Drag it, or use the arrow keys, to turn it.');
      $$('[data-paint]').forEach(function (b) {
        b.addEventListener('click', function () {
          $$('[data-paint]').forEach(function (x) { x.setAttribute('aria-pressed', String(x === b)); });
          s.setPaint(b.getAttribute('data-paint'));
        });
      });
      if ('IntersectionObserver' in window) new IntersectionObserver(function (es) { s.setVisible(es[0].isIntersecting); }).observe(carBox);
    }).catch(function (e) {
      // the photograph stays; the visitor loses nothing but the turning
      root.classList.remove('is-live');
      if (window.console && console.warn) console.warn('The car stays a photograph here:', e && e.message ? e.message : e);
    });
  }
  if (carBox) {
    var whenIdle = window.requestIdleCallback || function (fn) { return setTimeout(fn, 600); };
    if (document.readyState === 'complete') whenIdle(goLive, { timeout: 2500 });
    else window.addEventListener('load', function () { whenIdle(goLive, { timeout: 2500 }); });
  }

  // ------------------------------------------------------------------ type rises as its section arrives
  if ('IntersectionObserver' in window && !reduced) {
    var rise = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('is-in'); rise.unobserve(e.target); } });
    }, { rootMargin: '0px 0px -12% 0px' });
    $$('[data-rise]').forEach(function (el) { rise.observe(el); });
  } else {
    $$('[data-rise]').forEach(function (el) { el.classList.add('is-in'); });
  }

  // ------------------------------------------------------------------ before and after: the tape
  $$('[data-ba]').forEach(function (st) {
    var fig = st.closest('.ba'), range = $('.ba-range', fig);
    var set = function (v) {
      v = Math.max(2, Math.min(98, v));
      fig.style.setProperty('--split', v.toFixed(2) + '%');
      if (range) { range.value = String(Math.round(v)); range.setAttribute('aria-valuetext', Math.round(v) + '% after'); }
    };
    var from = function (e) { var r = st.getBoundingClientRect(); set(((e.clientX - r.left) / r.width) * 100); };
    var id = -1, sx = 0, sy = 0, dragging = false;
    st.addEventListener('pointerdown', function (e) {
      id = e.pointerId; sx = e.clientX; sy = e.clientY; dragging = e.pointerType === 'mouse';
      if (dragging) { st.setPointerCapture(id); from(e); }
    });
    st.addEventListener('pointermove', function (e) {
      if (e.pointerId !== id) return;
      if (!dragging && Math.abs(e.clientX - sx) > 6 && Math.abs(e.clientX - sx) > Math.abs(e.clientY - sy)) { dragging = true; st.setPointerCapture(id); }
      if (dragging) from(e);
    });
    var end = function (e) { if (e.pointerId === id) { id = -1; dragging = false; } };
    st.addEventListener('pointerup', function (e) { if (!dragging && e.pointerType !== 'mouse' && Math.abs(e.clientX - sx) < 6) from(e); end(e); });
    st.addEventListener('pointercancel', end);
    if (range) range.addEventListener('input', function () { set(+range.value); });
    set(50);
  });
  // its tabs
  $$('.ba-tabs').forEach(function (list) {
    var tabs = $$('[role="tab"]', list);
    var pick = function (tab, focus) {
      tabs.forEach(function (t) {
        var on = t === tab;
        t.setAttribute('aria-selected', String(on));
        t.tabIndex = on ? 0 : -1;
        var panel = document.getElementById(t.getAttribute('aria-controls'));
        if (panel) panel.hidden = !on;
      });
      if (focus) tab.focus();
    };
    tabs.forEach(function (t, i) {
      t.addEventListener('click', function () { pick(t); });
      t.addEventListener('keydown', function (e) {
        var n = e.key === 'ArrowRight' ? i + 1 : e.key === 'ArrowLeft' ? i - 1 : e.key === 'Home' ? 0 : e.key === 'End' ? tabs.length - 1 : null;
        if (n === null) return;
        e.preventDefault();
        pick(tabs[(n + tabs.length) % tabs.length], true);
      });
    });
  });

  // ------------------------------------------------------------------ reviews: a rail, one card at a time
  $$('[data-rail]').forEach(function (rail) {
    var wrap = rail.closest('.quotes') || rail.parentElement;
    var prev = $('[data-rail-prev]', wrap), next = $('[data-rail-next]', wrap), count = $('[data-rail-count]', wrap);
    var cards = $$('.quote', rail);
    var current = function () {
      var r = rail.getBoundingClientRect(), best = 0, bestD = Infinity;
      cards.forEach(function (c, i) { var d = Math.abs(c.getBoundingClientRect().left - r.left); if (d < bestD) { bestD = d; best = i; } });
      return best;
    };
    var update = function () {
      var i = current();
      if (count) count.textContent = pad(i + 1) + ' / ' + pad(cards.length);
      if (prev) prev.disabled = rail.scrollLeft < 4;
      if (next) next.disabled = rail.scrollLeft + rail.clientWidth >= rail.scrollWidth - 4;
    };
    var go = function (d) {
      var i = Math.max(0, Math.min(cards.length - 1, current() + d));
      rail.scrollTo({ left: cards[i].offsetLeft - rail.offsetLeft - (cards[0].offsetLeft - rail.offsetLeft), behavior: reduced ? 'auto' : 'smooth' });
    };
    if (prev) prev.addEventListener('click', function () { go(-1); });
    if (next) next.addEventListener('click', function () { go(1); });
    rail.addEventListener('scroll', function () { requestAnimationFrame(update); }, { passive: true });
    rail.addEventListener('keydown', function (e) { if (e.key === 'ArrowRight') { e.preventDefault(); go(1); } if (e.key === 'ArrowLeft') { e.preventDefault(); go(-1); } });
    $$('[data-more]', rail).forEach(function (b) {
      b.addEventListener('click', function () {
        var q = b.closest('.quote'), open = !q.classList.contains('is-open');
        q.classList.toggle('is-open', open);
        b.setAttribute('aria-expanded', String(open));
        b.textContent = open ? 'Show less' : 'Read all of it';
      });
    });
    update();
  });

  // ------------------------------------------------------------------ the tint studio
  $$('[data-tint]').forEach(function (studio) {
    var range = $('.shade-range', studio);
    var values = (range.getAttribute('data-shades') || '100,70,50,35,20,5').split(',').map(Number);
    var stops = $$('.shade-stops button', studio);
    var label = $('[data-shade-label]', studio);
    var films = { front: $('.tint-film[data-glass="front"]', studio), rear: $('.tint-film[data-glass="rear"]', studio) };
    var reads = { front: $('[data-read="front"]', studio), rear: $('[data-read="rear"]', studio) };
    var state = { front: 35, rear: 35, target: 'both' };
    var floor = data.tint && data.tint.front_min;
    studio.style.setProperty('--stops', String(values.length));
    var warn = document.createElement('p');
    warn.className = 'legal-note';
    warn.hidden = true;
    range.parentElement.appendChild(warn);
    // film multiplies the light through the glass; seen from outside it is crossed twice, so a shade reads darker than its number
    var darkness = function (vlt) { return vlt >= 100 ? 0 : (1 - Math.pow(vlt / 100, 0.9)) / 0.97; };
    var name = function (v) { return v >= 100 ? 'No film' : v + '%'; };
    var apply = function () {
      ['front', 'rear'].forEach(function (g) {
        if (films[g]) films[g].style.setProperty('--dark', darkness(state[g]).toFixed(3));
        if (reads[g]) reads[g].textContent = name(state[g]);
      });
      var shown = state.target === 'rear' ? state.rear : state.front;
      var i = values.indexOf(shown);
      range.value = String(i < 0 ? 0 : i);
      range.setAttribute('aria-valuetext', shown >= 100 ? 'No film' : shown + '% of light through');
      if (label) label.textContent = name(shown);
      stops.forEach(function (b) { b.classList.toggle('is-on', +b.getAttribute('data-vlt') === shown); });
      var illegal = floor && state.front < floor;
      warn.hidden = !illegal;
      if (illegal) warn.textContent = state.front + '% is darker than the law allows on the front side windows here. It is fine behind the driver.';
    };
    var setShade = function (v) {
      if (state.target === 'both' || state.target === 'front') state.front = v;
      if (state.target === 'both' || state.target === 'rear') state.rear = v;
      apply();
    };
    range.addEventListener('input', function () { setShade(values[+range.value]); });
    stops.forEach(function (b) { b.addEventListener('click', function () { setShade(+b.getAttribute('data-vlt')); }); });
    $$('[data-target]', studio).forEach(function (b) {
      b.addEventListener('click', function () {
        $$('[data-target]', studio).forEach(function (x) { x.setAttribute('aria-checked', String(x === b)); });
        state.target = b.getAttribute('data-target');
        apply();
      });
    });
    $$('[data-film]', studio).forEach(function (b) {
      b.addEventListener('click', function () {
        $$('[data-film]', studio).forEach(function (x) { x.setAttribute('aria-checked', String(x === b)); });
        $$('[data-film-specs]', studio).forEach(function (d) { d.hidden = d.getAttribute('data-film-specs') !== b.getAttribute('data-film'); });
      });
    });
    apply();
  });

  // ------------------------------------------------------------------ the PPF sheet
  $$('[data-cover]').forEach(function (cover) {
    var buttons = $$('[data-cover-key]', cover);
    var pick = function (key) {
      cover.setAttribute('data-cover-on', key);
      buttons.forEach(function (b) { b.setAttribute('aria-checked', String(b.getAttribute('data-cover-key') === key)); });
      $$('[data-cover-panel]', cover).forEach(function (p) { p.hidden = p.getAttribute('data-cover-panel') !== key; });
    };
    buttons.forEach(function (b, i) {
      b.addEventListener('click', function () { pick(b.getAttribute('data-cover-key')); });
      b.addEventListener('keydown', function (e) {
        var n = e.key === 'ArrowRight' || e.key === 'ArrowDown' ? i + 1 : e.key === 'ArrowLeft' || e.key === 'ArrowUp' ? i - 1 : null;
        if (n === null) return;
        e.preventDefault();
        var b2 = buttons[(n + buttons.length) % buttons.length];
        pick(b2.getAttribute('data-cover-key'));
        b2.focus();
      });
    });
    var first = buttons.filter(function (b) { return b.getAttribute('aria-checked') === 'true'; })[0] || buttons[0];
    if (first) pick(first.getAttribute('data-cover-key'));
  });

  // ------------------------------------------------------------------ the work: filters and the lightbox
  var wall = $('[data-wall]');
  if (wall) {
    var prints = $$('.print', wall), status = $('[data-filter-status]');
    var filterBtns = $$('[data-filter]');
    var applyFilter = function (key) {
      var shown = 0;
      prints.forEach(function (p) {
        var on = key === 'all' || (' ' + p.getAttribute('data-tags') + ' ').indexOf(' ' + key + ' ') >= 0;
        p.classList.toggle('is-out', !on);
        if (on) shown++;
      });
      filterBtns.forEach(function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-filter') === key)); });
      if (status) status.textContent = key === 'all' ? '' : shown + (shown === 1 ? ' photograph' : ' photographs');
      try { history.replaceState(null, '', key === 'all' ? location.pathname + location.search : '#' + key); } catch (e) {}
    };
    filterBtns.forEach(function (b) { b.addEventListener('click', function () { applyFilter(b.getAttribute('data-filter')); }); });
    var start = location.hash.slice(1);
    if (start && filterBtns.some(function (b) { return b.getAttribute('data-filter') === start; })) applyFilter(start);

    var items = [];
    try { items = JSON.parse($('#gallery-data').textContent); } catch (e) { items = []; }
    var box = $('[data-lightbox]'), lbStage = box && $('[data-lb-stage]', box), lbCap = box && $('[data-lb-cap]', box), lbCount = box && $('[data-lb-count]', box);
    var at = 0;
    var visible = function () { return prints.filter(function (p) { return !p.classList.contains('is-out'); }).map(function (p) { return +p.getAttribute('data-index'); }); };
    var img = function (p, alt) { return '<img src="' + p.src + '" srcset="' + (p.srcset || '') + '" sizes="100vw" width="' + p.w + '" height="' + p.h + '" alt="' + (alt || p.alt || '').replace(/"/g, '&quot;') + '">'; };
    var show = function (i) {
      var it = items[i];
      if (!it || !lbStage) return;
      at = i;
      var html;
      if (it.kind === 'pair' && it.before && it.after) html = '<div class="pair"><figure>' + img(it.before) + '<figcaption class="spec">Before</figcaption></figure><figure>' + img(it.after) + '<figcaption class="spec">After</figcaption></figure></div>';
      else if (it.kind === 'video' && it.video) html = '<video src="' + it.video.src + '" controls playsinline autoplay' + (it.pic ? ' poster="' + it.pic.src + '"' : '') + '></video>';
      else html = img(it.pic);
      lbStage.innerHTML = html;
      var v = visible(), pos = v.indexOf(i);
      if (lbCount) lbCount.textContent = 'Frame ' + it.no + ' · ' + pad(pos + 1) + ' / ' + pad(v.length);
      if (lbCap) lbCap.textContent = it.caption + (it.render ? ' (studio render)' : '');
    };
    var step = function (d) { var v = visible(), pos = v.indexOf(at); if (v.length) show(v[(pos + d + v.length) % v.length]); };
    var close = function () { if (box.open) box.close(); };
    if (box && box.showModal) {
      $$('[data-open]', wall).forEach(function (b) {
        b.addEventListener('click', function () { show(+b.getAttribute('data-open')); box.showModal(); });
      });
      $('[data-lb-close]', box).addEventListener('click', close);
      $('[data-lb-prev]', box).addEventListener('click', function () { step(-1); });
      $('[data-lb-next]', box).addEventListener('click', function () { step(1); });
      box.addEventListener('keydown', function (e) { if (e.key === 'ArrowRight') step(1); if (e.key === 'ArrowLeft') step(-1); });
      box.addEventListener('close', function () { lbStage.innerHTML = ''; var b = $('[data-open="' + at + '"]', wall); if (b) b.focus(); });
      box.addEventListener('click', function (e) { if (e.target === box || e.target === lbStage) close(); });
      var tx = null;
      lbStage.addEventListener('touchstart', function (e) { tx = e.touches[0].clientX; }, { passive: true });
      lbStage.addEventListener('touchend', function (e) { if (tx === null) return; var dx = e.changedTouches[0].clientX - tx; if (Math.abs(dx) > 50) step(dx < 0 ? 1 : -1); tx = null; }, { passive: true });
    }
  }

  // ------------------------------------------------------------------ book: three steps, then the request goes where the shop wants it
  var form = $('[data-wizard]');
  if (form) {
    var cfg = data.booking || {};
    var steps = $$('[data-step]', form), tabs = $$('[data-step-tab]', form);
    var current = 1;
    var services = {};
    (cfg.services || []).forEach(function (s) { services[s.key] = s; });
    var classLabel = {};
    (cfg.classes || []).forEach(function (c) { classLabel[c.key] = c.label; });
    var money = function (n) { return '$' + Math.round(n).toLocaleString('en-US'); };

    var go = function (n) {
      current = n;
      steps.forEach(function (s) { s.hidden = +s.getAttribute('data-step') !== n; });
      tabs.forEach(function (t) {
        var k = +t.getAttribute('data-step-tab');
        if (k === n) t.setAttribute('aria-current', 'step'); else t.removeAttribute('aria-current');
        t.classList.toggle('is-done', k < n);
      });
      var legend = $('[data-step="' + n + '"] .step-title', form);
      var top = form.getBoundingClientRect().top + window.scrollY - (strip ? strip.getBoundingClientRect().bottom : 0) - 20;
      if (window.scrollY > top) window.scrollTo({ top: top, behavior: reduced ? 'auto' : 'smooth' });
      if (legend) { legend.setAttribute('tabindex', '-1'); legend.focus({ preventScroll: true }); }
    };
    var vehicle = function () { var r = $('input[name="vehicle"]:checked', form); return r ? r.value : ''; };
    var chosen = function () { return $$('input[name="services"]:checked', form).map(function (i) { return i.value; }); };
    var option = function (key) { var r = $('input[name="opt-' + key + '"]:checked', form); return r && r.value ? r : null; };

    // what the choices add up to, where the shop has said: a starting price, never a quote
    var estimate = function () {
      var v = vehicle(), total = 0, any = false, unknown = false;
      chosen().forEach(function (key) {
        if (key === 'advice') return;
        var s = services[key], opt = option(key), price = null;
        if (s && opt) {
          var o = (s.options || []).filter(function (x) { return x.key === opt.value; })[0];
          if (o) price = o.price != null ? o.price : o.prices && v && o.prices[v] != null ? o.prices[v] : o.from != null ? o.from : null;
        }
        if (price == null && s && s.options) {
          var lows = s.options.map(function (x) { return x.price != null ? x.price : x.prices && v && x.prices[v] != null ? x.prices[v] : x.from; }).filter(function (x) { return typeof x === 'number'; });
          if (lows.length) price = Math.min.apply(null, lows);
        }
        if (typeof price === 'number') { total += price; any = true; } else unknown = true;
      });
      return any ? { total: total, partial: unknown } : null;
    };

    var summary = function () {
      var v = vehicle(), model = form.elements.model.value.trim();
      var list = chosen().map(function (key) {
        if (key === 'advice') return 'Advice on what the car needs';
        var s = services[key], o = option(key);
        return (s ? s.title : key) + (o ? ' (' + o.getAttribute('data-label') + ')' : '');
      });
      var day = $('input[name="day"]:checked', form), time = $('input[name="time"]:checked', form);
      var est = estimate();
      var set = function (k, t) { var el = $('[data-sum="' + k + '"]'); if (el) el.textContent = t; };
      set('vehicle', v ? classLabel[v] + (model ? ', ' + model : '') : 'Not chosen yet');
      set('services', list.length ? list.join('; ') : 'Not chosen yet');
      set('day', (day ? day.getAttribute('data-label') : 'Flexible') + (time && time.value !== 'Any time' ? ', ' + time.value.toLowerCase() : ''));
      var row = $('[data-sum-row="estimate"]');
      if (row) { row.hidden = !est; if (est) set('estimate', money(est.total) + (est.partial ? ' + quote' : '')); }
      var e = $('[data-estimate]', form);
      if (e) { e.hidden = !est; if (est) e.textContent = 'From ' + money(est.total) + (est.partial ? ', plus what we quote after a look' : '') + (v ? ' for a ' + classLabel[v].toLowerCase() : '') + '. The final price is confirmed before any work begins.'; }
      return { vehicle: v ? classLabel[v] : '', model: model, services: list, day: day ? day.getAttribute('data-label') : 'Flexible', time: time ? time.value : 'Any time', estimate: est };
    };

    // the days the shop is open, from tomorrow, as the shop counts them
    var daysBox = $('[data-days]', form);
    if (daysBox) {
      var now = shopNow(), out = [], d = new Date();
      for (var k = 1; out.length < (cfg.days_ahead || 14) && k < 40; k++) {
        var day = new Date(d.getTime() + k * 864e5), idx = (now.day + k) % 7;
        if (data.week && data.week.length && !(data.week[idx] || []).length) continue;
        var label = DAY_NAMES[idx] + ' ' + day.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        out.push('<label class="day"><input type="radio" name="day" value="' + day.toISOString().slice(0, 10) + '" data-label="' + label + '"><span><span class="spec">' + DAYS[idx] + '</span><b>' + day.getDate() + '</b><span class="spec">' + day.toLocaleDateString('en-US', { month: 'short' }) + '</span></span></label>');
      }
      out.push('<label class="day flex"><input type="radio" name="day" value="" data-label="Flexible" checked><span><b class="spec">Flexible</b></span></label>');
      daysBox.innerHTML = out.join('');
    }

    var error = function (n, show) { var e = $('[data-error="' + n + '"]', form); if (e) e.hidden = !show; };
    var valid = function (n) {
      if (n === 1) { var ok1 = !!vehicle(); error(1, !ok1); return ok1; }
      if (n === 2) { var ok2 = chosen().length > 0; error(2, !ok2); return ok2; }
      if (n === 3) {
        var name = form.elements.name, phone = form.elements.phone;
        var okName = name.value.trim().length > 1, okPhone = phone.value.replace(/\D/g, '').length >= 7;
        name.setAttribute('aria-invalid', String(!okName));
        phone.setAttribute('aria-invalid', String(!okPhone));
        error(3, !(okName && okPhone));
        if (!okName) name.focus(); else if (!okPhone) phone.focus();
        return okName && okPhone;
      }
      return true;
    };
    $$('[data-next]', form).forEach(function (b) { b.addEventListener('click', function () { if (valid(current)) go(current + 1); }); });
    $$('[data-back]', form).forEach(function (b) { b.addEventListener('click', function () { go(current - 1); }); });
    tabs.forEach(function (t) { t.addEventListener('click', function () { var k = +t.getAttribute('data-step-tab'); if (k < current) go(k); }); });

    $$('input[name="services"]', form).forEach(function (i) {
      i.addEventListener('change', function () {
        var opts = $('[data-opts="' + i.value + '"]', form);
        if (opts) opts.hidden = !i.checked;
        error(2, false);
      });
    });
    form.addEventListener('change', function () { summary(); if (vehicle()) error(1, false); });
    form.addEventListener('input', function (e) { if (e.target.name === 'model') summary(); });

    // arriving from a service's page: that service, and that package, already chosen
    var params = new URLSearchParams(location.search);
    var pre = params.get('service');
    if (pre) {
      var box2 = $('input[name="services"][value="' + pre + '"]', form);
      if (box2) {
        box2.checked = true;
        var o2 = $('[data-opts="' + pre + '"]', form);
        if (o2) o2.hidden = false;
        var pk = params.get('package');
        var r2 = pk && $('input[name="opt-' + pre + '"][value="' + pk + '"]', form);
        if (r2) r2.checked = true;
      }
    }
    summary();

    var message = function (s) {
      var f = form.elements;
      var lines = ['Booking request from the website', '', 'Name: ' + f.name.value.trim(), 'Phone: ' + f.phone.value.trim()];
      if (f.email.value.trim()) lines.push('Email: ' + f.email.value.trim());
      lines.push('Vehicle: ' + s.vehicle + (s.model ? ', ' + s.model : ''));
      lines.push('Services: ' + s.services.join('; '));
      lines.push('Preferred day: ' + s.day + (s.time !== 'Any time' ? ', ' + s.time.toLowerCase() : ''));
      if (s.estimate) lines.push('Listed from: ' + money(s.estimate.total) + (s.estimate.partial ? ' + quote' : ''));
      if (f.notes.value.trim()) lines.push('Notes: ' + f.notes.value.trim());
      return lines.join('\n');
    };
    var openApp = function (kind, text) {
      var url = kind === 'text' ? 'sms:' + data.text + '?&body=' + encodeURIComponent(text)
        : kind === 'whatsapp' ? 'https://wa.me/' + data.whatsapp + '?text=' + encodeURIComponent(text)
        : kind === 'email' ? 'mailto:' + data.email + '?subject=' + encodeURIComponent('Booking request') + '&body=' + encodeURIComponent(text)
        : 'tel:' + data.tel;
      window.location.href = url;
    };
    var sent = $('[data-sent]', form);
    var done = function (text, note) {
      steps.forEach(function (s) { s.hidden = true; });
      $('.steps-nav', form).hidden = true;
      sent.hidden = false;
      $('[data-sent-summary]', sent).textContent = text;
      if (note) $('[data-sent-text]', sent).textContent = note;
      sent.focus();
    };
    var sendBtn = $('[data-send]', form);
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      if (!valid(3)) return;
      if (form.elements._honey && form.elements._honey.value) { done('', cfg.reply); return; }
      var s = summary(), text = message(s);
      var method = cfg.method;
      if (method === 'text' || method === 'whatsapp' || method === 'email' || method === 'call') {
        // the request is handed to the visitor's own app; the page says what happens next, in case nothing opened
        var app = { text: 'Your messages app', whatsapp: 'WhatsApp', email: 'Your email app', call: 'Your phone' }[method];
        done(text, app + (method === 'call' ? ' is calling us now. Tell us the request below.' : ' should have opened with this request written out. Press send there. If nothing opened, ' + (data.tel ? 'call or text us on ' + data.tel.replace(/^\+1(\d{3})(\d{3})(\d{4})$/, '($1) $2-$3') : 'call us') + '.'));
        openApp(method, text);
        return;
      }
      if (cfg.test_mode) { done(text, 'Preview build: nothing was sent. On the live site this request goes straight to ' + cfg.email_target + '.'); return; }
      var f = form.elements;
      var payload = { _subject: 'New booking request: ' + f.name.value.trim(), _template: 'table', _captcha: 'false', name: f.name.value.trim(), phone: f.phone.value.trim(), email: f.email.value.trim(),
        vehicle: s.vehicle + (s.model ? ', ' + s.model : ''), services: s.services.join('; '), day: s.day, time: s.time, notes: f.notes.value.trim(), listed_from: s.estimate ? money(s.estimate.total) : '', page: location.href };
      if (f.email.value.trim()) payload._replyto = f.email.value.trim();
      sendBtn.disabled = true;
      var label = sendBtn.innerHTML;
      sendBtn.textContent = 'Sending…';
      var post = function (mode) {
        return fetch(cfg.endpoint, mode === 'plain'
          ? { method: 'POST', mode: 'no-cors', headers: { 'Content-Type': 'text/plain;charset=UTF-8' }, body: JSON.stringify(payload) }
          : { method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' }, body: JSON.stringify(payload) });
      };
      post('json').then(function (r) {
        if (r.type === 'opaque' || r.ok) return r;
        throw new Error('HTTP ' + r.status);
      }).catch(function (err) {
        // a webhook that does not answer cross-origin requests still takes a plain one
        if (method === 'webhook') return post('plain');
        throw err;
      }).then(function () {
        done(text, cfg.reply);
      }).catch(function () {
        sendBtn.disabled = false;
        sendBtn.innerHTML = label;
        var e3 = $('[data-error="3"]', form);
        e3.hidden = false;
        e3.textContent = 'That did not go through. Please text or call us instead: the buttons below send the same request.';
      });
    });
    $$('[data-alt]', form).forEach(function (b) {
      b.addEventListener('click', function () { if (valid(3)) openApp(b.getAttribute('data-alt'), message(summary())); });
    });
  }
})();
