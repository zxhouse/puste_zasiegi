// Sterowanie stanem klonu (parametry URL) + eksport położeń elementów dla kompozycji w teledysku.
(function () {
  const q = new URLSearchParams(location.search);
  const on = (k, d = '0') => (q.get(k) || d) === '1';
  const num = (k, d) => parseInt(q.get(k) || d, 10);
  const $ = (s) => document.querySelector(s);
  if (on('capture')) document.body.classList.add('capture');

  // komentarze pod wpisem z filmem
  const nc = num('comments', '-1');
  if (nc >= 0) {
    $('#video-comments').hidden = false;
    document.querySelectorAll('#video-comments .comment').forEach((c) => {
      const k = parseInt(c.dataset.c, 10);
      c.hidden = !(k <= nc && (q.get('who') ? q.get('who').split(',').includes(String(k)) : true));
    });
    $('#no-comments').hidden = !on('empty');
  }
  if (on('analytics')) $('#analytics').hidden = false;
  // komentarz Mirka pod wpisem prezesa
  if (q.get('prezes') !== null) { $('#prezes-comments').hidden = false; $('#c-szacun').hidden = !on('prezes'); }
  // strona profilu z rekomendacjami (zamiast feedu); recs = ile rekomendacji już widać
  if (on('profile')) {
    document.querySelector('.layout').classList.add('profile-mode');
    $('#profile').hidden = false;
    const nr = num('recs', '3');
    document.querySelectorAll('#recs .rec').forEach((r) => { r.hidden = parseInt(r.dataset.r, 10) > nr; });
    $('#no-recs').hidden = nr > 0;
    $('.recs-n').textContent = '(' + nr + ')';
  }
  // przewinięcie strony do elementu (np. wpisu Tadka) - zrzut i tak jest pełną stroną; tu tylko podświetlenie
  if (q.get('focus')) { const e = document.getElementById(q.get('focus')); if (e) e.classList.add('focus'); }
  if (on('simple')) { $('#post-simple').hidden = false; $('#c-tadek').hidden = !on('tadek'); }
  if (on('chat')) $('#chat').hidden = false;
  if (on('sent')) $('#sent').hidden = false;
  if (on('typing')) document.querySelectorAll('.ph').forEach((p) => p.classList.add('typing'));
  if (on('noplay')) $('#vplay').classList.add('hidden');
  // liczniki zostawione puste w trybie przechwytywania (rysowane w kompozycji, żeby mogły rosnąć klatka po klatce)
  if (on('blankcounts')) document.querySelectorAll('[data-bind]').forEach((e) => { e.dataset.orig = e.textContent; e.style.visibility = 'hidden'; });
  // odtwarzanie filmu po kliknięciu w okładkę (normalne użycie strony)
  const v = $('#clip');
  if (v) v.addEventListener('play', () => $('#vplay').style.display = 'none');

  function rects() {
    const out = {};
    const add = (name, el) => { const r = el.getBoundingClientRect(); out[name] = [r.left + scrollX, r.top + scrollY, r.width, r.height]; };
    document.querySelectorAll('[data-rect]').forEach((e) => { if (e.offsetParent !== null || e.closest('.msg-dock')) add(e.dataset.rect, e); });
    ['post-video', 'post-grazyna', 'post-simple', 'post-prezes', 'post-kasia', 'post-tadek', 'video-comments', 'no-comments', 'c-tadek', 'nav', 'dock', 'chat', 'analytics', 'profile', 'recs', 'prezes-comments'].forEach((id) => {
      const e = document.getElementById(id); if (e && !e.hidden && e.offsetParent !== null || (e && (id === 'nav' || id === 'dock'))) add(id, e);
    });
    document.querySelectorAll('[data-bind]').forEach((e) => {
      const r = e.getBoundingClientRect(); const cs = getComputedStyle(e);
      out['bind_' + e.dataset.bind] = [r.left + scrollX, r.top + scrollY, r.width, r.height, parseFloat(cs.fontSize), cs.color, cs.fontWeight];
    });
    out.page = [0, 0, document.documentElement.scrollWidth, document.documentElement.scrollHeight];
    return out;
  }
  window.__rects = rects;
})();
