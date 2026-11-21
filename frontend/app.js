function getDefaultUrls() {
  const host = window.location.hostname;
  const port = window.location.port;
  const isLocalStatic =
    (host === "127.0.0.1" || host === "localhost") && port !== "3000";

  if (isLocalStatic) {
    return {
      student: "http://127.0.0.1:8001",
      course: "http://127.0.0.1:8002",
      reg: "http://127.0.0.1:8003",
    };
  }

  return {
    student: `${window.location.origin}/api/students`,
    course: `${window.location.origin}/api/courses`,
    reg: `${window.location.origin}/api/registrations`,
  };
}

const defaults = getDefaultUrls();

// Nếu trước đó lỡ lưu URL /api/... khi đang chạy Live Server local thì tự làm sạch để không lỗi
const savedStudentUrl = localStorage.getItem("STUDENT_SERVICE_URL");
const savedCourseUrl = localStorage.getItem("COURSE_SERVICE_URL");
const savedRegUrl = localStorage.getItem("REGISTRATION_SERVICE_URL");

const isLocalHost =
  window.location.hostname === "127.0.0.1" || window.location.hostname === "localhost";

if (
  isLocalHost &&
  window.location.port !== "3000" &&
  ((savedStudentUrl && savedStudentUrl.includes("/api/")) ||
    (savedCourseUrl && savedCourseUrl.includes("/api/")) ||
    (savedRegUrl && savedRegUrl.includes("/api/")))
) {
  localStorage.removeItem("STUDENT_SERVICE_URL");
  localStorage.removeItem("COURSE_SERVICE_URL");
  localStorage.removeItem("REGISTRATION_SERVICE_URL");
}

const DEFAULT_URLS = {
  student: localStorage.getItem("STUDENT_SERVICE_URL") || defaults.student,
  course: localStorage.getItem("COURSE_SERVICE_URL") || defaults.course,
  reg: localStorage.getItem("REGISTRATION_SERVICE_URL") || defaults.reg,
};

const STUDENT_STORAGE_KEY = "SELECTED_STUDENT_CODE";
const PAGE_STORAGE_KEY = "ACTIVE_WORKSPACE_PAGE";

document.getElementById("studentUrl").value = DEFAULT_URLS.student;
document.getElementById("courseUrl").value = DEFAULT_URLS.course;
document.getElementById("regUrl").value = DEFAULT_URLS.reg;

let latestSections = [];

function getUrls() {
  return {
    student: document.getElementById("studentUrl").value.trim().replace(/\/+$/, ""),
    course: document.getElementById("courseUrl").value.trim().replace(/\/+$/, ""),
    reg: document.getElementById("regUrl").value.trim().replace(/\/+$/, ""),
  };
}

function getActiveStudentCode() {
  return (localStorage.getItem(STUDENT_STORAGE_KEY) || "").trim();
}

function getActivePage() {
  return localStorage.getItem(PAGE_STORAGE_KEY) || "";
}

function saveUrls() {
  const urls = getUrls();
  localStorage.setItem("STUDENT_SERVICE_URL", urls.student);
  localStorage.setItem("COURSE_SERVICE_URL", urls.course);
  localStorage.setItem("REGISTRATION_SERVICE_URL", urls.reg);
  loadAll();
}

function setMessage(text, isError = false) {
  const targets = [document.getElementById("msg"), document.getElementById("msgWorkspace")];
  targets.forEach((el) => {
    if (!el) return;
    el.style.color = isError ? "#991b1b" : "#166534";
    el.style.background = isError ? "#fee2e2" : "#dcfce7";
    el.style.borderColor = isError ? "#fca5a5" : "#86efac";
    el.textContent = text;
  });
}

function syncScreenVisibility() {
  const code = getActiveStudentCode();
  const page = getActivePage();

  const studentScreen = document.getElementById("studentScreen");
  const workspaceScreen = document.getElementById("workspaceScreen");
  const menuBox = document.getElementById("studentActionMenu");
  const sectionsPage = document.getElementById("sectionsPage");
  const registrationsPage = document.getElementById("registrationsPage");
  const navSectionsBtn = document.getElementById("navSectionsBtn");
  const navRegsBtn = document.getElementById("navRegsBtn");

  if (!code) {
    studentScreen.style.display = "block";
    workspaceScreen.style.display = "none";
    menuBox.style.display = "none";
    return;
  }

  if (page === "sections" || page === "registrations") {
    studentScreen.style.display = "none";
    workspaceScreen.style.display = "block";
    sectionsPage.style.display = page === "sections" ? "block" : "none";
    registrationsPage.style.display = page === "registrations" ? "block" : "none";
    navSectionsBtn.className = page === "sections" ? "" : "secondary";
    navRegsBtn.className = page === "registrations" ? "" : "secondary";
  } else {
    studentScreen.style.display = "block";
    workspaceScreen.style.display = "none";
    menuBox.style.display = "block";
  }
}

