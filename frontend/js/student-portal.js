/**
 * Cổng Sinh viên: đăng nhập, khảo sát (POST /feedbacks), lịch sử (GET /feedbacks/my-history).
 */
(function () {
  const API_URL = 'http://localhost:8000';
  /** Tách khóa với cổng GV — tránh dùng nhầm JWT teacher khi cùng origin (Live Server). */
  const TOKEN_KEY = 'access_token_student';
  const OTHER_PORTAL_TOKEN_KEY = 'access_token_teacher';
  const LEGACY_TOKEN_KEY = 'access_token';
  const SURVEY_FORM_NAME = 'Khảo sát cảm xúc phản hồi học tập';
  const DEFAULT_SURVEY_OFFERINGS_EMPTY =
    'Hiện chưa có môn nào được mở khảo sát. Vui lòng liên hệ giảng viên.';
  const SURVEY_QUESTIONS = [
    'Bạn đánh giá thế nào về phương pháp giảng dạy của giảng viên?',
    'Cơ sở vật chất phục vụ môn học này ra sao?',
    'Nội dung môn học có đáp ứng kỳ vọng của bạn không?',
    'Bạn có góp ý thêm nào khác không? (Nếu không, ghi "Không")',
  ];
  const LABEL_VI = {
    positive: 'Tích cực',
    negative: 'Tiêu cực',
    neutral: 'Trung tính',
  };

  function token() {
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

  function normalizeLoginUsername(raw) {
    try {
      return String(raw || '')
        .normalize('NFKC')
        .trim();
    } catch (_) {
      return String(raw || '').trim();
    }
  }

  async function migrateLegacyStudentToken() {
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
      if (p && p.role === 'student') {
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
    const t = token();
    if (t) h['Authorization'] = 'Bearer ' + t;
    return h;
  }

  function esc(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  function formatDate(iso) {
    if (!iso) return '—';
    try {
      const d = new Date(String(iso).replace(' ', 'T'));
      if (isNaN(d.getTime())) return String(iso);
      return d.toLocaleString('vi-VN', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch (_) {
      return String(iso);
    }
  }

  function labelClass(st) {
    if (st === 'positive' || st === 'negative' || st === 'neutral') return st;
    return 'neutral';
  }

  function labelVi(st) {
    return LABEL_VI[st] || st;
  }

  document.addEventListener('DOMContentLoaded', function () {
    const loginSection = document.getElementById('loginSection');
    const appSection = document.getElementById('appSection');
    const loginForm = document.getElementById('loginForm');
    const loginError = document.getElementById('loginError');
    const loginBtn = document.getElementById('btnLogin');
    const greetingEl = document.getElementById('greeting');
    const metaEl = document.getElementById('metaLine');
    const mustChangeBanner = document.getElementById('mustChangeBanner');
    const changePwdForm = document.getElementById('changePwdForm');
    const pwdMsg = document.getElementById('pwdMsg');
    const btnLogout = document.getElementById('btnLogout');
    const surveyPage = document.getElementById('surveyPage');
    const historyPage = document.getElementById('historyPage');
    const navTabs = document.querySelectorAll('.nav-tab');
    const surveyInput = document.getElementById('surveyInput');
    const btnSubmit = document.getElementById('btnSubmitSurvey');
    const thankYou = document.getElementById('thankYou');
    const surveyError = document.getElementById('surveyError');
    const historyAccordion = document.getElementById('historyAccordion');
    const historyError = document.getElementById('historyError');
    const historyEmpty = document.getElementById('historyEmpty');
    const surveyOfferingsList = document.getElementById('surveyOfferingsList');
    const surveyOfferingsEmpty = document.getElementById('surveyOfferingsEmpty');
    const surveyModalBackdrop = document.getElementById('surveyModalBackdrop');
    const surveyModalMeta = document.getElementById('surveyModalMeta');
    const surveyModalFields = document.getElementById('surveyModalFields');
    const surveyModalError = document.getElementById('surveyModalError');
    const btnSurveyModalCancel = document.getElementById('btnSurveyModalCancel');
    const btnSurveyModalSubmit = document.getElementById('btnSurveyModalSubmit');

    let profile = null;
    let currentMustChange = false;
    let historyLoaded = false;
    let surveyModalConfigId = null;

    function show(el, on) {
      el.classList.toggle('hidden', !on);
    }

    function setLoginLoading(loading) {
      if (!loginBtn) return;
      loginBtn.disabled = loading;
      loginBtn.classList.toggle('loading', loading);
      var label = loginBtn.querySelector('.btn-label');
      if (label) label.textContent = loading ? 'Đang đăng nhập…' : 'Đăng nhập';
    }

    function setSubmitLoading(loading) {
      btnSubmit.disabled = loading;
      btnSubmit.classList.toggle('loading', loading);
      var label = btnSubmit.querySelector('.btn-label');
      if (label) label.textContent = loading ? 'Đang gửi…' : 'Gửi góp ý chung';
    }

    function setModalSubmitLoading(loading) {
      if (!btnSurveyModalSubmit) return;
      btnSurveyModalSubmit.disabled = loading;
      btnSurveyModalSubmit.classList.toggle('loading', loading);
      var label = btnSurveyModalSubmit.querySelector('.btn-label');
      if (label) label.textContent = loading ? 'Đang gửi…' : 'Gửi khảo sát';
    }

    async function apiLogin(username, password) {
      const res = await fetch(API_URL + '/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, portal: 'student' }),
      });
      const data = await res.json().catch(function () {
        return {};
      });
      if (!res.ok) throw new Error(data.detail || 'Đăng nhập thất bại');
      return data;
    }

    async function apiProfile() {
      const res = await fetch(API_URL + '/users/me', { headers: authHeaders(false) });
      if (res.status === 401) return null;
      if (!res.ok) throw new Error('Không tải được hồ sơ');
      return res.json();
    }

    async function apiChangePassword(oldPassword, newPassword) {
      const res = await fetch(API_URL + '/auth/change-password', {
        method: 'POST',
        headers: authHeaders(true),
        body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
      });
      const data = await res.json().catch(function () {
        return {};
      });
      if (!res.ok) throw new Error(data.detail || 'Đổi mật khẩu thất bại');
      return data;
    }

    async function apiSubmitFeedback(content) {
      const res = await fetch(API_URL + '/feedbacks', {
        method: 'POST',
        headers: authHeaders(true),
        body: JSON.stringify({ content: content }),
      });
      const data = await res.json().catch(function () {
        return {};
      });
      if (!res.ok) throw new Error(detailToMessage(data.detail) || 'Gửi thất bại');
      return data;
    }

    function detailToMessage(detail) {
      if (detail == null) return '';
      if (typeof detail === 'string') return detail;
      if (Array.isArray(detail)) {
        return detail
          .map(function (x) {
            return x.msg || x.message || JSON.stringify(x);
          })
          .join('; ');
      }
      return String(detail);
    }

    async function apiSurveyOfferings() {
      const res = await fetch(API_URL + '/student/survey/offerings', {
        headers: authHeaders(false),
      });
      const data = await res.json().catch(function () {
        return [];
      });
      if (!res.ok) throw new Error(detailToMessage(data.detail) || 'Không tải danh sách môn');
      return Array.isArray(data) ? data : [];
    }

    async function apiSubmitSurveyFeedback(surveyConfigId, answers) {
      const res = await fetch(API_URL + '/feedbacks', {
        method: 'POST',
        headers: authHeaders(true),
        body: JSON.stringify({
          survey_config_id: surveyConfigId,
          answers: answers,
        }),
      });
      const data = await res.json().catch(function () {
        return {};
      });
      if (!res.ok) throw new Error(detailToMessage(data.detail) || 'Gửi khảo sát thất bại');
      return data;
    }

    async function apiMyHistory() {
      const res = await fetch(API_URL + '/feedbacks/my-history?limit=100', {
        headers: authHeaders(false),
      });
      const data = await res.json().catch(function () {
        return {};
      });
      if (!res.ok) throw new Error(data.detail || 'Không tải lịch sử');
      return data;
    }

    function renderHeader() {
      if (!profile) return;
      var name = profile.full_name || profile.username;
      greetingEl.textContent = 'Chào bạn, ' + name;
      var lop = profile.class_name ? profile.class_name : '—';
      if (profile.department) lop += ' · ' + profile.department;
      metaEl.textContent = 'MSSV: ' + profile.username + ' · Lớp: ' + lop;
      currentMustChange = !!profile.must_change_password;
      show(mustChangeBanner, currentMustChange);
    }

    function showLoginView() {
      setToken(null);
      profile = null;
      historyLoaded = false;
      show(loginSection, true);
      show(appSection, false);
    }

    async function showAppView() {
      show(loginSection, false);
      show(appSection, true);
      try {
        profile = await apiProfile();
        if (!profile || profile.role !== 'student') {
          setToken(null);
          showLoginView();
          loginError.textContent = 'Phiên không hợp lệ. Vui lòng đăng nhập lại.';
          return;
        }
        renderHeader();
        goSurvey();
      } catch (_) {
        setToken(null);
        showLoginView();
      }
    }

    function goSurvey() {
      navTabs.forEach(function (t) {
        t.classList.toggle('active', t.getAttribute('data-page') === 'survey');
      });
      show(surveyPage, true);
      show(historyPage, false);
      loadSurveyOfferings();
    }

    async function loadSurveyOfferings() {
      if (!surveyOfferingsList || !surveyOfferingsEmpty) return;
      surveyOfferingsList.innerHTML = '';
      surveyOfferingsEmpty.textContent = DEFAULT_SURVEY_OFFERINGS_EMPTY;
      if (!token() || currentMustChange) {
        show(surveyOfferingsEmpty, false);
        return;
      }
      try {
        var list = await apiSurveyOfferings();
        if (!list.length) {
          show(surveyOfferingsEmpty, true);
          return;
        }
        show(surveyOfferingsEmpty, false);
        list.forEach(function (o) {
          var row = document.createElement('div');
          row.className = 'offering-row';
          row.innerHTML =
            '<div><div class="offering-title">Môn: ' +
            esc(o.subject_name) +
            '</div><div class="offering-meta">' +
            esc(o.subject_code) +
            ' · ' +
            esc(o.semester_name) +
            '</div></div>';
          var btn = document.createElement('button');
          btn.type = 'button';
          btn.className = 'btn primary btn-sm';
          btn.textContent = 'Điền form';
          btn.addEventListener('click', function () {
            openSurveyModal(o);
          });
          row.appendChild(btn);
          surveyOfferingsList.appendChild(row);
        });
      } catch (e) {
        show(surveyOfferingsEmpty, true);
        surveyOfferingsEmpty.textContent =
          (e.message || String(e)) + ' — không tải được danh sách môn.';
      }
    }

    function openSurveyModal(o) {
      if (!surveyModalBackdrop || !surveyModalFields) return;
      surveyModalConfigId = o.survey_config_id;
      surveyModalError.textContent = '';
      document.getElementById('surveyModalTitle').textContent = 'Khảo sát: ' + o.subject_name;
      surveyModalMeta.textContent = o.subject_code + ' · ' + o.semester_name;
      surveyModalFields.innerHTML = '';
      SURVEY_QUESTIONS.forEach(function (q, i) {
        var wrap = document.createElement('div');
        wrap.className = 'sq-field';
        var lab = document.createElement('label');
        lab.className = 'lbl';
        lab.setAttribute('for', 'sq_' + i);
        lab.textContent = q;
        var ta = document.createElement('textarea');
        ta.id = 'sq_' + i;
        ta.required = true;
        ta.setAttribute('rows', '3');
        wrap.appendChild(lab);
        wrap.appendChild(ta);
        surveyModalFields.appendChild(wrap);
      });
      surveyModalBackdrop.classList.remove('hidden');
      surveyModalBackdrop.setAttribute('aria-hidden', 'false');
    }

    function closeSurveyModal() {
      surveyModalConfigId = null;
      if (surveyModalBackdrop) {
        surveyModalBackdrop.classList.add('hidden');
        surveyModalBackdrop.setAttribute('aria-hidden', 'true');
      }
      if (surveyModalFields) surveyModalFields.innerHTML = '';
    }

    function goHistory() {
      navTabs.forEach(function (t) {
        t.classList.toggle('active', t.getAttribute('data-page') === 'history');
      });
      show(surveyPage, false);
      show(historyPage, true);
      loadHistory();
    }

    function buildAccordion(rounds) {
      historyAccordion.innerHTML = '';
      if (!rounds || !rounds.length) {
        show(historyEmpty, true);
        return;
      }
      show(historyEmpty, false);

      rounds.forEach(function (round, idx) {
        var item = document.createElement('div');
        item.className = 'acc-item';
        var lid = String(round.stored_label || 'neutral');
        var lc = labelClass(lid);

        var trigger = document.createElement('button');
        trigger.type = 'button';
        trigger.className = 'acc-trigger';
        trigger.setAttribute('aria-expanded', 'false');
        var formTitle = round.subject_name
          ? 'Môn: ' +
            round.subject_name +
            (round.semester_name ? ' · ' + round.semester_name : '')
          : SURVEY_FORM_NAME;
        trigger.innerHTML =
          '<span class="acc-trigger-main">' +
          '<span class="acc-date">' +
          esc(formatDate(round.created_at)) +
          '</span>' +
          '<span class="acc-sep" aria-hidden="true">|</span>' +
          '<span class="acc-form-name">' +
          esc(formTitle) +
          '</span>' +
          '<span class="badge-vi ' +
          lc +
          '">' +
          esc(labelVi(lid)) +
          '</span>' +
          '</span>' +
          '<span class="acc-chevron" aria-hidden="true">▼</span>';

        var panel = document.createElement('div');
        panel.className = 'acc-panel';
        var inner = '';
        var sents = round.sentences || [];
        if (!sents.length) {
          inner +=
            '<p class="muted small" style="padding:0.75rem 0">Không tải được chi tiết câu (model chưa sẵn sàng).</p>';
        } else {
          sents.forEach(function (sent) {
            var st = String(sent.sentiment || 'neutral');
            inner +=
              '<div class="history-detail-row">' +
              '<div class="history-detail-text">“' +
              esc(sent.text || '') +
              '”</div>' +
              '<div class="history-detail-meta">' +
              '<span class="badge-vi ' +
              labelClass(st) +
              '">' +
              esc(labelVi(st)) +
              '</span>' +
              '</div></div>';
          });
        }
        panel.innerHTML = inner;

        trigger.addEventListener('click', function () {
          var open = item.classList.toggle('open');
          trigger.setAttribute('aria-expanded', open ? 'true' : 'false');
        });

        item.appendChild(trigger);
        item.appendChild(panel);
        historyAccordion.appendChild(item);
      });
    }

    async function loadHistory() {
      historyError.textContent = '';
      if (!token()) return;
      try {
        var data = await apiMyHistory();
        buildAccordion(data.rounds || []);
        historyLoaded = true;
      } catch (e) {
        historyError.textContent = e.message || String(e);
        show(historyEmpty, false);
        historyAccordion.innerHTML = '';
      }
    }

    loginForm.addEventListener('submit', async function (e) {
      e.preventDefault();
      loginError.textContent = '';
      var u = normalizeLoginUsername(document.getElementById('username').value);
      var p = document.getElementById('password').value;
      if (!u || !p) return;
      setLoginLoading(true);
      try {
        var data = await apiLogin(u, p);
        setToken(data.access_token);
        await showAppView();
      } catch (err) {
        loginError.textContent = err.message || String(err);
      } finally {
        setLoginLoading(false);
      }
    });

    btnLogout.addEventListener('click', function () {
      document.getElementById('username').value = '';
      document.getElementById('password').value = '';
      thankYou.classList.add('hidden');
      surveyInput.value = '';
      closeSurveyModal();
      showLoginView();
    });

    if (btnSurveyModalCancel) {
      btnSurveyModalCancel.addEventListener('click', closeSurveyModal);
    }
    if (surveyModalBackdrop) {
      surveyModalBackdrop.addEventListener('click', function (e) {
        if (e.target === surveyModalBackdrop) closeSurveyModal();
      });
    }
    if (btnSurveyModalSubmit) {
      btnSurveyModalSubmit.addEventListener('click', async function () {
        if (surveyModalConfigId == null) return;
        surveyModalError.textContent = '';
        var answers = [];
        for (var i = 0; i < SURVEY_QUESTIONS.length; i++) {
          var el = document.getElementById('sq_' + i);
          var a = el && el.value ? el.value.trim() : '';
          if (!a) {
            surveyModalError.textContent = 'Vui lòng trả lời đủ các câu hỏi.';
            return;
          }
          answers.push({ question: SURVEY_QUESTIONS[i], answer: a });
        }
        setModalSubmitLoading(true);
        try {
          await apiSubmitSurveyFeedback(surveyModalConfigId, answers);
          closeSurveyModal();
          thankYou.classList.remove('hidden');
          thankYou.textContent = 'Cảm ơn bạn, khảo sát đã được ghi nhận!';
          historyLoaded = false;
          loadSurveyOfferings();
        } catch (err) {
          surveyModalError.textContent = err.message || String(err);
        } finally {
          setModalSubmitLoading(false);
        }
      });
    }

    navTabs.forEach(function (tab) {
      tab.addEventListener('click', function () {
        if (tab.getAttribute('data-page') === 'history') goHistory();
        else goSurvey();
      });
    });

    changePwdForm.addEventListener('submit', async function (e) {
      e.preventDefault();
      pwdMsg.textContent = '';
      var oldP = document.getElementById('oldPwd').value;
      var newP = document.getElementById('newPwd').value;
      try {
        await apiChangePassword(oldP, newP);
        pwdMsg.textContent = 'Đã cập nhật mật khẩu.';
        document.getElementById('oldPwd').value = '';
        document.getElementById('newPwd').value = '';
        profile = await apiProfile();
        renderHeader();
      } catch (err) {
        pwdMsg.textContent = err.message || String(err);
      }
    });

    btnSubmit.addEventListener('click', async function () {
      var text = surveyInput.value.trim();
      if (!text) return;
      if (currentMustChange) {
        surveyError.textContent = 'Vui lòng đổi mật khẩu ở khối phía trên trước khi gửi phản hồi.';
        return;
      }
      surveyError.textContent = '';
      thankYou.classList.add('hidden');
      setSubmitLoading(true);
      try {
        await apiSubmitFeedback(text);
        thankYou.classList.remove('hidden');
        thankYou.textContent =
          'Cảm ơn bạn, phản hồi của bạn đã được ghi nhận!';
        surveyInput.value = '';
        historyLoaded = false;
      } catch (err) {
        surveyError.textContent = 'Lỗi: ' + (err.message || String(err));
      } finally {
        setSubmitLoading(false);
      }
    });

    async function boot() {
      await migrateLegacyStudentToken();
      if (!token()) {
        showLoginView();
        return;
      }
      await showAppView();
    }

    boot();
  });
})();
