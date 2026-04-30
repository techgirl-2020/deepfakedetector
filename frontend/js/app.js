const API_BASE_URL = window.API_BASE_URL || 'http://localhost';

const API = {
  BASE_AUTH: `${API_BASE_URL}/auth`,
  BASE_USER: `${API_BASE_URL}/user`,
};

function formatApiError(data) {
  if (!data || typeof data !== 'object') return 'Request failed';
  if (data.error) return typeof data.error === 'string' ? data.error : JSON.stringify(data.error);
  const d = data.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d)) return d.map((x) => (x.msg != null ? x.msg : String(x))).join(' ');
  if (d && typeof d === 'object') return JSON.stringify(d);
  const flat = Object.values(data).flat();
  if (flat.length) return flat.join(' ');
  return 'Request failed';
}

var typedBrand = document.getElementById('typedBrand');
const word = "Fake";
let charIndex = 0;
let deleting = false;

function typeBrand() {
  if (!typedBrand) return;

  if (!deleting) {
    typedBrand.textContent = word.slice(0, charIndex + 1);
    charIndex++;

    if (charIndex === word.length) {
      deleting = true;
      setTimeout(typeBrand, 1400);
      return;
    }

  } else {
    typedBrand.textContent = word.slice(0, charIndex - 1);
    charIndex--;

    if (charIndex === 0) {
      deleting = false;
    }
  }

  setTimeout(typeBrand, deleting ? 120 : 180);
}

typeBrand();

const api = {
  async request(url, options = {}) {
    const { includeAuth = true, headers: optionHeaders, ...fetchOptions } = options;
    const token = includeAuth ? localStorage.getItem('access') : null;
    const headers = { 'Content-Type': 'application/json', ...(optionHeaders || {}) };
    if (token) headers['Authorization'] = 'Bearer ' + token;
    if (fetchOptions.body instanceof FormData) delete headers['Content-Type'];
    const res = await fetch(url, { ...fetchOptions, headers });
    const data = await res.json().catch(() => ({}));
    if (res.status === 401) {
      // Token expired or invalid, force logout
      localStorage.removeItem('access');
      localStorage.removeItem('refresh');
      localStorage.removeItem('user');
      window.location.href = 'index.html';
      throw new Error('Session expired. Please log in again.');
    }
    if (!res.ok) {
      throw new Error(formatApiError(data));
    }
    return data;
  },
  login: (u, p) => api.request(API.BASE_AUTH + '/login/', { method: 'POST', includeAuth: false, body: JSON.stringify({ username: u, password: p }) }),
  register: (u, e, p, p2) => api.request(API.BASE_AUTH + '/register/', { method: 'POST', includeAuth: false, body: JSON.stringify({ username: u, email: e, password: p, password2: p2, role: 'user' }) }),
  logout: (r) => api.request(API.BASE_AUTH + '/logout/', { method: 'POST', body: JSON.stringify({ refresh: r }) }),
  getHistory: () => api.request(API.BASE_USER + '/history/'),
  saveHistory: (d) => api.request(API.BASE_USER + '/history/', { method: 'POST', body: JSON.stringify(d) }),
  getProfile: () => api.request(API.BASE_USER + '/me/'),
  async detect(formData) {
    const token = localStorage.getItem('access');
    const headers = {};

    if (token) headers.Authorization = 'Bearer ' + token;

    const res = await fetch(API.BASE_USER + '/detect/', {
      method: 'POST',
      headers,
      body: formData
    });

    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      throw new Error(formatApiError(data));
    }

    return data;
  },
};

function getUser() {
  try { return JSON.parse(localStorage.getItem('user') || 'null'); } catch { return null; }
}

function requireAuth() {
  if (!localStorage.getItem('access')) window.location.href = 'index.html';
}
// ===== UI HANDLERS =====

function switchTab(tab, el) {
  const tabs = document.querySelectorAll('.tab');
  const panels = document.querySelectorAll('.form-panel');

  tabs.forEach(t => {
    if (t) t.classList.remove('active');
  });
  panels.forEach(p => {
    if (p) p.classList.remove('active');
  });

  if (el) {
    el.classList.add('active');
  } else {
    const targetTab = document.querySelector(`.tab[onclick*="'${tab}'"]`);
    if (targetTab) targetTab.classList.add('active');
  }

  const target = document.getElementById(`panel-${tab}`);
  if (target) target.classList.add('active');
}

async function handleLogin() {
  const btn = document.getElementById('loginBtn');
  const errEl = document.getElementById('login-error');
  if (errEl) { errEl.classList.remove('show'); errEl.textContent = ''; }

  try {
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;

    if (!username || !password) {
      throw new Error('Please enter your username and password.');
    }

    if (btn) btn.disabled = true;
    const data = await api.login(username, password);

    // tokens are nested under data.tokens
    const tokens = data.tokens || data;
    localStorage.setItem('access', tokens.access);
    localStorage.setItem('refresh', tokens.refresh);
    if (data.user) localStorage.setItem('user', JSON.stringify(data.user));

    window.location.href = 'dashboard.html';

  } catch (err) {
    if (errEl) { errEl.textContent = err.message; errEl.classList.add('show'); }
    else alert(err.message);
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function handleRegister() {
  const btn = document.getElementById('registerBtn');
  const errEl = document.getElementById('register-error');
  const okEl = document.getElementById('register-success');
  if (errEl) { errEl.classList.remove('show'); errEl.textContent = ''; }
  if (okEl)  { okEl.classList.remove('show');  okEl.textContent = '';  }

  try {
    const username  = document.getElementById('reg-username').value.trim();
    const email     = document.getElementById('reg-email').value.trim();
    const password  = document.getElementById('reg-password').value;
    const password2 = document.getElementById('reg-password2').value;

    if (!username || !email || !password || !password2) {
      throw new Error('Please fill in all fields.');
    }
    if (password !== password2) {
      throw new Error('Passwords do not match.');
    }

    if (btn) btn.disabled = true;
    await api.register(username, email, password, password2);

    if (okEl) { okEl.textContent = 'Account created! Please sign in.'; okEl.classList.add('show'); }
    switchTab('login', document.querySelector('.tab[onclick*="login"]'));

  } catch (err) {
    if (errEl) { errEl.textContent = err.message; errEl.classList.add('show'); }
    else alert(err.message);
  } finally {
    if (btn) btn.disabled = false;
  }
}

function toggleTheme() {
  const body = document.body;
  const currentTheme = body.getAttribute('data-theme');
  const newTheme = currentTheme === 'light' ? 'dark' : 'light';
  body.setAttribute('data-theme', newTheme);
}
