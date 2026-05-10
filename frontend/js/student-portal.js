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
  const LABEL_VI = {
    positive: 'Tích cực',
    negative: 'Tiêu cực',
    neutral: 'Trung tính',
  };
  /** Khớp backend/app/services/sentiment_pipeline.py và student-survey-subject.js */
  const SURVEY_TEACHER_NAME_Q = 'Tên giảng viên phụ trách môn học';
  const SURVEY_OPTIONAL_COMMENT_Q =
    'Bạn có góp ý thêm nào khác không? (Nếu không, ghi "Không")';

  function foldViLower(s) {
    try {
      return String(s || '')
        .replace(/\s+/g, ' ')
        .trim()
        .toLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '');
    } catch (_) {
      return String(s || '')
        .replace(/\s+/g, ' ')
        .trim()
        .toLowerCase();
    }
  }

  function stripSurroundingQuotes(s) {
    var t = String(s || '').trim();
    if (t.length >= 2) {
      var a = t[0];
      var b = t[t.length - 1];
      if (a === b && '\'"“”‘’'.indexOf(a) >= 0) return t.slice(1, -1).trim();
    }
    return t;
  }

  function isEffectivelyNoExtraComment(answer) {
    var a = stripSurroundingQuotes(answer);
    a = String(a || '')
      .replace(/\s+/g, ' ')
      .trim();
    if (!a) return true;
    var f = foldViLower(a);
    return f === 'khong' || f === 'ko';
  }

  function skipSurveyPairForSentiment(q, a) {
    var qs = String(q || '').trim();
    if (qs === SURVEY_TEACHER_NAME_Q) return true;
    if (qs === SURVEY_OPTIONAL_COMMENT_Q && isEffectivelyNoExtraComment(a)) return true;
    return false;
  }

  /** Mỗi phần tử = một dòng gửi PhoBERT (khớp split_by_newlines sau khi nối bằng \\n). */
  function expandSurveyLinesForSentimentModel(pairs) {
    var out = [];
    if (!pairs || !pairs.length) return out;
    for (var i = 0; i < pairs.length; i++) {
      var p = pairs[i];
      if (skipSurveyPairForSentiment(p.q, p.a)) continue;
      var text = String(p.a || '').replace(/\r\n/g, '\n').trim();
      if (!text) continue;
      var lines = text.split('\n');
      for (var j = 0; j < lines.length; j++) {
        var line = lines[j].replace(/\s+/g, ' ').trim();
        if (line) out.push({ q: p.q, line: line });
      }
    }
    return out;
  }

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
    const PORTAL_SURVEY_ONLY = document.getElementById('surveyOnlyApp') !== null;
    const loginSection = document.getElementById('loginSection');
    const appSection = document.getElementById('appSection');
    const loginForm = document.getElementById('loginForm');
    const navTabs = document.querySelectorAll('.nav-tab');
    const surveyPage = document.getElementById('surveyPage');
    const loginError = document.getElementById('loginError');
    const loginBtn = document.getElementById('btnLogin');
    const greetingEl = document.getElementById('greeting');
    const metaEl = document.getElementById('metaLine');
    const mustChangeBanner = document.getElementById('mustChangeBanner');
    const changePwdForm = document.getElementById('changePwdForm');
    const pwdMsg = document.getElementById('pwdMsg');
    const btnLogout = document.getElementById('btnLogout');
    const historyPage = document.getElementById('historyPage');
    const surveyInput = document.getElementById('surveyInput');
    const btnSubmit = document.getElementById('btnSubmitSurvey');
    const thankYou = document.getElementById('thankYou');
    const surveyError = document.getElementById('surveyError');
    const historyAccordion = document.getElementById('historyAccordion');
    const historyError = document.getElementById('historyError');
    const historyEmpty = document.getElementById('historyEmpty');
    const surveyOfferingsList = document.getElementById('surveyOfferingsList');
    const surveyOfferingsEmpty = document.getElementById('surveyOfferingsEmpty');

    let profile = null;
    let currentMustChange = false;
    let historyLoaded = false;

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
      if (!btnSubmit) return;
      btnSubmit.disabled = loading;
      btnSubmit.classList.toggle('loading', loading);
      var label = btnSubmit.querySelector('.btn-label');
      if (label) label.textContent = loading ? 'Đang gửi…' : 'Gửi góp ý chung';
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
      if (!profile || !greetingEl || !metaEl) return;
      var name = profile.full_name || profile.username;
      greetingEl.textContent = 'Chào bạn, ' + name;
      var lop = profile.class_name ? profile.class_name : '—';
      if (profile.department) lop += ' · ' + profile.department;
      metaEl.textContent = 'MSSV: ' + profile.username + ' · Lớp: ' + lop;
      currentMustChange = !!profile.must_change_password;
      show(mustChangeBanner, currentMustChange);
    }

    function showLoginView() {
      if (PORTAL_SURVEY_ONLY) return;
      setToken(null);
      profile = null;
      historyLoaded = false;
      if (loginSection) show(loginSection, true);
      if (appSection) show(appSection, false);
    }

    async function showSurveyOnlyApp() {
      try {
        profile = await apiProfile();
        if (!profile || profile.role !== 'student') {
          setToken(null);
          window.location.replace('student.html');
          return;
        }
        renderHeader();
        goSurvey();
      } catch (_) {
        setToken(null);
        window.location.replace('student.html');
      }
    }

    function goSurvey() {
      if (!PORTAL_SURVEY_ONLY) return;
      navTabs.forEach(function (t) {
        var on = t.getAttribute('data-page') === 'survey';
        t.classList.toggle('active', on);
        t.setAttribute('aria-selected', on ? 'true' : 'false');
      });
      if (surveyPage) show(surveyPage, true);
      if (historyPage) show(historyPage, false);
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
          var link = document.createElement('a');
          link.href =
            'student-survey-subject.html?c=' + encodeURIComponent(String(o.survey_config_id));
          link.className = 'btn primary btn-sm offering-form-link';
          link.textContent = 'Đánh giá';
          row.appendChild(link);
          surveyOfferingsList.appendChild(row);
        });
      } catch (e) {
        show(surveyOfferingsEmpty, true);
        surveyOfferingsEmpty.textContent =
          (e.message || String(e)) + ' — không tải được danh sách môn.';
      }
    }

    function goHistory() {
      if (!PORTAL_SURVEY_ONLY) return;
      navTabs.forEach(function (t) {
        var on = t.getAttribute('data-page') === 'history';
        t.classList.toggle('active', on);
        t.setAttribute('aria-selected', on ? 'true' : 'false');
      });
      if (surveyPage) show(surveyPage, false);
      if (historyPage) show(historyPage, true);
      loadHistory();
    }

    function parseSurveyHistoryBlocks(content) {
      if (content == null || content === '') return null;
      var parts = String(content).replace(/\r\n/g, '\n').split(/\n\n/);
      var out = [];
      for (var i = 0; i < parts.length; i++) {
        var block = parts[i].trim();
        if (!block) continue;
        var nl = block.indexOf('\n');
        if (nl === -1) {
          out.push({ q: '', a: block });
          continue;
        }
        out.push({
          q: block.slice(0, nl).trim(),
          a: block.slice(nl + 1).trim(),
        });
      }
      return out.length ? out : null;
    }

    function buildAccordion(rounds) {
      if (!historyAccordion) return;
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
        var pairs =
          round.survey_config_id != null ? parseSurveyHistoryBlocks(round.content) : null;
        var chunks = pairs ? expandSurveyLinesForSentimentModel(pairs) : null;
        if (!sents.length) {
          inner +=
            '<p class="muted small" style="padding:0.75rem 0">Không tải được chi tiết câu (model chưa sẵn sàng).</p>';
        } else if (chunks && chunks.length === sents.length) {
          for (var si = 0; si < chunks.length; si++) {
            var st = String(sents[si].sentiment || 'neutral');
            var ch = chunks[si];
            if (ch.q) {
              inner +=
                '<div class="history-detail-row history-detail-q">' +
                '<div class="history-detail-text muted small">' +
                esc(ch.q) +
                '</div></div>';
            }
            inner +=
              '<div class="history-detail-row">' +
              '<div class="history-detail-text">“' +
              esc(ch.line) +
              '”</div>' +
              '<div class="history-detail-meta">' +
              '<span class="badge-vi ' +
              labelClass(st) +
              '">' +
              esc(labelVi(st)) +
              '</span>' +
              '</div></div>';
          }
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
      if (!historyAccordion || !historyError) return;
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

    if (loginForm) {
      loginForm.addEventListener('submit', async function (e) {
        e.preventDefault();
        if (loginError) loginError.textContent = '';
        var uEl = document.getElementById('username');
        var pEl = document.getElementById('password');
        var u = normalizeLoginUsername(uEl ? uEl.value : '');
        var p = pEl ? pEl.value : '';
        if (!u || !p) return;
        setLoginLoading(true);
        try {
          var data = await apiLogin(u, p);
          setToken(data.access_token);
          window.location.href = 'student-survey.html';
        } catch (err) {
          if (loginError) loginError.textContent = err.message || String(err);
        } finally {
          setLoginLoading(false);
        }
      });
    }

    btnLogout.addEventListener('click', function () {
      var uEl = document.getElementById('username');
      var pEl = document.getElementById('password');
      if (uEl) uEl.value = '';
      if (pEl) pEl.value = '';
      if (thankYou) thankYou.classList.add('hidden');
      if (surveyInput) surveyInput.value = '';
      if (PORTAL_SURVEY_ONLY) {
        setToken(null);
        window.location.href = 'student.html';
        return;
      }
      showLoginView();
    });

    if (PORTAL_SURVEY_ONLY && navTabs.length) {
      navTabs.forEach(function (tab) {
        tab.addEventListener('click', function () {
          if (tab.getAttribute('data-page') === 'history') goHistory();
          else goSurvey();
        });
      });
    }

    if (changePwdForm) changePwdForm.addEventListener('submit', async function (e) {
      e.preventDefault();
      if (pwdMsg) pwdMsg.textContent = '';
      var oldP = document.getElementById('oldPwd').value;
      var newP = document.getElementById('newPwd').value;
      try {
        await apiChangePassword(oldP, newP);
        if (pwdMsg) pwdMsg.textContent = 'Đã cập nhật mật khẩu.';
        document.getElementById('oldPwd').value = '';
        document.getElementById('newPwd').value = '';
        profile = await apiProfile();
        renderHeader();
        loadSurveyOfferings();
        historyLoaded = false;
        if (PORTAL_SURVEY_ONLY && historyPage && !historyPage.classList.contains('hidden')) {
          loadHistory();
        }
      } catch (err) {
        if (pwdMsg) pwdMsg.textContent = err.message || String(err);
      }
    });

    if (btnSubmit) btnSubmit.addEventListener('click', async function () {
      var text = surveyInput.value.trim();
      if (!text) return;
      if (currentMustChange) {
        if (surveyError) surveyError.textContent = 'Vui lòng đổi mật khẩu ở khối phía trên trước khi gửi phản hồi.';
        return;
      }
      if (surveyError) surveyError.textContent = '';
      if (thankYou) thankYou.classList.add('hidden');
      setSubmitLoading(true);
      try {
        await apiSubmitFeedback(text);
        if (thankYou) {
          thankYou.classList.remove('hidden');
          thankYou.textContent =
            'Cảm ơn bạn, phản hồi của bạn đã được ghi nhận!';
        }
        surveyInput.value = '';
        historyLoaded = false;
      } catch (err) {
        if (surveyError) surveyError.textContent = 'Lỗi: ' + (err.message || String(err));
      } finally {
        setSubmitLoading(false);
      }
    });

    async function boot() {
      await migrateLegacyStudentToken();
      if (PORTAL_SURVEY_ONLY) {
        if (!token()) {
          window.location.replace('student.html');
          return;
        }
        await showSurveyOnlyApp();
        return;
      }
      if (!token()) {
        showLoginView();
        return;
      }
      window.location.replace('student-survey.html');
    }

    boot();
  });
})();
