/**
 * Dashboard Giảng viên — PhoBERT / thống kê / quản trị.
 */
(function () {
  const API_URL = 'http://localhost:8000';
  const TOKEN_KEY = 'access_token_teacher';
  const OTHER_PORTAL_TOKEN_KEY = 'access_token_student';
  const LEGACY_TOKEN_KEY = 'access_token';
  const ADMIN_KEY_STORAGE = 'admin_x_key';

  const COLORS = {
    positive: '#34d399',
    negative: '#fb7185',
    neutral: '#fbbf24',
    other: '#78716c',
  };

  let chartPie = null;
  let chartBar = null;
  let tableOffset = 0;
  const PAGE_SIZE = 25;
  let searchDebounce = null;

  function getToken() {
    return sessionStorage.getItem(TOKEN_KEY);
  }

  function setToken(t) {
    if (t) {
      sessionStorage.setItem(TOKEN_KEY, t);
      sessionStorage.removeItem(OTHER_PORTAL_TOKEN_KEY);
      sessionStorage.removeItem(LEGACY_TOKEN_KEY);
    } else {
      sessionStorage.removeItem(TOKEN_KEY);
    }
  }

  async function migrateLegacyTeacherToken() {
    if (sessionStorage.getItem(TOKEN_KEY)) return;
    var leg = sessionStorage.getItem(LEGACY_TOKEN_KEY);
    if (!leg) return;
    try {
      var res = await fetch(API_URL + '/users/me', {
        headers: { Authorization: 'Bearer ' + leg },
      });
      if (!res.ok) {
        sessionStorage.removeItem(LEGACY_TOKEN_KEY);
        return;
      }
      var p = await res.json();
      if (p && p.role === 'teacher') {
        setToken(leg);
      } else {
        sessionStorage.removeItem(LEGACY_TOKEN_KEY);
      }
    } catch (_) {
      sessionStorage.removeItem(LEGACY_TOKEN_KEY);
    }
  }

  function authHeaders(json) {
    const h = {};
    if (json) h['Content-Type'] = 'application/json';
    const t = getToken();
    if (t) h['Authorization'] = 'Bearer ' + t;
    return h;
  }

  function getAdminKey() {
    return sessionStorage.getItem(ADMIN_KEY_STORAGE) || '';
  }

  function setAdminKey(k) {
    if (k) sessionStorage.setItem(ADMIN_KEY_STORAGE, k);
    else sessionStorage.removeItem(ADMIN_KEY_STORAGE);
  }

  /**
   * Khóa đã lưu hoặc đang gõ trong ô (fallback).
   * Tránh lỗi: đã bấm Lưu nhưng sessionStorage trống do khác origin (vd. 127.0.0.1 vs localhost),
   * hoặc chưa bấm Lưu nhưng ô đã có giá trị.
   */
  function getEffectiveAdminKey() {
    const fromStore = getAdminKey().trim();
    if (fromStore) return fromStore;
    const el = document.getElementById('adminKeyInput');
    const fromInput = el && el.value ? String(el.value).trim() : '';
    if (fromInput) {
      setAdminKey(fromInput);
      return fromInput;
    }
    return '';
  }

  function esc(s) {
    const d = document.createElement('div');
    d.textContent = s == null ? '' : String(s);
    return d.innerHTML;
  }

  function showLogin(on) {
    document.getElementById('loginShell').classList.toggle('hidden', !on);
    document.getElementById('appShell').classList.toggle('hidden', on);
  }

  function setLoginLoading(loading) {
    const btn = document.getElementById('btnLogin');
    if (!btn) return;
    btn.disabled = loading;
    btn.classList.toggle('loading', loading);
    document.getElementById('loginBtnText').textContent = loading ? 'Đang đăng nhập…' : 'Đăng nhập';
  }

  function showPage(id) {
    ['page-dashboard', 'page-feedback', 'page-survey-wf', 'page-admin'].forEach(function (pid) {
      document.getElementById(pid).classList.toggle('hidden', pid !== id);
    });
    document.querySelectorAll('.nav-link').forEach(function (a) {
      a.classList.toggle('active', a.getAttribute('data-page') === id);
    });
    if (id === 'page-dashboard') loadDashboard();
    if (id === 'page-feedback') {
      loadClassOptions();
      loadAlerts();
      loadTable();
    }
    if (id === 'page-survey-wf') loadSurveyWorkflowPage();
  }

  async function loadSurveyWorkflowPage() {
    const msg = document.getElementById('surveyWfMsg');
    const subHost = document.getElementById('surveyWfSubjects');
    if (msg) msg.textContent = '';
    if (subHost) subHost.innerHTML = '<p class="muted small">Đang tải…</p>';
    try {
      const [classes, semesters] = await Promise.all([
        apiTeacher('/teacher/survey/classes'),
        apiTeacher('/teacher/survey/semesters'),
      ]);
      const selC = document.getElementById('selectSurveyClass');
      const selS = document.getElementById('selectSurveySemester');
      if (!selC || !selS) return;
      selC.innerHTML = '<option value="">— Chọn lớp —</option>';
      classes.forEach(function (c) {
        const o = document.createElement('option');
        o.value = String(c.id);
        o.textContent = c.class_name + (c.department ? ' · ' + c.department : '');
        selC.appendChild(o);
      });
      selS.innerHTML = '<option value="">— Chọn kỳ học —</option>';
      semesters.forEach(function (s) {
        const o = document.createElement('option');
        o.value = String(s.id);
        o.textContent = s.name;
        selS.appendChild(o);
      });
      if (subHost) subHost.innerHTML = '<p class="muted small">Chọn lớp và kỳ để hiện danh sách môn.</p>';
    } catch (e) {
      if (msg) {
        msg.className = 'err';
        msg.textContent = e.message || String(e);
      }
      if (subHost) subHost.innerHTML = '';
    }
  }

  async function loadSurveySubjectCheckboxes() {
    const msg = document.getElementById('surveyWfMsg');
    const subHost = document.getElementById('surveyWfSubjects');
    const selC = document.getElementById('selectSurveyClass');
    const selS = document.getElementById('selectSurveySemester');
    if (!selC || !selS || !subHost) return;
    const cid = selC.value;
    const sid = selS.value;
    if (!cid || !sid) {
      subHost.innerHTML = '<p class="muted small">Chọn lớp và kỳ để hiện danh sách môn.</p>';
      return;
    }
    if (msg) msg.textContent = '';
    subHost.innerHTML = '<p class="muted small">Đang tải môn…</p>';
    try {
      const rows = await apiTeacher(
        '/teacher/survey/configs?class_id=' + encodeURIComponent(cid) + '&semester_id=' + encodeURIComponent(sid)
      );
      subHost.innerHTML = '';
      if (!rows.length) {
        subHost.innerHTML = '<p class="muted small">Kỳ này chưa gắn môn nào trong hệ thống.</p>';
        return;
      }
      rows.forEach(function (r) {
        const id = 'subjChk_' + r.subject_id;
        const row = document.createElement('label');
        row.className = 'survey-wf-row';
        row.innerHTML =
          '<input type="checkbox" id="' +
          id +
          '" data-subject-id="' +
          r.subject_id +
          '" ' +
          (r.is_active ? 'checked' : '') +
          ' />' +
          '<span>' +
          esc(r.subject_name) +
          ' <span class="muted">(' +
          esc(r.subject_code) +
          ')</span></span>';
        subHost.appendChild(row);
      });
    } catch (e) {
      subHost.innerHTML = '';
      if (msg) {
        msg.className = 'err';
        msg.textContent = e.message || String(e);
      }
    }
  }

  async function submitSurveyActivation() {
    const msg = document.getElementById('surveyWfMsg');
    const selC = document.getElementById('selectSurveyClass');
    const selS = document.getElementById('selectSurveySemester');
    const subHost = document.getElementById('surveyWfSubjects');
    if (msg) {
      msg.textContent = '';
      msg.className = '';
    }
    const cid = selC && selC.value;
    const semid = selS && selS.value;
    if (!cid || !semid) {
      if (msg) {
        msg.className = 'err';
        msg.textContent = 'Chọn lớp và kỳ học.';
      }
      return;
    }
    const checks = subHost ? subHost.querySelectorAll('input[type="checkbox"][data-subject-id]') : [];
    const activeIds = [];
    checks.forEach(function (ch) {
      if (ch.checked) activeIds.push(parseInt(ch.getAttribute('data-subject-id'), 10));
    });
    try {
      await apiTeacher('/teacher/survey/activate', {
        method: 'POST',
        headers: authHeaders(true),
        body: JSON.stringify({
          class_id: parseInt(cid, 10),
          semester_id: parseInt(semid, 10),
          active_subject_ids: activeIds,
        }),
      });
      if (msg) {
        msg.className = 'ok';
        msg.textContent =
          'Đã cập nhật. Sinh viên lớp đã chọn chỉ thấy nút khảo sát cho các môn đã tích.';
      }
    } catch (e) {
      if (msg) {
        msg.className = 'err';
        msg.textContent = e.message || String(e);
      }
    }
  }

  async function apiTeacher(path, opts) {
    const res = await fetch(API_URL + path, Object.assign({ headers: authHeaders(false) }, opts));
    const data = await res.json().catch(function () {
      return {};
    });
    if (res.status === 401) {
      setToken(null);
      showLogin(true);
      throw new Error('Phiên hết hạn. Vui lòng đăng nhập lại.');
    }
    if (!res.ok) throw new Error(data.detail || res.statusText);
    return data;
  }

  function destroyCharts() {
    if (chartPie) {
      chartPie.destroy();
      chartPie = null;
    }
    if (chartBar) {
      chartBar.destroy();
      chartBar = null;
    }
  }

  async function loadDashboard() {
    destroyCharts();
    try {
      const overview = await apiTeacher('/admin/stats/overview');
      const classes = await apiTeacher('/admin/stats/classes');

      document.getElementById('statStudents').textContent = overview.total_students_participated;
      document.getElementById('statFeedbacks').textContent = overview.total_feedbacks;
      document.getElementById('statPositive').textContent =
        overview.positive_rate_percent.toFixed(1) + '%';

      const dist = overview.sentiment_distribution || [];
      const pieLabels = [];
      const pieData = [];
      const pieColors = [];
      dist.forEach(function (d) {
        pieLabels.push(d.label_vi);
        pieData.push(d.count);
        if (d.label === 'positive') pieColors.push(COLORS.positive);
        else if (d.label === 'negative') pieColors.push(COLORS.negative);
        else if (d.label === 'neutral') pieColors.push(COLORS.neutral);
        else pieColors.push(COLORS.other);
      });

      const ctxPie = document.getElementById('chartPie');
      if (typeof Chart !== 'undefined' && ctxPie) {
        chartPie = new Chart(ctxPie, {
          type: 'doughnut',
          data: {
            labels: pieLabels,
            datasets: [{ data: pieData, backgroundColor: pieColors, borderWidth: 0 }],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { position: 'bottom', labels: { color: '#a8a29e', padding: 14 } },
            },
          },
        });
      }

      const items = classes.items || [];
      const barLabels = items.map(function (i) {
        return i.class_name + (i.department ? ' · ' + i.department : '');
      });
      const barPos = items.map(function (i) {
        return i.positive;
      });

      const ctxBar = document.getElementById('chartBar');
      if (typeof Chart !== 'undefined' && ctxBar) {
        chartBar = new Chart(ctxBar, {
          type: 'bar',
          data: {
            labels: barLabels.length ? barLabels : ['(Chưa có dữ liệu)'],
            datasets: [
              {
                label: 'Số phản hồi tích cực',
                data: barLabels.length ? barPos : [0],
                backgroundColor: COLORS.positive,
                borderRadius: 6,
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              x: { ticks: { color: '#a8a29e', maxRotation: 45 }, grid: { color: '#44403c' } },
              y: {
                beginAtZero: true,
                ticks: { color: '#a8a29e', stepSize: 1 },
                grid: { color: '#44403c' },
              },
            },
            plugins: { legend: { display: false } },
          },
        });
      }
    } catch (e) {
      document.getElementById('dashError').textContent = e.message || String(e);
    }
  }

  async function loadClassOptions() {
    const sel = document.getElementById('filterClass');
    if (!sel || sel.dataset.loaded === '1') return;
    try {
      const data = await apiTeacher('/admin/meta/classes');
      sel.innerHTML = '<option value="">Tất cả lớp</option>';
      (data.items || []).forEach(function (c) {
        const o = document.createElement('option');
        o.value = String(c.id);
        o.textContent = c.class_name + (c.department ? ' — ' + c.department : '');
        sel.appendChild(o);
      });
      sel.dataset.loaded = '1';
    } catch (_) {
      /* ignore */
    }
  }

  function badgeClass(label) {
    if (label === 'positive') return 'badge-pos';
    if (label === 'negative') return 'badge-neg';
    return 'badge-neu';
  }

  async function loadAlerts() {
    const box = document.getElementById('alertCards');
    const err = document.getElementById('feedbackError');
    err.textContent = '';
    box.innerHTML = '';
    try {
      const data = await apiTeacher('/admin/feedbacks/alerts?limit=15');
      const items = data.items || [];
      if (!items.length) {
        box.innerHTML = '<p class="page-desc" style="margin:0">Không có phản hồi tiêu cực nổi bật.</p>';
        return;
      }
      items.forEach(function (a) {
        const div = document.createElement('div');
        div.className = 'alert-card';
        div.innerHTML =
          '<div class="meta">' +
          esc(a.student_full_name || a.username) +
          ' · ' +
          esc(a.class_name || '—') +
          ' · Tin cậy ' +
          (a.confidence * 100).toFixed(1) +
          '% · ' +
          esc(a.created_at) +
          '</div><div class="txt">' +
          esc(a.content) +
          '</div>';
        box.appendChild(div);
      });
    } catch (e) {
      err.textContent = e.message || String(e);
    }
  }

  async function loadTable() {
    const tbody = document.getElementById('tableBody');
    const err = document.getElementById('feedbackError');
    const pagerInfo = document.getElementById('pagerInfo');
    err.textContent = '';
    tbody.innerHTML = '<tr><td colspan="6" style="color:#a8a29e">Đang tải…</td></tr>';

    const classId = document.getElementById('filterClass').value;
    const label = document.getElementById('filterLabel').value;
    const q = document.getElementById('filterSearch').value.trim();

    let qs =
      '/admin/feedbacks/all?limit=' +
      PAGE_SIZE +
      '&offset=' +
      tableOffset;
    if (classId) qs += '&class_id=' + encodeURIComponent(classId);
    if (label) qs += '&label=' + encodeURIComponent(label);
    if (q) qs += '&q=' + encodeURIComponent(q);

    try {
      const data = await apiTeacher(qs);
      const items = data.items || [];
      const total = data.total || 0;
      pagerInfo.textContent =
        'Hiển thị ' +
        (items.length ? tableOffset + 1 : 0) +
        '–' +
        (tableOffset + items.length) +
        ' / ' +
        total;

      tbody.innerHTML = '';
      if (!items.length) {
        tbody.innerHTML = '<tr><td colspan="6" style="color:#a8a29e">Không có bản ghi.</td></tr>';
      } else {
        items.forEach(function (r) {
          const tr = document.createElement('tr');
          tr.innerHTML =
            '<td>' +
            esc(r.created_at) +
            '</td><td class="cell-content">' +
            esc(r.content) +
            '</td><td><span class="badge ' +
            badgeClass(r.label) +
            '">' +
            esc(r.label_vi) +
            '</span></td><td>' +
            (r.confidence * 100).toFixed(1) +
            '%</td><td>' +
            esc(r.student_full_name || r.username) +
            '</td><td>' +
            esc(r.class_name || '—') +
            '</td>';
          tbody.appendChild(tr);
        });
      }

      document.getElementById('btnPrev').disabled = tableOffset <= 0;
      document.getElementById('btnNext').disabled = tableOffset + items.length >= total;
    } catch (e) {
      tbody.innerHTML = '';
      err.textContent = e.message || String(e);
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.getElementById('loginForm').addEventListener('submit', async function (e) {
      e.preventDefault();
      document.getElementById('loginErr').textContent = '';
      const u = document.getElementById('username').value.trim();
      const p = document.getElementById('password').value;
      if (!u || !p) return;
      setLoginLoading(true);
      try {
        const res = await fetch(API_URL + '/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: u, password: p, portal: 'teacher' }),
        });
        const data = await res.json().catch(function () {
          return {};
        });
        if (!res.ok) throw new Error(data.detail || 'Đăng nhập thất bại');
        setToken(data.access_token);
        showLogin(false);
        document.getElementById('sidebarUser').textContent = data.full_name || data.username;
        showPage('page-dashboard');
      } catch (err) {
        document.getElementById('loginErr').textContent = err.message || String(err);
      } finally {
        setLoginLoading(false);
      }
    });

    document.getElementById('btnLogout').addEventListener('click', function () {
      setToken(null);
      document.getElementById('username').value = '';
      document.getElementById('password').value = '';
      destroyCharts();
      showLogin(true);
    });

    document.querySelectorAll('.nav-link').forEach(function (el) {
      el.addEventListener('click', function () {
        showPage(el.getAttribute('data-page'));
      });
    });

    var selSurveyClass = document.getElementById('selectSurveyClass');
    var selSurveySem = document.getElementById('selectSurveySemester');
    if (selSurveyClass) selSurveyClass.addEventListener('change', loadSurveySubjectCheckboxes);
    if (selSurveySem) selSurveySem.addEventListener('change', loadSurveySubjectCheckboxes);
    var btnAct = document.getElementById('btnSurveyActivate');
    if (btnAct) btnAct.addEventListener('click', submitSurveyActivation);

    document.getElementById('btnApplyFilter').addEventListener('click', function () {
      tableOffset = 0;
      loadTable();
    });

    document.getElementById('filterSearch').addEventListener('input', function () {
      clearTimeout(searchDebounce);
      searchDebounce = setTimeout(function () {
        tableOffset = 0;
        loadTable();
      }, 400);
    });

    document.getElementById('btnPrev').addEventListener('click', function () {
      tableOffset = Math.max(0, tableOffset - PAGE_SIZE);
      loadTable();
    });
    document.getElementById('btnNext').addEventListener('click', function () {
      tableOffset += PAGE_SIZE;
      loadTable();
    });

    const savedAdmin = getAdminKey();
    if (savedAdmin) document.getElementById('adminKeyInput').value = savedAdmin;

    document.getElementById('btnSaveAdminKey').addEventListener('click', function () {
      const k = document.getElementById('adminKeyInput').value.trim();
      setAdminKey(k);
      const msgEl = document.getElementById('adminKeyMsg');
      if (k) {
        msgEl.textContent = 'Đã lưu khóa trong phiên trình duyệt (session).';
        msgEl.className = 'ok';
      } else {
        msgEl.textContent = 'Đã xóa khóa.';
        msgEl.className = '';
      }
    });

    document.getElementById('btnPickExcel').addEventListener('click', function () {
      document.getElementById('excelFile').click();
    });

    document.getElementById('excelFile').addEventListener('change', async function () {
      const f = this.files && this.files[0];
      const msg = document.getElementById('importMsg');
      msg.textContent = '';
      if (!f) return;
      const key = getEffectiveAdminKey();
      if (!key) {
        msg.textContent = 'Nhập và lưu X-Admin-Key trước.';
        msg.className = 'err';
        return;
      }
      const fd = new FormData();
      fd.append('file', f);
      try {
        const res = await fetch(API_URL + '/admin/users/import-excel', {
          method: 'POST',
          headers: { 'X-Admin-Key': key },
          body: fd,
        });
        const data = await res.json().catch(function () {
          return {};
        });
        if (!res.ok) {
          if (res.status === 404) {
            throw new Error(
              'Không tìm thấy API import (404). Khởi động lại backend; kiểm tra ' +
                API_URL +
                '/docs có endpoint POST /admin/users/import-excel.'
            );
          }
          throw new Error(data.detail || 'Import thất bại');
        }
        msg.className = 'ok';
        msg.textContent =
          'Xong: tạo mới ' + (data.created || 0) + ', cập nhật ' + (data.updated || 0) + '.';
        if (data.errors && data.errors.length) {
          msg.textContent += ' Cảnh báo: ' + data.errors.slice(0, 3).join('; ');
        }
      } catch (e) {
        msg.className = 'err';
        msg.textContent = e.message || String(e);
      }
      this.value = '';
    });

    document.getElementById('btnPickMasterExcel').addEventListener('click', function () {
      document.getElementById('masterExcelFile').click();
    });

    document.getElementById('masterExcelFile').addEventListener('change', async function () {
      const f = this.files && this.files[0];
      const msg = document.getElementById('importMasterMsg');
      msg.textContent = '';
      if (!f) return;
      const key = getEffectiveAdminKey();
      if (!key) {
        msg.textContent = 'Nhập và lưu X-Admin-Key trước.';
        msg.className = 'err';
        return;
      }
      const fd = new FormData();
      fd.append('file', f);
      try {
        const res = await fetch(API_URL + '/admin/import-master-excel', {
          method: 'POST',
          headers: { 'X-Admin-Key': key },
          body: fd,
        });
        const data = await res.json().catch(function () {
          return {};
        });
        if (!res.ok) {
          if (res.status === 404) {
            throw new Error(
              'Không tìm thấy API import (404). Tắt backend và chạy lại (python run.py). Kiểm tra: mở trình duyệt ' +
                API_URL +
                '/admin/import-master-excel — phải thấy JSON hướng dẫn, không phải 404.'
            );
          }
          throw new Error(data.detail || 'Import master thất bại');
        }
        msg.className = data.ok ? 'ok' : 'err';
        msg.textContent =
          'Lớp mới ' +
          (data.classes_new || 0) +
          ', đã có ' +
          (data.classes_existing || 0) +
          ' | Môn tạo ' +
          (data.subjects_created || 0) +
          ', cập nhật ' +
          (data.subjects_updated || 0) +
          ' | Liên kết kỳ+môn +' +
          (data.semester_links_added || 0) +
          ' | SV tạo ' +
          (data.users_created || 0) +
          ', cập nhật ' +
          (data.users_updated || 0) +
          '.';
        if (data.errors && data.errors.length) {
          msg.textContent += ' Lỗi/cảnh báo: ' + data.errors.slice(0, 5).join('; ');
        }
        document.getElementById('filterClass').dataset.loaded = '';
        var sc = document.getElementById('selectSurveyClass');
        if (sc) sc.dataset.loaded = '';
      } catch (e) {
        msg.className = 'err';
        msg.textContent = e.message || String(e);
      }
      this.value = '';
    });

    document.getElementById('formCreateClass').addEventListener('submit', async function (e) {
      e.preventDefault();
      const msg = document.getElementById('classMsg');
      msg.textContent = '';
      const key = getEffectiveAdminKey();
      if (!key) {
        msg.textContent = 'Nhập và lưu X-Admin-Key trước.';
        msg.className = 'err';
        return;
      }
      const class_name = document.getElementById('newClassName').value.trim();
      const department = document.getElementById('newClassDept').value.trim();
      if (!class_name) return;
      try {
        const res = await fetch(API_URL + '/admin/classes', {
          method: 'POST',
          headers: Object.assign({ 'X-Admin-Key': key }, authHeaders(true)),
          body: JSON.stringify({ class_name: class_name, department: department }),
        });
        const data = await res.json().catch(function () {
          return {};
        });
        if (!res.ok) throw new Error(data.detail || 'Lỗi tạo lớp');
        msg.className = 'ok';
        msg.textContent = 'Đã tạo / khớp lớp ID ' + data.id + '.';
        document.getElementById('newClassName').value = '';
        document.getElementById('newClassDept').value = '';
        document.getElementById('filterClass').dataset.loaded = '';
      } catch (e) {
        msg.className = 'err';
        msg.textContent = e.message || String(e);
      }
    });

    migrateLegacyTeacherToken().then(function () {
      if (getToken()) {
        showLogin(false);
        apiTeacher('/users/me')
          .then(function (me) {
            document.getElementById('sidebarUser').textContent = me.full_name || me.username;
            showPage('page-dashboard');
          })
          .catch(function () {
            showLogin(true);
          });
      } else {
        showLogin(true);
      }
    });
  });
})();
