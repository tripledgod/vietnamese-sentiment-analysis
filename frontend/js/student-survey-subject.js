/**
 * Trang form khảo sát theo một môn (survey_config_id qua ?c=).
 */
(function () {
  const API_URL = 'http://localhost:8000';
  const TOKEN_KEY = 'access_token_student';
  const OTHER_PORTAL_TOKEN_KEY = 'access_token_teacher';
  const LEGACY_TOKEN_KEY = 'access_token';
  const TEACHER_NAME_QUESTION = 'Tên giảng viên phụ trách môn học';
  const SURVEY_QUESTIONS = [
    'Bạn đánh giá thế nào về phương pháp giảng dạy của giảng viên?',
    'Cơ sở vật chất phục vụ môn học này ra sao?',
    'Nội dung môn học có đáp ứng kỳ vọng của bạn không?',
    'Bạn có góp ý thêm nào khác không? (Nếu không, ghi "Không")',
  ];

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

  async function apiProfile() {
    const res = await fetch(API_URL + '/users/me', { headers: authHeaders(false) });
    if (res.status === 401) return null;
    if (!res.ok) throw new Error('Không tải được hồ sơ');
    return res.json();
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

  document.addEventListener('DOMContentLoaded', function () {
    const root = document.getElementById('surveySubjectFormApp');
    if (!root) return;

    const greetingEl = document.getElementById('greeting');
    const metaEl = document.getElementById('metaLine');
    const mustChangeBanner = document.getElementById('mustChangeBanner');
    const changePwdForm = document.getElementById('changePwdForm');
    const pwdMsg = document.getElementById('pwdMsg');
    const btnLogout = document.getElementById('btnLogout');
    const bootErrorEl = document.getElementById('subjectSurveyBootError');
    const formShell = document.getElementById('subjectSurveyFormShell');
    const titleEl = document.getElementById('subjectSurveyTitle');
    const metaSurveyEl = document.getElementById('subjectSurveyMeta');
    const fieldsEl = document.getElementById('subjectSurveyFields');
    const submitErrEl = document.getElementById('subjectSurveySubmitError');
    const thankYouEl = document.getElementById('subjectSurveyThankYou');
    const btnSubmit = document.getElementById('btnSubjectSurveySubmit');

    const params = new URLSearchParams(window.location.search);
    const cidRaw = params.get('c');
    const surveyConfigId =
      cidRaw != null && String(cidRaw).trim() !== '' ? parseInt(String(cidRaw).trim(), 10) : NaN;

    let profile = null;
    let currentMustChange = false;
    let activeConfigId = null;

    function show(el, on) {
      if (!el) return;
      el.classList.toggle('hidden', !on);
    }

    function showBootError(msg) {
      if (bootErrorEl) {
        bootErrorEl.textContent = msg;
        show(bootErrorEl, true);
      }
      show(formShell, false);
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

    function setSubmitLoading(loading) {
      if (!btnSubmit) return;
      btnSubmit.disabled = loading;
      btnSubmit.classList.toggle('loading', loading);
      var label = btnSubmit.querySelector('.btn-label');
      if (label) label.textContent = loading ? 'Đang gửi…' : 'Gửi khảo sát';
    }

    function buildFormFields() {
      if (!fieldsEl) return;
      fieldsEl.innerHTML = '';
      var teacherWrap = document.createElement('div');
      teacherWrap.className = 'sq-field sq-field--teacher';
      var teacherLab = document.createElement('label');
      teacherLab.className = 'lbl';
      teacherLab.setAttribute('for', 'sq_teacher_name');
      teacherLab.textContent = TEACHER_NAME_QUESTION;
      var teacherIn = document.createElement('input');
      teacherIn.type = 'text';
      teacherIn.id = 'sq_teacher_name';
      teacherIn.required = true;
      teacherIn.setAttribute('autocomplete', 'name');
      teacherIn.placeholder = 'Ví dụ: Nguyễn Văn A';
      teacherWrap.appendChild(teacherLab);
      teacherWrap.appendChild(teacherIn);
      fieldsEl.appendChild(teacherWrap);

      SURVEY_QUESTIONS.forEach(function (q, i) {
        var wrap = document.createElement('div');
        wrap.className = 'sq-field';
        var lab = document.createElement('label');
        lab.className = 'lbl';
        lab.setAttribute('for', 'sq_subj_' + i);
        lab.textContent = q;
        var ta = document.createElement('textarea');
        ta.id = 'sq_subj_' + i;
        ta.required = true;
        ta.setAttribute('rows', '4');
        wrap.appendChild(lab);
        wrap.appendChild(ta);
        fieldsEl.appendChild(wrap);
      });
    }

    async function boot() {
      await migrateLegacyStudentToken();
      if (!token()) {
        window.location.replace('student.html');
        return;
      }

      if (!Number.isFinite(surveyConfigId) || surveyConfigId < 1) {
        showBootError('Liên kết không hợp lệ (thiếu mã khảo sát môn). Hãy quay lại trang khảo sát và chọn môn.');
        return;
      }
      activeConfigId = surveyConfigId;

      try {
        profile = await apiProfile();
        if (!profile || profile.role !== 'student') {
          setToken(null);
          window.location.replace('student.html');
          return;
        }
        renderHeader();
      } catch (_) {
        setToken(null);
        window.location.replace('student.html');
        return;
      }

      if (currentMustChange) {
        if (bootErrorEl) {
          bootErrorEl.textContent = '';
          show(bootErrorEl, false);
        }
        show(formShell, false);
        return;
      }

      try {
        var list = await apiSurveyOfferings();
        var o = list.find(function (x) {
          return Number(x.survey_config_id) === Number(activeConfigId);
        });
        if (!o) {
          showBootError(
            'Không tìm thấy môn này trong danh sách khảo sát hiện tại. Có thể giảng viên đã đóng đợt hoặc bạn không thuộc lớp được mở.'
          );
          return;
        }
        show(bootErrorEl, false);
        if (titleEl) titleEl.textContent = 'Khảo sát: ' + o.subject_name;
        if (metaSurveyEl) metaSurveyEl.textContent = o.subject_code + ' · ' + o.semester_name;
        buildFormFields();
        show(formShell, true);
        show(thankYouEl, false);
        if (submitErrEl) submitErrEl.textContent = '';
      } catch (e) {
        showBootError((e.message || String(e)) + ' — không tải được form.');
      }
    }

    btnLogout.addEventListener('click', function () {
      setToken(null);
      window.location.href = 'student.html';
    });

    if (changePwdForm) {
      changePwdForm.addEventListener('submit', async function (e) {
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
          if (!currentMustChange) {
            await boot();
          }
        } catch (err) {
          if (pwdMsg) pwdMsg.textContent = err.message || String(err);
        }
      });
    }

    if (btnSubmit) {
      btnSubmit.addEventListener('click', async function () {
        if (activeConfigId == null || currentMustChange) return;
        if (submitErrEl) submitErrEl.textContent = '';
        var teacherEl = document.getElementById('sq_teacher_name');
        var teacherName = teacherEl && teacherEl.value ? teacherEl.value.trim() : '';
        if (!teacherName) {
          if (submitErrEl) submitErrEl.textContent = 'Vui lòng điền tên giảng viên.';
          return;
        }
        var answers = [{ question: TEACHER_NAME_QUESTION, answer: teacherName }];
        for (var i = 0; i < SURVEY_QUESTIONS.length; i++) {
          var el = document.getElementById('sq_subj_' + i);
          var a = el && el.value ? el.value.trim() : '';
          if (!a) {
            if (submitErrEl) submitErrEl.textContent = 'Vui lòng trả lời đủ các câu hỏi.';
            return;
          }
          answers.push({ question: SURVEY_QUESTIONS[i], answer: a });
        }
        setSubmitLoading(true);
        try {
          await apiSubmitSurveyFeedback(activeConfigId, answers);
          if (thankYouEl) {
            thankYouEl.classList.remove('hidden');
            thankYouEl.textContent = 'Cảm ơn bạn, khảo sát đã được ghi nhận!';
          }
          show(formShell, false);
        } catch (err) {
          if (submitErrEl) submitErrEl.textContent = err.message || String(err);
        } finally {
          setSubmitLoading(false);
        }
      });
    }

    boot();
  });
})();
