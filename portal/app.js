/* ==========================================================================
   CLIENT UPDATE PORTAL
   Swaps the details prompt to match the update type, collects photos (resized
   on the phone so they upload quickly from the shop), and posts everything to
   the endpoint below.

   The form has no action in the HTML, so it only sends through this script.
   ========================================================================== */
(() => {
  'use strict';

  // FormSubmit endpoint as base64 pieces (base URL, mailbox, domain), joined
  // only at send time so the inbox address appears nowhere in the page source.
  // This keeps it from scrapers that read HTML, not from anyone who reads this
  // file or watches the request. To change it, encode with btoa('...').
  const ENDPOINT_PARTS = ['aHR0cHM6Ly9mb3Jtc3VibWl0LmNv', 'c3VwcG9ydA==', 'dmVjdG9yd29ya2Zsb3dzLmNvbQ=='];
  const endpoint = () => {
    const [base, mailbox, domain] = ENDPOINT_PARTS.map((s) => atob(s));
    return `${base}/${mailbox}${String.fromCharCode(64)}${domain}`;
  };

  const MAX_PHOTOS = 10;
  const MAX_TOTAL_MB = 9;               // FormSubmit caps all files at 10 MB together; 9 MiB stays under it either way it counts
  const MAX_EDGE = 2048;                // px on the long side after resizing; the sites show 1280 at most
  const JPEG_QUALITY = 0.85;
  const KEEP_UNDER = 1.5 * 1024 * 1024; // a photo already this small and within MAX_EDGE is sent as is
  const STORE_KEY = 'vw-portal-client';

  // What to ask for under each update type. `done` finishes "Sam has ___ for <shop>."
  const TYPES = {
    '': {
      hint: 'Pick the kind of update above and we’ll show you what to include.',
      placeholder: 'What’s changing?',
      photos: 'Add anything that helps, like a shot of your price board.',
      done: 'your update',
    },
    'Change Package Prices': {
      hint: 'List each package with its old and new price. Say if a price depends on vehicle size.',
      placeholder: 'Full Detail (sedan): $180 → $199\nFull Detail (SUV/truck): $220 → $249\nCeramic, 3-year: $899 → $949',
      photos: 'Got a printed price sheet or board? A photo of it works too.',
      done: 'the new prices',
    },
    'Swap Gallery Photos': {
      hint: 'Say which photos come down and where the new ones go. Add the new ones below.',
      placeholder: 'Take down the white Tahoe and the red Civic.\nPut the black M4 first. That one got the full ceramic coat.',
      photos: 'Whole car in frame, good light, no one standing in the shot. Add up to 10.',
      done: 'the new photos',
    },
    'Update Business Hours': {
      hint: 'Give the hours for each day, and the date they start. Say if they’re only for a holiday or season.',
      placeholder: 'Mon–Fri 8am–6pm\nSat 9am–3pm\nSun closed\nStarting Nov 1',
      photos: 'Not usually needed for hours.',
      done: 'the new hours',
    },
    'Other': {
      hint: 'Tell us what to change and where it is on the site. Paste any new wording exactly as you want it.',
      placeholder: 'On the Ceramic Coating page, change the warranty line to:\n“5-year warranty, transferable to the next owner.”',
      photos: 'Add anything that helps, like a screenshot of the part to change.',
      done: 'your update',
    },
  };

  const $ = (id) => document.getElementById(id);
  const form = $('update-form');
  const nameIn = $('f-name');
  const shopIn = $('f-shop');
  const typeSel = $('f-type');
  const details = $('f-details');
  const detailsHint = $('f-details-hint');
  const photosHint = $('f-photos-hint');
  const fileIn = $('f-photos');
  const drop = $('drop');
  const thumbs = $('thumbs');
  const sum = $('thumbs-sum');
  const alertBox = $('alert');
  const sendBtn = $('send');
  const sendLabel = sendBtn.querySelector('.btn__label');
  const status = $('status');
  const done = $('done');

  form.noValidate = true; // our own messages replace the browser's bubbles

  /* Remembered client --------------------------------------------------------
     A link like baggudi.com/portal/?shop=AZ%20Detailers fills the shop in;
     otherwise this phone remembers who sent the last update. */
  const params = new URLSearchParams(location.search);
  const saved = readStore();
  nameIn.value = params.get('name') || saved.name || '';
  shopIn.value = params.get('shop') || saved.shop || '';

  function readStore() {
    try { return JSON.parse(localStorage.getItem(STORE_KEY)) || {}; } catch { return {}; }
  }
  function writeStore() {
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify({ name: nameIn.value.trim(), shop: shopIn.value.trim() }));
    } catch { /* private mode: nothing to remember */ }
  }

  /* Update type -> prompt ------------------------------------------------------ */
  function applyType() {
    const t = TYPES[typeSel.value] || TYPES[''];
    details.placeholder = t.placeholder;
    detailsHint.textContent = t.hint;
    photosHint.textContent = t.photos;
  }
  typeSel.addEventListener('change', () => { applyType(); clearError(typeSel); });
  applyType();

  /* Field errors --------------------------------------------------------------- */
  function showError(el, msg) {
    const err = $(el.id + '-err');
    err.querySelector('span').textContent = msg;
    err.hidden = false;
    el.setAttribute('aria-invalid', 'true');
    const ids = (el.getAttribute('aria-describedby') || '').split(' ').filter(Boolean);
    if (!ids.includes(err.id)) el.setAttribute('aria-describedby', [...ids, err.id].join(' '));
  }
  function clearError(el) {
    const err = $(el.id + '-err');
    if (!err || err.hidden) return;
    err.hidden = true;
    el.removeAttribute('aria-invalid');
    const ids = (el.getAttribute('aria-describedby') || '').split(' ').filter((id) => id && id !== err.id);
    if (ids.length) el.setAttribute('aria-describedby', ids.join(' '));
    else el.removeAttribute('aria-describedby');
  }
  for (const el of [nameIn, shopIn, details]) el.addEventListener('input', () => clearError(el));

  function validate() {
    const checks = [
      [nameIn, nameIn.value.trim(), 'Add your name.'],
      [shopIn, shopIn.value.trim(), 'Add your shop name.'],
      [typeSel, typeSel.value, 'Pick what kind of update this is.'],
      [details, details.value.trim(), 'Tell us what to change.'],
    ];
    let first = null;
    for (const [el, ok, msg] of checks) {
      if (ok) continue;
      showError(el, msg);
      first ??= el;
    }
    if (!first && totalBytes() > MAX_TOTAL_MB * 1024 * 1024) first = fileIn;
    first?.focus();
    return !first;
  }

  /* Photos ----------------------------------------------------------------------- */
  const photos = []; // { id, file, url, el, ready }
  let seq = 0;

  const isImage = (f) => f.type.startsWith('image/') || /\.(heic|heif)$/i.test(f.name);
  const totalBytes = () => photos.reduce((n, p) => n + p.file.size, 0);
  const mb = (bytes) => (bytes / 1048576).toFixed(bytes < 10485760 ? 1 : 0);

  function photoError(msg) {
    const err = $('f-photos-err');
    err.querySelector('span').textContent = msg;
    err.hidden = !msg;
    drop.classList.toggle('is-invalid', !!msg);
  }

  function addFiles(list) {
    const files = [...list];
    const images = files.filter(isImage);
    const room = MAX_PHOTOS - photos.length;
    photoError('');
    if (images.length > room) {
      photoError(room
        ? `Only ${room} more will fit. One update carries ${MAX_PHOTOS} photos, so send the rest in another.`
        : `That’s ${MAX_PHOTOS} photos, the most one update can carry. Send the rest in another update.`);
    } else if (images.length < files.length) {
      photoError('Only photos can go here. Other files were left out.');
    }
    for (const file of images.slice(0, Math.max(room, 0))) {
      const p = { id: ++seq, file, url: URL.createObjectURL(file) };
      p.el = thumb(p);
      p.ready = shrink(file, p.url).then((out) => {
        p.file = out;
        p.el.classList.remove('is-busy');
        summarise();
      });
      photos.push(p);
    }
    summarise();
  }

  function thumb(p) {
    const li = document.createElement('li');
    li.className = 'thumb is-busy';
    const img = new Image();
    img.alt = '';
    img.decoding = 'async';
    img.src = p.url;
    // HEIC dragged into a browser that can't show it: keep the file, show an icon
    img.onerror = () => { img.replaceWith(icon('i-image')); li.classList.add('is-raw'); };
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'thumb__remove';
    btn.setAttribute('aria-label', `Remove ${p.file.name}`);
    btn.append(icon('i-x'));
    btn.addEventListener('click', () => removePhoto(p));
    li.append(img, btn);
    thumbs.append(li);
    return li;
  }

  function icon(id) {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('class', 'icon');
    svg.setAttribute('aria-hidden', 'true');
    const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
    use.setAttribute('href', '#' + id);
    svg.append(use);
    return svg;
  }

  function removePhoto(p) {
    const i = photos.indexOf(p);
    if (i < 0) return;
    photos.splice(i, 1);
    URL.revokeObjectURL(p.url);
    p.el.remove();
    photoError('');
    summarise();
    // keep focus in the list so a keyboard or screen reader user isn't dropped to the top
    const next = photos[i] || photos[i - 1];
    (next ? next.el.querySelector('button') : fileIn).focus();
  }

  function clearPhotos() {
    for (const p of photos) URL.revokeObjectURL(p.url);
    photos.length = 0;
    thumbs.replaceChildren();
    photoError('');
    summarise();
  }

  function summarise() {
    const n = photos.length;
    thumbs.hidden = sum.hidden = n === 0;
    if (!n) return;
    const bytes = totalBytes();
    const busy = photos.some((p) => p.el.classList.contains('is-busy'));
    sum.textContent = `${n} photo${n === 1 ? '' : 's'} · ${busy ? 'preparing…' : mb(bytes) + ' MB'}`;
    if (!busy && bytes > MAX_TOTAL_MB * 1048576) {
      photoError(`These add up to ${mb(bytes)} MB and the limit is ${MAX_TOTAL_MB} MB. Remove a few and send them separately.`);
    }
  }

  // Resize big JPEG/HEIC/WebP photos on the phone. Drawing an <img> applies the
  // camera's EXIF rotation in every current browser, so shots stay upright.
  // Anything that fails to decode or wouldn't shrink is sent as picked.
  async function shrink(file, url) {
    if (!/^image\/(jpeg|webp|heic|heif)$/.test(file.type)) return file;
    try {
      const img = new Image();
      img.src = url;
      await img.decode();
      const scale = Math.min(1, MAX_EDGE / Math.max(img.naturalWidth, img.naturalHeight));
      if (scale === 1 && file.size <= KEEP_UNDER) return file;
      const canvas = document.createElement('canvas');
      canvas.width = Math.round(img.naturalWidth * scale);
      canvas.height = Math.round(img.naturalHeight * scale);
      canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
      const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', JPEG_QUALITY));
      canvas.width = canvas.height = 0; // hand the memory back straight away on iOS
      if (!blob || blob.size >= file.size) return file;
      const name = file.name.replace(/\.[^.]+$/, '') + '.jpg';
      return new File([blob], name, { type: 'image/jpeg', lastModified: file.lastModified });
    } catch {
      return file;
    }
  }

  fileIn.addEventListener('change', () => {
    addFiles(fileIn.files);
    fileIn.value = ''; // so picking the same photo again still fires
  });

  // Drag and drop (desktop). Dropping a file anywhere else must not open it in the tab.
  const hasFiles = (e) => [...(e.dataTransfer?.types || [])].includes('Files');
  for (const type of ['dragover', 'drop']) {
    window.addEventListener(type, (e) => { if (hasFiles(e)) e.preventDefault(); });
  }
  drop.addEventListener('dragenter', (e) => { if (hasFiles(e)) drop.classList.add('is-over'); });
  drop.addEventListener('dragover', (e) => { if (hasFiles(e)) e.dataTransfer.dropEffect = 'copy'; });
  drop.addEventListener('dragleave', (e) => { if (!drop.contains(e.relatedTarget)) drop.classList.remove('is-over'); });
  drop.addEventListener('drop', (e) => {
    drop.classList.remove('is-over');
    if (e.dataTransfer?.files.length) addFiles(e.dataTransfer.files);
  });

  /* Sending ---------------------------------------------------------------------- */
  function showAlert(msg) {
    alertBox.querySelector('span').textContent = msg;
    alertBox.hidden = false;
  }

  function setBusy(label, progress) {
    const on = label != null;
    sendBtn.disabled = on;
    sendBtn.setAttribute('aria-busy', String(on));
    sendLabel.textContent = on ? label : 'Send update';
    sendBtn.style.setProperty('--progress', on ? progress || 0 : 0);
  }

  // XHR rather than fetch: it reports upload progress, which matters on a slow
  // connection with photos attached.
  function post(url, data, onProgress) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', url);
      xhr.setRequestHeader('Accept', 'application/json');
      xhr.timeout = 180000;
      xhr.upload.onprogress = (e) => { if (e.lengthComputable) onProgress(e.loaded / e.total); };
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) return resolve();
        let detail = '';
        try {
          const body = JSON.parse(xhr.responseText);
          detail = body.errors?.map((x) => x.message).join(' ') || body.error || body.message || '';
        } catch { /* not JSON */ }
        reject(new Error(detail
          ? `It didn’t go through: ${detail}`
          : `It didn’t go through (error ${xhr.status}). Try again in a minute, or text Sam.`));
      };
      xhr.onerror = () => reject(new Error('Couldn’t reach the server. Everything you entered is still here, so try again when you have signal.'));
      xhr.ontimeout = () => reject(new Error('Sending took too long. Check your signal and try again.'));
      xhr.send(data);
    });
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (sendBtn.disabled) return;
    alertBox.hidden = true;
    if (!validate()) return;

    if (photos.length) {
      setBusy('Preparing photos…');
      await Promise.all(photos.map((p) => p.ready));
      if (totalBytes() > MAX_TOTAL_MB * 1048576) { setBusy(null); summarise(); fileIn.focus(); return; }
    }

    const shop = shopIn.value.trim();
    const type = typeSel.value;
    const data = new FormData(form);
    data.delete('photos');
    // one field per photo: FormSubmit's documented upload is a named field per file
    photos.forEach((p, i) => data.append(`photo_${i + 1}`, p.file, p.file.name));
    data.set('_subject', `Website update: ${shop} · ${type}`);

    setBusy('Sending…');
    status.textContent = 'Sending your update.';
    try {
      await post(endpoint(), data, (f) => {
        // the server's reply comes after the last byte, so hold the bar short of full
        sendBtn.style.setProperty('--progress', Math.min(f, 0.96));
        if (photos.length) sendLabel.textContent = `Sending… ${Math.round(f * 100)}%`;
      });
    } catch (err) {
      setBusy(null);
      status.textContent = '';
      showAlert(err.message);
      return;
    }

    writeStore();
    setBusy(null);
    status.textContent = '';
    const first = nameIn.value.trim().split(/\s+/)[0];
    $('done-name').textContent = first ? `, ${first}` : '';
    $('done-text').textContent = `Sam has ${(TYPES[type] || TYPES['']).done} for ${shop}. We’ll confirm once your site is updated.`;
    form.hidden = true;
    done.hidden = false;
    done.focus();
    done.scrollIntoView({ block: 'start', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
  });

  $('again').addEventListener('click', () => {
    typeSel.selectedIndex = 0;
    details.value = '';
    clearPhotos();
    applyType();
    done.hidden = true;
    form.hidden = false;
    typeSel.focus();
  });
})();
