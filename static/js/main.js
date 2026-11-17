/* Campus Lost & Found — shared JS */
const CSRF = document.querySelector('meta[name="csrf"]')?.content || '';

async function api(url, opts = {}) {
  const o = { headers: { 'X-CSRF-Token': CSRF, 'Content-Type': 'application/json' }, ...opts };
  const r = await fetch(url, o);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || 'Request failed');
  return data;
}

/* Theme */
function applyTheme(t) {
  const dark = t === 'dark' || (t === 'system' && matchMedia('(prefers-color-scheme: dark)').matches);
  document.documentElement.classList.toggle('dark', dark);
  const ic = document.getElementById('theme-icon');
  if (ic) ic.textContent = dark ? 'light_mode' : 'dark_mode';
}
function toggleTheme() {
  const next = document.documentElement.classList.contains('dark') ? 'light' : 'dark';
  localStorage.setItem('clf_theme', next); applyTheme(next);
}

/* Sidebar (mobile) */
function toggleSidebar(force) {
  const sb = document.getElementById('sidebar'), sc = document.getElementById('scrim');
  const open = force !== undefined ? force : !sb.classList.contains('open');
  sb.classList.toggle('open', open); sc.classList.toggle('show', open);
}

/* Live badge polling */
async function pollCounts() {
  try {
    const c = await api('/api/counts', { headers: {} });
    setBadge('badge-notes', c.notifications); setBadge('badge-msgs', c.messages);
  } catch (e) { /* signed out or offline */ }
}
function setBadge(id, n) {
  const el = document.getElementById(id); if (!el) return;
  el.textContent = n > 99 ? '99+' : n; el.classList.toggle('hidden', !n);
}

/* Image dropzone with preview */
function initDropzone() {
  const dz = document.getElementById('dropzone'); if (!dz) return;
  const input = dz.querySelector('input[type=file]');
  const render = (file) => {
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) { alert('Image must be under 5 MB.'); input.value = ''; return; }
    const url = URL.createObjectURL(file);
    dz.querySelector('.dz-content').innerHTML =
      `<img src="${url}" alt="preview"><div class="text-xs">${file.name} — click to change</div>`;
  };
  dz.addEventListener('click', () => input.click());
  input.addEventListener('click', e => e.stopPropagation());
  input.addEventListener('change', () => render(input.files[0]));
  ['dragenter', 'dragover'].forEach(ev => dz.addEventListener(ev, e => { e.preventDefault(); dz.classList.add('drag'); }));
  ['dragleave', 'drop'].forEach(ev => dz.addEventListener(ev, e => { e.preventDefault(); dz.classList.remove('drag'); }));
  dz.addEventListener('drop', e => { if (e.dataTransfer.files[0]) { input.files = e.dataTransfer.files; render(input.files[0]); } });
}

/* Confirm-on-submit helper: <form data-confirm="Are you sure?"> */
document.addEventListener('submit', e => {
  const msg = e.target.dataset?.confirm;
  if (msg && !confirm(msg)) e.preventDefault();
});

document.addEventListener('DOMContentLoaded', () => {
  applyTheme(localStorage.getItem('clf_theme') || 'light');
  initDropzone();
  setTimeout(() => document.querySelectorAll('.flash').forEach(f => f.remove()), 5000);
  if (document.getElementById('badge-notes')) { setInterval(pollCounts, 20000); }
});