function onStudentDropdownChange() {
  const dropdown = document.getElementById("studentDropdown");
  const chosenCode = dropdown.value.trim();

  if (!chosenCode) {
    localStorage.removeItem(STUDENT_STORAGE_KEY);
    localStorage.removeItem(PAGE_STORAGE_KEY);
    syncScreenVisibility();
    loadAll();
    return;
  }

  localStorage.setItem(STUDENT_STORAGE_KEY, chosenCode);
  localStorage.removeItem(PAGE_STORAGE_KEY);
  loadAll();
}

function openPage(pageName) {
  if (!getActiveStudentCode()) return;
  localStorage.setItem(PAGE_STORAGE_KEY, pageName);
  syncScreenVisibility();
  loadAll();
}

function backToStudentScreen() {
  localStorage.removeItem(PAGE_STORAGE_KEY);
  syncScreenVisibility();
  loadAll();
}

function openEditStudentForm(student) {
  document.getElementById("editStudentCode").value = student.student_code;
  document.getElementById("editStudentName").value = student.full_name;
  document.getElementById("editStudentMajor").value = student.major;
  document.getElementById("editStudentPanel").style.display = "block";
  document.getElementById("editStudentName").focus();
}

function closeEditStudentForm() {
  document.getElementById("editStudentPanel").style.display = "none";
  document.getElementById("editStudentCode").value = "";
  document.getElementById("editStudentName").value = "";
  document.getElementById("editStudentMajor").value = "";
}

function toggleAddSectionForm(forceState) {
  const panel = document.getElementById("addSectionPanel");
  const btn = document.getElementById("toggleAddSectionBtn");
  const shouldOpen = typeof forceState === "boolean" ? forceState : panel.style.display === "none";

  panel.style.display = shouldOpen ? "block" : "none";
  btn.textContent = shouldOpen ? "Đóng form" : "+ Thêm học phần";
  if (shouldOpen) {
    document.getElementById("newCourseCode").focus();
  }
}

function renderStudentDropdown(students, activeCode) {
  const dropdown = document.getElementById("studentDropdown");
  dropdown.innerHTML = `<option value="">-- Chọn sinh viên --</option>`;

  students.forEach((st) => {
    const opt = document.createElement("option");
    opt.value = st.student_code;
    opt.textContent = `${st.student_code} - ${st.full_name} (${st.major})`;
    if (st.student_code === activeCode) {
      opt.selected = true;
    }
    dropdown.appendChild(opt);
  });
}

async function loadAll() {
  const urls = getUrls();

  try {
    const [allStudentsRes, secRes] = await Promise.all([
      fetch(`${urls.student}/students`),
      fetch(`${urls.course}/sections`),
    ]);
    const allStudents = await allStudentsRes.json();
    const sections = await secRes.json();
    latestSections = Array.isArray(sections) ? sections : [];

    const code = getActiveStudentCode();
    const validStudent = allStudents.find((s) => s.student_code === code);
    if (code && !validStudent) {
      localStorage.removeItem(STUDENT_STORAGE_KEY);
      localStorage.removeItem(PAGE_STORAGE_KEY);
    }

    const currentCode = getActiveStudentCode();
    renderStudentDropdown(allStudents, currentCode);
    renderStudents(allStudents);
    syncScreenVisibility();

    if (!currentCode) {
      renderSections(latestSections, new Set(), "");
      renderRegistrations([], latestSections);
      return;
    }

    const stRes = await fetch(`${urls.student}/students/${encodeURIComponent(currentCode)}`);
    if (!stRes.ok) {
      renderSections(latestSections, new Set(), currentCode);
      renderRegistrations([], latestSections);
      return;
    }

    const st = await stRes.json();
    const label = `${st.student_code} - ${st.full_name} (${st.major})`;
    document.getElementById("menuStudentLabel").textContent = `Đã chọn sinh viên: ${label} — Chọn trang muốn mở:`;
    document.getElementById("workspaceStudentInfo").textContent = `Sinh viên: ${label}`;

    const regRes = await fetch(`${urls.reg}/registrations?student_code=${encodeURIComponent(currentCode)}`);
    const regs = await regRes.json();
    const regList = Array.isArray(regs) ? regs : [];
    const registeredSectionIds = new Set(regList.map((r) => r.section_id));

    renderSections(latestSections, registeredSectionIds, currentCode);
    renderRegistrations(regList, latestSections);
  } catch {
    setMessage("Không kết nối được tới backend service. Kiểm tra URL hoặc trạng thái server.", true);
  }
}

