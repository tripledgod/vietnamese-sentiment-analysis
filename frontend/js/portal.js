/**
 * Cổng Sinh viên / Giảng viên: đăng nhập JWT, đổi mật khẩu, phân tích cảm xúc.
 * body[data-portal] = "student" | "teacher" (API role)
 */
(function () {
  const API_URL = 'http://localhost:8000';
  function tokenKeyForPortal() {
    return portal() === 'teacher' ? 'access_token_teacher' : 'access_token_student';
  }

  function portal() {
    return document.body.getAttribute('data-portal') || 'student';
  }

  function token() {
    var k = tokenKeyForPortal();
    var t = sessionStorage.getItem(k);
    if (t) return t;
    return sessionStorage.getItem('access_token');
  }

  function setToken(t) {
    var k = tokenKeyForPortal();
    if (t) {
      sessionStorage.setItem(k, t);
      sessionStorage.removeItem(k === 'access_token_teacher' ? 'access_token_student' : 'access_token_teacher');
      sessionStorage.removeItem('access_token');
    } else {
      sessionStorage.removeItem(k);
    }
  }

  function authHeaders(json = true) {
    const h = {};
    if (json) h['Content-Type'] = 'application/json';
    const t = token();
    if (t) h['Authorization'] = 'Bearer ' + t;
    return h;
  }

  async function apiLogin(username, password) {
    const res = await fetch(API_URL + '/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, portal: portal() }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || 'Đăng nhập thất bại');
    return data;
  }

  async function apiMe() {
    const res = await fetch(API_URL + '/auth/me', { headers: authHeaders(false) });
    if (res.status === 401) return null;
    if (!res.ok) throw new Error('Không tải được thông tin tài khoản');
    return res.json();
  }

  async function apiChangePassword(oldPassword, newPassword) {
    const res = await fetch(API_URL + '/auth/change-password', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || 'Đổi mật khẩu thất bại');
    return data;
  }

  async function apiPredict(text) {
    const res = await fetch(API_URL + '/predict', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ text }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || 'HTTP ' + res.status);
    return data;
  }

  /** Sinh viên: PhoBERT + ghi bảng feedbacks (user_id, content, label, confidence, created_at). */
  async function apiSubmitFeedback(text) {
    const res = await fetch(API_URL + '/feedbacks', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ content: text }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || 'HTTP ' + res.status);
    return data;
  }

  function renderItem(item, idx) {
    let probsHtml = '';
    for (const [label, p] of Object.entries(item.probabilities || {})) {
      const pct = (p * 100).toFixed(1);
      probsHtml +=
        '<div class="prob-row">' +
        '<span class="prob-label">' +
        label +
        '</span>' +
        '<div class="prob-bar"><div class="prob-fill ' +
        label +
        '" style="width:' +
        pct +
        '%"></div></div>' +
        '<span class="prob-pct">' +
        pct +
        '%</span>' +
        '</div>';
    }
    return (
      '<div class="sentence-block">' +
      (idx >= 0
        ? '<div class="sentence-text">"' +
          String(item.text || '').replace(/"/g, '&quot;') +
          '"</div>'
        : '') +
      '<span class="sentiment-badge ' +
      item.sentiment +
      '">' +
      item.sentiment +
      '</span>' +
      '<div class="probs">' +
      probsHtml +
      '</div>' +
      '</div>'
    );
  }

  function show(el, on) {
    el.classList.toggle('hidden', !on);
  }

  document.addEventListener('DOMContentLoaded', function () {
    const loginSection = document.getElementById('loginSection');
    const appSection = document.getElementById('appSection');
    const loginForm = document.getElementById('loginForm');
    const loginError = document.getElementById('loginError');
    const userLabel = document.getElementById('userLabel');
    const mustChangeBanner = document.getElementById('mustChangeBanner');
    const changePwdForm = document.getElementById('changePwdForm');
    const pwdMsg = document.getElementById('pwdMsg');
    const input = document.getElementById('input');
    const btn = document.getElementById('btn');
    const result = document.getElementById('result');
    const sentencesEl = document.getElementById('sentences');
    const errEl = document.getElementById('error');
    const btnLogout = document.getElementById('btnLogout');

    let currentMustChange = false;

    function showLogin() {
      setToken(null);
      show(loginSection, true);
      show(appSection, false);
    }

    function showApp(profile) {
      show(loginSection, false);
      show(appSection, true);
      userLabel.textContent =
        (profile.full_name ? profile.full_name + ' · ' : '') + profile.username + ' · ' + profile.role;
      var isTeacher = profile.role === 'teacher';
      currentMustChange = !isTeacher && !!profile.must_change_password;
      show(mustChangeBanner, currentMustChange);
    }

    async function refreshSession() {
      const t = token();
      if (!t) {
        showLogin();
        return;
      }
      try {
        const profile = await apiMe();
        if (!profile) {
          showLogin();
          return;
        }
        if (profile.role !== portal()) {
          loginError.textContent = 'Phiên không khớp cổng này. Vui lòng đăng nhập lại.';
          setToken(null);
          showLogin();
          return;
        }
        showApp(profile);
      } catch (_) {
        showLogin();
      }
    }

    loginForm.addEventListener('submit', async function (e) {
      e.preventDefault();
      loginError.textContent = '';
      const u = document.getElementById('username').value.trim();
      const p = document.getElementById('password').value;
      if (!u || !p) return;
      try {
        const data = await apiLogin(u, p);
        setToken(data.access_token);
        await refreshSession();
      } catch (err) {
        loginError.textContent = err.message || String(err);
      }
    });

    btnLogout.addEventListener('click', function () {
      showLogin();
      document.getElementById('username').value = '';
      document.getElementById('password').value = '';
    });

    changePwdForm.addEventListener('submit', async function (e) {
      e.preventDefault();
      pwdMsg.textContent = '';
      const oldP = document.getElementById('oldPwd').value;
      const newP = document.getElementById('newPwd').value;
      try {
        await apiChangePassword(oldP, newP);
        pwdMsg.textContent = 'Đã đổi mật khẩu. Bạn có thể tiếp tục phân tích.';
        document.getElementById('oldPwd').value = '';
        document.getElementById('newPwd').value = '';
        await refreshSession();
      } catch (err) {
        pwdMsg.textContent = err.message || String(err);
      }
    });

    btn.addEventListener('click', async function () {
      const text = input.value.trim();
      if (!text) return;
      if (portal() === 'student' && currentMustChange) {
        errEl.textContent = 'Vui lòng đổi mật khẩu (khối phía trên) trước khi gửi phản hồi.';
        return;
      }
      btn.disabled = true;
      errEl.textContent = '';
      result.classList.remove('show');
      try {
        const isStudent = portal() === 'student';
        const data = isStudent ? await apiSubmitFeedback(text) : await apiPredict(text);
        const items = data.sentences || (data.sentiment ? [data] : []);
        if (!items.length || !items[0].sentiment) {
          errEl.textContent = 'API trả về dữ liệu không đúng định dạng.';
          return;
        }
        let html = '';
        if (isStudent && data.id != null) {
          html +=
            '<p class="save-ok">Đã lưu khảo sát vào SQLite · Mã bản ghi #' +
            data.id +
            ' · Nhãn (đoạn đầu): <strong>' +
            (data.label || '') +
            '</strong> · Độ tin cậy: ' +
            ((data.confidence != null ? data.confidence : 0) * 100).toFixed(1) +
            '%</p>';
        }
        items.forEach(function (item, idx) {
          html += renderItem(item, items.length > 1 ? idx : -1);
        });
        sentencesEl.innerHTML = html;
        result.classList.add('show');
      } catch (e) {
        errEl.textContent = 'Lỗi: ' + (e.message || 'Không kết nối được API');
      } finally {
        btn.disabled = false;
      }
    });

    refreshSession();
  });
})();
