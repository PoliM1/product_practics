// static/js/dashboard.js
const API = '';
const token = localStorage.getItem('token');
if (!token) window.location.href = '/';
const H = { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' };

let currentOrgId = null;
let allTasks = [];
let orgMembers = [];

const ROLE_LABELS = {
  employee: '👤 Сотрудник', manager: '📋 Менеджер',
  reviewer: '✅ Проверяющий', boss: '👑 Руководитель',
};
const STATUS_LABELS = {
  pending: '🔵 В ожидании', in_progress: '🟡 В работе',
  on_review: '🟡 На проверке', completed: '🟢 Принято', rejected: '🔴 Отклонено',
};

// ── Инициализация ─────────────────────────────────────────────────────────────

async function init() {
  await loadCurrentUser();
  await loadOrgs();
  await loadInvitations();
}

async function loadCurrentUser() {
  const res = await fetch(API + '/auth/me', { headers: H });
  if (!res.ok) { logout(); return; }
  const u = await res.json();
  document.getElementById('sb-avatar').textContent = u.full_name[0].toUpperCase();
  document.getElementById('sb-name').textContent   = u.full_name;
  document.getElementById('sb-role').textContent   = ROLE_LABELS[u.role] || u.role;
}

// ── Организации ───────────────────────────────────────────────────────────────

async function loadOrgs() {
  const res = await fetch(API + '/orgs/my-orgs', { headers: H });
  if (!res.ok) return;
  const orgs = await res.json();

  const select = document.getElementById('org-select');
  select.innerHTML = '<option value="">— Выберите организацию —</option>';
  orgs.forEach(o => {
    select.innerHTML += `<option value="${o.id}">${o.name}</option>`;
  });

  if (orgs.length > 0) {
    currentOrgId = orgs[0].id;
    select.value = currentOrgId;
    await loadTasks();
    await loadMembers();
  }
}

async function onOrgChange() {
  currentOrgId = document.getElementById('org-select').value || null;
  if (currentOrgId) {
    await loadTasks();
    await loadMembers();
  } else {
    clearBoard();
  }
}

async function loadMembers() {
  if (!currentOrgId) return;
  const res = await fetch(API + `/orgs/${currentOrgId}/members`, { headers: H });
  if (!res.ok) return;
  orgMembers = await res.json();

  const opts = orgMembers.map(m =>
    `<option value="${m.id}">${m.full_name} — ${m.position}</option>`
  ).join('');
  document.getElementById('new-task-assignee').innerHTML = '<option value="">— Не назначен —</option>' + opts;
  document.getElementById('new-task-reviewer').innerHTML = '<option value="">— Не назначен —</option>' + opts;
}

// ── Задачи ────────────────────────────────────────────────────────────────────

async function loadTasks() {
  if (!currentOrgId) return;
  ['pending','work','done','rejected'].forEach(c => {
    const el = document.getElementById('col-' + c);
    if (el) el.innerHTML = '<div class="loading"></div>';
  });

  const res = await fetch(API + `/tasks/org/${currentOrgId}`, { headers: H });
  if (!res.ok) return;
  allTasks = await res.json();
  renderKanban();
  renderStats();
}

function renderStats() {
  const c = { pending: 0, work: 0, done: 0, rejected: 0 };
  allTasks.forEach(t => {
    if (t.status === 'pending') c.pending++;
    else if (t.status === 'in_progress' || t.status === 'on_review') c.work++;
    else if (t.status === 'completed') c.done++;
    else if (t.status === 'rejected') c.rejected++;
  });
  document.getElementById('count-pending').textContent  = c.pending;
  document.getElementById('count-work').textContent     = c.work;
  document.getElementById('count-done').textContent     = c.done;
  document.getElementById('count-rejected').textContent = c.rejected;
}

function renderKanban() {
  const cols = {
    pending:  { el: document.getElementById('col-pending'),  cnt: 0 },
    work:     { el: document.getElementById('col-work'),     cnt: 0 },
    done:     { el: document.getElementById('col-done'),     cnt: 0 },
    rejected: { el: document.getElementById('col-rejected'), cnt: 0 },
  };
  Object.values(cols).forEach(c => { if (c.el) c.el.innerHTML = ''; });

  if (allTasks.length === 0) {
    if (cols.pending.el) cols.pending.el.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">📋</div>
        <p>Задач пока нет.<br>Создайте первую!</p>
      </div>`;
    return;
  }

  allTasks.forEach(task => {
    let colKey = 'pending';
    if (task.status === 'in_progress' || task.status === 'on_review') colKey = 'work';
    else if (task.status === 'completed') colKey = 'done';
    else if (task.status === 'rejected')  colKey = 'rejected';

    cols[colKey].cnt++;
    const col = cols[colKey].el;
    if (!col) return;

    const deadline = task.deadline
      ? `<div class="task-deadline">⏰ ${new Date(task.deadline).toLocaleDateString('ru')}</div>` : '';
    const tf = task.files.filter(f => f.type === 'task_file').length;
    const rf = task.files.filter(f => f.type === 'result_file').length;
    const filesInfo = (tf || rf)
      ? `<div style="font-size:11px;color:var(--gray);margin-top:4px;">
           ${tf ? `📎 Задание: ${tf}` : ''}${rf ? ` • 📤 Результат: ${rf}` : ''}
         </div>` : '';

    col.innerHTML += `
      <div class="task-card ${task.status}" onclick="openTask(${task.id})">
        <span class="status-badge badge-${task.status}">${STATUS_LABELS[task.status]}</span>
        <div class="task-title">${escHtml(task.title)}</div>
        <div class="task-meta">
          <span>👤 ${escHtml(task.assignee?.name || 'Не назначен')}</span>
          <span>✍️ ${escHtml(task.creator?.name || '')}</span>
        </div>
        ${deadline}${filesInfo}
      </div>`;
  });

  document.getElementById('cnt-pending').textContent  = cols.pending.cnt;
  document.getElementById('cnt-work').textContent     = cols.work.cnt;
  document.getElementById('cnt-done').textContent     = cols.done.cnt;
  document.getElementById('cnt-rejected').textContent = cols.rejected.cnt;
}

function clearBoard() {
  ['pending','work','done','rejected'].forEach(c => {
    const el = document.getElementById('col-' + c);
    if (el) el.innerHTML = '';
  });
  allTasks = [];
  renderStats();
}

// ── Открытие задачи ───────────────────────────────────────────────────────────

function openTask(taskId) {
  const task = allTasks.find(t => t.id === taskId);
  if (!task) return;
  const userId = parseInt(localStorage.getItem('userId'));

  document.getElementById('m-title').textContent    = task.title;
  document.getElementById('m-desc').textContent     = task.description || 'Нет описания';
  document.getElementById('m-status').innerHTML     = `<span class="status-badge badge-${task.status}">${STATUS_LABELS[task.status]}</span>`;
  document.getElementById('m-assignee').textContent = task.assignee?.name || 'Не назначен';
  document.getElementById('m-reviewer').textContent = task.reviewer?.name || 'Не назначен';
  document.getElementById('m-deadline').textContent = task.deadline || 'Не указан';
  document.getElementById('m-comment').textContent  = task.review_comment || '';
  document.getElementById('m-comment-section').style.display = task.review_comment ? '' : 'none';
  document.getElementById('current-task-id').value  = taskId;

  const taskFiles   = task.files.filter(f => f.type === 'task_file');
  const resultFiles = task.files.filter(f => f.type === 'result_file');
  document.getElementById('m-task-files').innerHTML   = renderFileList(taskFiles);
  document.getElementById('m-result-files').innerHTML = renderFileList(resultFiles);

  const isAssignee = task.assignee?.id === userId;
  const isReviewer = task.reviewer?.id === userId;
  const isCreator  = task.creator?.id  === userId;

  const actions = document.getElementById('m-actions');
  actions.innerHTML = '';
  if (isAssignee && task.status === 'pending')
    actions.innerHTML += `<button class="btn-secondary" onclick="changeStatus('in_progress')">▶️ Взять в работу</button>`;
  if (isAssignee && task.status === 'in_progress')
    actions.innerHTML += `<button class="btn-secondary" onclick="changeStatus('on_review')">🔍 Отправить на проверку</button>`;

  const showUpload = isAssignee && ['pending','in_progress'].includes(task.status);
  document.getElementById('upload-result-section').style.display = showUpload ? '' : 'none';

  const canReview = (isReviewer || isCreator) && ['on_review','in_progress','pending'].includes(task.status);
  document.getElementById('review-actions-section').style.display = canReview ? '' : 'none';
  document.getElementById('reject-form').classList.add('hidden');
  document.getElementById('reject-comment').value = '';

  openModal('task-modal-overlay');
}

function renderFileList(files) {
  if (!files.length) return '<div style="color:var(--gray);font-size:13px;padding:8px 0;">Нет файлов</div>';
  const icons = {'.docx':'📝','.doc':'📝','.xlsx':'📊','.xls':'📊','.pdf':'📄','.txt':'📃','.accdb':'🗄️','.mdb':'🗄️'};
  return files.map(f => {
    const ext  = '.' + f.name.split('.').pop().toLowerCase();
    const icon = icons[ext] || '📎';
    const badge = f.type === 'result_file'
      ? '<span class="status-badge badge-completed" style="font-size:10px;">Результат</span>'
      : '<span class="status-badge badge-pending"   style="font-size:10px;">Задание</span>';
    return `
      <div class="file-item">
        <span class="file-icon">${icon}</span>
        <span class="file-name">${escHtml(f.name)}</span>
        ${badge}
        <a href="/tasks/file/${f.id}/download" target="_blank">Скачать</a>
      </div>`;
  }).join('');
}

// ── Смена статуса ─────────────────────────────────────────────────────────────

async function changeStatus(status) {
  const taskId  = document.getElementById('current-task-id').value;
  const comment = document.getElementById('reject-comment').value;
  let url = `/tasks/${taskId}/status?status=${status}`;
  if (comment) url += `&comment=${encodeURIComponent(comment)}`;

  const res  = await fetch(API + url, { method: 'PATCH', headers: H });
  const data = await res.json();
  if (res.ok) { closeModal('task-modal-overlay'); await loadTasks(); }
  else alert(data.detail || 'Ошибка изменения статуса');
}

function showRejectForm() {
  document.getElementById('reject-form').classList.remove('hidden');
}

// ── Загрузка результата ───────────────────────────────────────────────────────

async function uploadResult() {
  const taskId = document.getElementById('current-task-id').value;
  const file   = document.getElementById('result-file-input').files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append('file', file);

  const res  = await fetch(API + `/tasks/${taskId}/upload-result`, {
    method: 'POST',
    headers: { 'Authorization': 'Bearer ' + token },
    body: formData,
  });
  const data = await res.json();

  if (res.ok) {
    alert('✅ ' + data.message);
    closeModal('task-modal-overlay');
    await loadTasks();
  } else {
    alert(data.detail || 'Ошибка загрузки');
  }
  document.getElementById('result-file-input').value = '';
}

// ── Создание задачи ───────────────────────────────────────────────────────────

function showCreateTaskModal() {
  if (!currentOrgId) { alert('Сначала выберите организацию'); return; }
  openModal('create-task-modal');
}

function updateFileList() {
  const files     = document.getElementById('task-files-input').files;
  const container = document.getElementById('selected-files');
  container.innerHTML = '';
  Array.from(files).forEach(f => {
    container.innerHTML += `
      <div class="file-item">
        <span class="file-icon">📎</span>
        <span class="file-name">${escHtml(f.name)}</span>
        <span class="file-type">${(f.size/1024).toFixed(0)} KB</span>
      </div>`;
  });
}

async function createTask() {
  const title = document.getElementById('new-task-title').value.trim();
  if (!title) { alert('Введите название задачи'); return; }

  const formData = new FormData();
  formData.append('title',       title);
  formData.append('description', document.getElementById('new-task-desc').value);
  formData.append('org_id',      currentOrgId);

  const assignee = document.getElementById('new-task-assignee').value;
  const reviewer = document.getElementById('new-task-reviewer').value;
  const deadline = document.getElementById('new-task-deadline').value;
  if (assignee) formData.append('assignee_id', assignee);
  if (reviewer) formData.append('reviewer_id', reviewer);
  if (deadline) formData.append('deadline',    deadline);

  Array.from(document.getElementById('task-files-input').files).forEach(f => {
    formData.append('files', f);
  });

  const res  = await fetch(API + '/tasks/create', {
    method: 'POST',
    headers: { 'Authorization': 'Bearer ' + token },
    body: formData,
  });
  const data = await res.json();

  if (res.ok) {
    closeModal('create-task-modal');
    document.getElementById('new-task-title').value = '';
    document.getElementById('new-task-desc').value  = '';
    document.getElementById('task-files-input').value = '';
    document.getElementById('selected-files').innerHTML = '';
    await loadTasks();
  } else {
    alert(data.detail || 'Ошибка создания задачи');
  }
}

// ── Создание организации ──────────────────────────────────────────────────────

function showCreateOrgModal() {
  document.getElementById('new-org-name').value = '';
  document.getElementById('new-org-desc').value = '';
  openModal('create-org-modal');
}

async function createOrg() {
  const name = document.getElementById('new-org-name').value.trim();
  const desc = document.getElementById('new-org-desc').value.trim();
  if (!name) { alert('Введите название организации'); return; }

  const res  = await fetch(API + '/orgs/create', {
    method: 'POST', headers: H,
    body: JSON.stringify({ name, description: desc }),
  });
  const data = await res.json();

  if (res.ok) {
    closeModal('create-org-modal');
    await loadOrgs();
    // Выбираем только что созданную организацию
    document.getElementById('org-select').value = data.id;
    currentOrgId = String(data.id);
    await loadTasks();
    await loadMembers();
    alert('✅ Организация «' + name + '» создана!');
  } else {
    alert(data.detail || 'Ошибка создания организации');
  }
}

// ── Приглашения ───────────────────────────────────────────────────────────────

async function loadInvitations() {
  const res = await fetch(API + '/orgs/my-invitations', { headers: H });
  if (!res.ok) return;
  const invitations = await res.json();
  const badge = document.getElementById('inv-badge');
  if (invitations.length > 0) {
    badge.textContent = invitations.length;
    badge.classList.remove('hidden');
  } else {
    badge.classList.add('hidden');
  }
}

async function showInvitationsModal() {
  openModal('invitations-modal');
  const res  = await fetch(API + '/orgs/my-invitations', { headers: H });
  const invs = await res.json();
  const container = document.getElementById('invitations-list');

  if (!invs.length) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">📭</div>
        <p>Нет новых приглашений</p>
      </div>`;
    return;
  }

  container.innerHTML = invs.map(inv => `
    <div class="invitation-card">
      <div class="invitation-info">
        <div class="org-name">🏢 ${escHtml(inv.org_name)}</div>
        <div class="org-owner">Приглашает: ${escHtml(inv.owner_name)}</div>
      </div>
      <div class="invitation-actions">
        <button class="btn-success btn-sm" onclick="acceptInvitation(${inv.id})">✅ Принять</button>
        <button class="btn-danger  btn-sm" onclick="declineInvitation(${inv.id})">❌ Отклонить</button>
      </div>
    </div>`).join('');
}

async function acceptInvitation(invId) {
  const res = await fetch(API + `/orgs/invitations/${invId}/accept`, { method: 'POST', headers: H });
  if (res.ok) { closeModal('invitations-modal'); await loadOrgs(); await loadInvitations(); }
}
async function declineInvitation(invId) {
  const res = await fetch(API + `/orgs/invitations/${invId}/decline`, { method: 'POST', headers: H });
  if (res.ok) { await showInvitationsModal(); await loadInvitations(); }
}

// ── Поиск пользователей ───────────────────────────────────────────────────────

function showInviteModal() {
  if (!currentOrgId) { alert('Сначала выберите организацию'); return; }
  document.getElementById('invite-search').value = '';
  document.getElementById('search-results').innerHTML = '';
  openModal('invite-modal');
}

let searchTimeout;
async function searchUsers() {
  clearTimeout(searchTimeout);
  const q = document.getElementById('invite-search').value.trim();
  if (q.length < 2) { document.getElementById('search-results').innerHTML = ''; return; }

  searchTimeout = setTimeout(async () => {
    const res   = await fetch(API + `/users/search?q=${encodeURIComponent(q)}`, { headers: H });
    const users = await res.json();
    const container = document.getElementById('search-results');

    if (!users.length) {
      container.innerHTML = '<p style="color:var(--gray);padding:12px;font-size:14px;">Пользователи не найдены</p>';
      return;
    }

    container.innerHTML = users.map(u => `
      <div class="file-item" style="margin-top:8px;">
        <span class="file-icon">👤</span>
        <div style="flex:1;">
          <div style="font-weight:600;font-size:14px;">${escHtml(u.full_name)}</div>
          <div style="font-size:12px;color:var(--gray);">${escHtml(u.email)} • ${escHtml(u.position)}</div>
        </div>
        <button class="btn-secondary btn-sm" onclick="inviteUser(${u.id}, '${escHtml(u.full_name)}')">
          Пригласить
        </button>
      </div>`).join('');
  }, 400);
}

async function inviteUser(userId) {
  const res  = await fetch(API + `/orgs/${currentOrgId}/invite/${userId}`, { method: 'POST', headers: H });
  const data = await res.json();
  alert(data.message || data.detail);
  if (res.ok) closeModal('invite-modal');
}

// ── Утилиты ───────────────────────────────────────────────────────────────────

function openModal(id) {
  document.getElementById(id).classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}
function closeModal(id) {
  document.getElementById(id).classList.add('hidden');
  document.body.style.overflow = '';
}
document.addEventListener('click', e => {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.add('hidden');
    document.body.style.overflow = '';
  }
});
function escHtml(s) {
  if (!s) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function logout() { localStorage.clear(); window.location.href = '/'; }

document.addEventListener('DOMContentLoaded', init);