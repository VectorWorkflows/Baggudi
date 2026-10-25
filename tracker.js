/* Demo alerts for baggudi.com: a Telegram message when someone opens a demo, and one more once they engage with it.
   No cookies. Quiet for bots, localhost, and any browser that has opened a demo with ?me=1 (Sam's; ?me=0 undoes it).
   On an expired demo's page (expire_demos.py writes it, loading this with data-expired="1") it sends one urgent alert instead.
   Each demo says so once per visit: refreshing or moving between its pages sends nothing new.
   The messages go through a Cloudflare Worker (demo-alerts-worker, outside this repo), which holds the bot token. */
(function () {
  var RELAY = 'https://demo-alerts.demo-alerts-worker.workers.dev/';
  var me = document.currentScript, d = document, n = navigator, l = location, ss, ls, tz = '';
  try { ss = sessionStorage; ls = localStorage; } catch (e) {}
  function get(s, k) { try { return s.getItem(k); } catch (e) {} }
  function set(s, k, v) { try { s.setItem(k, v); } catch (e) {} }
  try { tz = Intl.DateTimeFormat().resolvedOptions().timeZone || ''; } catch (e) {}
  if (/[?&]me=1/.test(l.search)) set(ls, 'vw-me', 1);
  if (/[?&]me=0/.test(l.search)) try { ls.removeItem('vw-me'); } catch (e) {}
  if (n.webdriver || /bot|crawl|spider|slurp|headless|lighthouse|preview|facebookexternalhit/i.test(n.userAgent) ||
      !/^https?:$/.test(l.protocol) || /^(localhost|127\.|0\.0\.0\.0|\[)/.test(l.hostname) ||
      get(ls, 'vw-me')) return;

  var slug = decodeURIComponent(l.pathname.split('/')[1] || '') || 'home', K = 'vw:' + slug + ':';
  // a beacon still goes out while the tab is closing, and plain text needs no CORS preflight
  // the Worker keeps visits from Sam's home network quiet unless the page has ?force_alert=1 (the beacon's Referer carries no query)
  function send(text) { n.sendBeacon && n.sendBeacon(RELAY + (/[?&]force_alert=1/.test(l.search) ? '?force_alert=1' : ''), text); }

  if (me && me.getAttribute('data-expired') == '1') {
    if (!get(ss, K + 'expired')) {
      set(ss, K + 'expired', 1);
      send('🚨 EXPIRED DEMO VISITED: ' + slug + ' just clicked their expired link! Restore: python expire_demos.py --restore ' + slug);
    }
    return;
  }

  if (!get(ss, K + 'open')) {
    set(ss, K + 'open', 1);
    var ua = n.userAgent, ref = d.referrer;
    var device = /iPhone|iPod/.test(ua) ? 'iPhone' : /iPad/.test(ua) || /Mac/.test(ua) && n.maxTouchPoints > 1 ? 'iPad' : /Android/.test(ua) ? 'Android' : 'Desktop';
    send('👀 DEMO OPENED: ' + slug + '\n📱 Device: ' + device + ' (' + screen.width + '×' + screen.height + ')\n🌎 Timezone: ' +
      (tz || 'unknown') + ' | Referrer: ' + (ref ? ref.replace(/^https?:\/\//, '').slice(0, 80) : 'direct'));
  }
  if (get(ss, K + 'done')) return;

  // seconds of viewing, what they touched and the pages they saw add up across the demo's pages
  var secs = +get(ss, K + 'secs') || 0, seen = (get(ss, K + 'seen') || '').split(',').filter(Boolean), pages = (+get(ss, K + 'pages') || 0) + 1, soon;
  set(ss, K + 'pages', pages);
  function engaged() {
    if (get(ss, K + 'done')) return;
    set(ss, K + 'done', 1);
    clearInterval(tick);
    send('🔥 ENGAGED: ' + slug + ' — stayed ' + Math.round(secs) + 's, ' + (pages > 1 ? 'saw ' + pages + ' pages, ' : '') +
      'interacted with: ' + (seen.join(' / ') || 'nothing, just reading') + '!');
  }
  // timers run late on a busy page (the 3D car), so time is read off the clock; a gap of minutes is a sleeping laptop
  var last = Date.now(), tick = setInterval(function () {
    var now = Date.now(), gap = now - last;
    last = now;
    if (d.visibilityState == 'visible' && gap < 6e4) { secs += gap / 1000; set(ss, K + 'secs', secs); if (secs >= 30) engaged(); }
  }, 1000);
  function touched(e) {
    var t = e.target, near = function (sel) { return t.closest && t.closest(sel); };
    // the detailing kit turns its car from anywhere over it and marks the page .is-turning while it does
    var what = e.type == 'submit' ? 'booking form' : near('[data-tint]') ? 'tint previewer' :
      near('input[type=range],[data-ba],.tape-strip,.tape-handle') ? 'before/after slider' :
      d.querySelector('.is-turning') || near('canvas,[data-car],.paint,.viewer') ? '3D car' :
      near('a[href^="tel:"],a[href^="sms:"],a[href^="mailto:"],a[href*="book"],button[type=submit],.btn') ? 'CTA' : '';
    if (!what) return;
    if (seen.indexOf(what) < 0) { seen.push(what); set(ss, K + 'seen', seen); }
    // a few seconds' grace, so a spin and then a slide arrive as one message
    if (!soon) soon = setTimeout(engaged, 5000);
  }
  ['pointerdown', 'pointerup', 'click', 'input', 'submit'].forEach(function (type) { d.addEventListener(type, touched, true); });
  // leaving after a touch or ten seconds still counts
  function leaving() { if (soon || secs >= 10) engaged(); }
  d.addEventListener('visibilitychange', function () { if (d.visibilityState == 'hidden') leaving(); });
  addEventListener('pagehide', leaving);
})();
