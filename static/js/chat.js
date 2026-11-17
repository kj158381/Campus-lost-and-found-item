/* AJAX chat: polls for new messages and posts without page reload */
(function () {
  const root = document.getElementById('chat');
  if (!root) return;
  const log = document.getElementById('chat-log');
  const form = document.getElementById('chat-form');
  const input = document.getElementById('chat-input');
  const base = `/api/chat/${root.dataset.item}/${root.dataset.other}/messages`;
  let lastId = parseInt(root.dataset.last || '0', 10);
  let lastDay = root.dataset.lastday || '';

  const scrollDown = () => { log.scrollTop = log.scrollHeight; };
  function add(m) {
    if (m.day !== lastDay) {
      const s = document.createElement('div'); s.className = 'day-sep'; s.textContent = m.day; log.appendChild(s); lastDay = m.day;
    }
    const b = document.createElement('div');
    b.className = 'bubble ' + (m.mine ? 'mine' : 'theirs');
    b.textContent = m.body;
    const t = document.createElement('small'); t.textContent = m.time; b.appendChild(t);
    log.appendChild(b); lastId = Math.max(lastId, m.id);
    const empty = document.getElementById('chat-empty'); if (empty) empty.remove();
  }
  async function poll() {
    try {
      const d = await api(`${base}?after=${lastId}`, { headers: {} });
      if (d.messages.length) { d.messages.forEach(add); scrollDown(); }
    } catch (e) {}
  }
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const body = input.value.trim(); if (!body) return;
    input.value = ''; input.focus();
    try { const d = await api(base, { method: 'POST', body: JSON.stringify({ body }) }); add(d.message); scrollDown(); }
    catch (err) { input.value = body; alert(err.message); }
  });
  input.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); } });
  scrollDown();
  setInterval(poll, 3000);
})();
