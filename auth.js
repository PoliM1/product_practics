// static/js/auth.js
// Логика страницы входа и регистрации

const API = '';  // Пустая строка = запросы идут на тот же сервер

// Если пользователь уже залогинен — сразу на дашборд
if (localStorage.getItem('token')) {
  window.location.href = '/dashboard';
}

// ── Переключение вкладок ─────────────────────────────────────────────────────

function switchTab(tab) {
  // Скрываем все вкладки
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
  hideMessage();

  // Показываем нужную
  const tabEl = document.getElementById(tab + '-tab');
  if (tabEl) tabEl.classList.add('active');

  // Подсвечиваем кнопку (только для login/register)
  if (tab === 'login') document.querySelectorAll('.tab-btn')[0]?.classList.add('active');
  if (tab === 'register') document.querySelectorAll('.tab-btn')[1]?.classList.add('active');
}

// ── Сообщения ────────────────────────────────────────────────────────────────

function showMessage(text, type = 'error') {
  const el = document.getElementById('auth-message');
  el.textContent = text;
  el.className = 'message ' + type;
}

function hideMessage() {
  const el = document.getElementById('auth-message');
  if (el) el.className = 'message hidden';
}

// ── Вход ─────────────────────────────────────────────────────────────────────

async function login() {
  const email = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value;

  if (!email || !password) {
    showMessage('Заполните все поля');
    return;
  }

  try {
    const res = await fetch(API + '/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });

    const data = await res.json();

    if (res.ok) {
      // Сохраняем токен в localStorage
      // localStorage сохраняется между сессиями браузера
      localStorage.setItem('token', data.access_token);
      localStorage.setItem('userId', data.user_id);
      localStorage.setItem('userName', data.full_name);
      // Переходим на главную
      window.location.href = '/dashboard';
    } else {
      showMessage(data.detail || 'Неверный email или пароль');
    }
  } catch (err) {
    showMessage('Сервер недоступен. Попробуйте позже.');
    console.error(err);
  }
}

// ── Регистрация ──────────────────────────────────────────────────────────────

async function register() {
  const fields = {
    full_name:  document.getElementById('reg-name').value.trim(),
    email:      document.getElementById('reg-email').value.trim(),
    phone:      document.getElementById('reg-phone').value.trim(),
    birth_date: document.getElementById('reg-birth').value,
    position:   document.getElementById('reg-position').value.trim(),
    role:       document.getElementById('reg-role').value,
    password:   document.getElementById('reg-password').value,
  };

  // Клиентская валидация
  for (const [key, val] of Object.entries(fields)) {
    if (!val) {
      showMessage('Заполните все обязательные поля');
      return;
    }
  }

  if (fields.password.length < 8) {
    showMessage('Пароль должен быть минимум 8 символов');
    return;
  }

  try {
    const res = await fetch(API + '/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(fields),
    });

    const data = await res.json();

    if (res.ok) {
      localStorage.setItem('token', data.access_token);
      localStorage.setItem('userId', data.user_id);
      localStorage.setItem('userName', data.full_name);
      window.location.href = '/dashboard';
    } else {
      // Pydantic возвращает detail в разных форматах
      if (Array.isArray(data.detail)) {
        showMessage(data.detail.map(e => e.msg).join(', '));
      } else {
        showMessage(data.detail || 'Ошибка регистрации');
      }
    }
  } catch (err) {
    showMessage('Сервер недоступен. Попробуйте позже.');
    console.error(err);
  }
}

// ── Восстановление пароля ────────────────────────────────────────────────────

async function forgotPassword() {
  const contact = document.getElementById('forgot-contact').value.trim();

  if (!contact) {
    showMessage('Введите email или номер телефона');
    return;
  }

  try {
    const res = await fetch(API + '/auth/forgot-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ contact }),
    });

    const data = await res.json();
    showMessage(data.message, 'success');
  } catch (err) {
    showMessage('Ошибка. Попробуйте позже.');
  }
}

// ── Enter для быстрой отправки ───────────────────────────────────────────────

document.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') {
    const activeTab = document.querySelector('.tab-content.active')?.id;
    if (activeTab === 'login-tab') login();
    if (activeTab === 'register-tab') register();
    if (activeTab === 'forgot-tab') forgotPassword();
  }
});