function renderStudents(students) {
  const tbody = document.getElementById("studentsBody");
  tbody.innerHTML = "";

  if (!students.length) {
    tbody.innerHTML = `<tr><td colspan="4">Chưa có sinh viên nào.</td></tr>`;
    return;
  }

  students.forEach((st) => {
    const tr = document.createElement("tr");

    const tdCode = document.createElement("td");
    tdCode.textContent = st.student_code;

    const tdName = document.createElement("td");
    tdName.textContent = st.full_name;

    const tdMajor = document.createElement("td");
    tdMajor.textContent = st.major;

    const tdActions = document.createElement("td");
    const editBtn = document.createElement("button");
    editBtn.textContent = "Sửa";
    editBtn.onclick = () => openEditStudentForm(st);

    tdActions.appendChild(editBtn);
    tr.appendChild(tdCode);
    tr.appendChild(tdName);
    tr.appendChild(tdMajor);
    tr.appendChild(tdActions);
    tbody.appendChild(tr);
  });
}

async function addStudent() {
  const urls = getUrls();
  const student_code = document.getElementById("newStudentCode").value.trim();
  const full_name = document.getElementById("newStudentName").value.trim();
  const major = document.getElementById("newStudentMajor").value.trim();

  if (!student_code || !full_name || !major) {
    setMessage("Vui lòng nhập đầy đủ Mã SV, Họ tên và Ngành học.", true);
    return;
  }

  try {
    const res = await fetch(`${urls.student}/students`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ student_code, full_name, major }),
    });
    const data = await res.json();
    if (!res.ok) {
      setMessage(data.detail || "Thêm sinh viên thất bại.", true);
      return;
    }
    document.getElementById("newStudentCode").value = "";
    document.getElementById("newStudentName").value = "";
    document.getElementById("newStudentMajor").value = "";
    localStorage.setItem(STUDENT_STORAGE_KEY, data.student_code);
    localStorage.removeItem(PAGE_STORAGE_KEY);
    setMessage(`Đã thêm sinh viên ${data.student_code} - ${data.full_name}.`);
    loadAll();
  } catch {
    setMessage("Lỗi khi gọi Student Service.", true);
  }
}

async function updateStudent() {
  const urls = getUrls();
  const student_code = document.getElementById("editStudentCode").value.trim();
  const full_name = document.getElementById("editStudentName").value.trim();
  const major = document.getElementById("editStudentMajor").value.trim();

  if (!student_code || !full_name || !major) {
    setMessage("Vui lòng nhập đầy đủ Họ tên và Ngành học.", true);
    return;
  }

  try {
    const res = await fetch(`${urls.student}/students/${encodeURIComponent(student_code)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ full_name, major }),
    });
    const data = await res.json();
    if (!res.ok) {
      setMessage(data.detail || "Cập nhật sinh viên thất bại.", true);
      return;
    }
    closeEditStudentForm();
    localStorage.setItem(STUDENT_STORAGE_KEY, data.student_code);
    setMessage(`Đã cập nhật sinh viên ${data.student_code} - ${data.full_name}.`);
    loadAll();
  } catch {
    setMessage("Lỗi khi gọi Student Service.", true);
  }
}

async function addSection() {
  const urls = getUrls();
  const course_code = document.getElementById("newCourseCode").value.trim();
  const course_name = document.getElementById("newCourseName").value.trim();
  const credits = Number(document.getElementById("newCredits").value);
  const schedule = document.getElementById("newSchedule").value;
  const max_slots = Number(document.getElementById("newMaxSlots").value);

  if (!course_code || !course_name || !schedule) {
    setMessage("Vui lòng nhập đầy đủ Mã HP, Tên học phần và Lịch học.", true);
    return;
  }
  if (credits < 1 || credits > 4) {
    setMessage("Số tín chỉ chỉ được chọn từ 1 đến 4 TC.", true);
    return;
  }
  if (!Number.isInteger(max_slots) || max_slots < 1 || max_slots > 150) {
    setMessage("Sĩ số phải là số nguyên từ 1 đến tối đa 150.", true);
    return;
  }

  try {
    const res = await fetch(`${urls.course}/sections`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ course_code, course_name, credits, schedule, max_slots }),
    });
    const data = await res.json();
    if (!res.ok) {
      setMessage(data.detail || "Thêm học phần thất bại.", true);
      return;
    }
    document.getElementById("newCourseCode").value = "";
    document.getElementById("newCourseName").value = "";
    document.getElementById("newCredits").value = "3";
    document.getElementById("newMaxSlots").value = "30";
    toggleAddSectionForm(false);
    setMessage(`Đã thêm học phần ${data.course_code} - ${data.course_name}.`);
    loadAll();
  } catch {
    setMessage("Lỗi khi gọi Course Service.", true);
  }
}

async function deleteSection(sectionId) {
  const urls = getUrls();
  try {
    const res = await fetch(`${urls.course}/sections/${sectionId}`, { method: "DELETE" });
    const data = await res.json();
    if (!res.ok) {
      setMessage(data.detail || "Không thể xóa học phần.", true);
      return;
    }
    setMessage("Đã xóa học phần.");
    loadAll();
  } catch {
    setMessage("Lỗi khi xóa học phần.", true);
  }
}

function renderSections(sections, registeredIds, studentCode) {
  const tbody = document.getElementById("sectionsBody");
  tbody.innerHTML = "";

  if (!sections.length) {
    tbody.innerHTML = `<tr><td colspan="6">Chưa có lớp học phần nào.</td></tr>`;
    return;
  }

  sections.forEach((s) => {
    const isFull = s.enrolled_slots >= s.max_slots;
    const isRegistered = registeredIds.has(s.id);
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${s.course_code}</td>
      <td>${s.course_name}</td>
      <td>${s.credits}</td>
      <td>${s.schedule}</td>
      <td>${s.enrolled_slots}/${s.max_slots}</td>
      <td>
        <div class="actions">
          <button ${isFull || isRegistered || !studentCode ? "disabled" : ""} onclick="registerSection('${studentCode}', ${s.id})">
            ${isRegistered ? "Đã đăng ký" : isFull ? "Hết chỗ" : "Đăng ký"}
          </button>
          <button class="danger" onclick="deleteSection(${s.id})">Xóa</button>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function renderRegistrations(regs, sections = latestSections) {
  const tbody = document.getElementById("regsBody");
  tbody.innerHTML = "";

  if (!Array.isArray(regs) || !regs.length) {
    tbody.innerHTML = `<tr><td colspan="4">Chưa đăng ký học phần nào.</td></tr>`;
    return;
  }

  regs.forEach((r) => {
    const matched =
      sections.find((s) => {
        if (
          r.section_id !== undefined &&
          r.section_id !== null &&
          String(s.id) === String(r.section_id)
        ) {
          return true;
        }
        if (
          r.section_code &&
          (String(s.section_code || "") === String(r.section_code) ||
            String(s.course_code || "") === String(r.section_code))
        ) {
          return true;
        }
        return false;
      }) || {};

    const courseCode =
      r.course_code ||
      matched.course_code ||
      r.section_code ||
      (r.section_id ? `#${r.section_id}` : "—");
    const courseName = r.course_name || matched.course_name || "Chưa cập nhật";
    const schedule = r.schedule || matched.schedule || "—";

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${courseCode}</td>
      <td>${courseName}</td>
      <td>${schedule}</td>
      <td><button class="danger" onclick="cancelRegistration(${r.id})">Hủy</button></td>
    `;
    tbody.appendChild(tr);
  });
}

async function registerSection(studentCode, sectionId) {
  const urls = getUrls();
  const activeCode = studentCode || getActiveStudentCode();
  try {
    const res = await fetch(`${urls.reg}/registrations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ student_code: activeCode, section_id: sectionId }),
    });
    const data = await res.json();
    if (!res.ok) {
      setMessage(data.detail || "Đăng ký thất bại", true);
      return;
    }
    localStorage.setItem(STUDENT_STORAGE_KEY, activeCode);
    setMessage("Đăng ký học phần thành công!");
    loadAll();
  } catch {
    setMessage("Lỗi khi gửi yêu cầu đăng ký.", true);
  }
}

async function cancelRegistration(regId) {
  const urls = getUrls();
  const activeCode = getActiveStudentCode();
  try {
    const res = await fetch(`${urls.reg}/registrations/${regId}`, { method: "DELETE" });
    if (!res.ok) {
      setMessage("Hủy đăng ký thất bại.", true);
      return;
    }
    if (activeCode) {
      localStorage.setItem(STUDENT_STORAGE_KEY, activeCode);
    }
    setMessage("Đã hủy đăng ký học phần.");
    loadAll();
  } catch {
    setMessage("Lỗi khi hủy đăng ký.", true);
  }
}

loadAll();