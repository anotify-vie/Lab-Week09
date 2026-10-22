const API = "/api/v1";
const $ = (selector) => document.querySelector(selector);
let token = sessionStorage.getItem("token");
let user = null;
let heroes = [];
let teams = [];
let editingId = null;

function message(text, error = false) {
  $("#message").textContent = text;
  $("#message").dataset.error = String(error);
}

function resetEditor() {
  editingId = null;
  $("#hero-form").reset();
  $("#editor-title").textContent = "Tạo hero của bạn";
  $("#editor-hint").textContent = "Đăng nhập để tạo hero. Bạn có thể sửa hoặc xóa hero của mình.";
  $("#save-hero").textContent = "Tạo hero";
  $("#secret-name").required = true;
  $("#cancel-edit").hidden = true;
}

function renderAccount() {
  $("#account-status").textContent = user
    ? `Logged in as ${user.username} · ${user.role === "admin" ? "Quản trị viên" : "Thành viên"}`
    : "Chưa đăng nhập";
  $("#auth-forms").hidden = Boolean(user);
  $("#logout").hidden = !user;
  $("#hero-fields").disabled = !user;
  $("#team-panel").hidden = user?.role !== "admin";
  renderHeroes();
}

function logout() {
  token = null;
  user = null;
  sessionStorage.removeItem("token");
  resetEditor();
  renderAccount();
}

async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers },
  });
  if (response.status === 401) {
    logout();
    throw new Error(path === "/token" ? "Tên đăng nhập hoặc mật khẩu không đúng." : "Vui lòng đăng nhập lại. Phiên có thể đã hết hạn.");
  }
  if (response.status === 403) throw new Error("Bạn không có quyền thực hiện thao tác này.");
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = Array.isArray(body.detail) ? body.detail.map((item) => item.msg).join("; ") : body.detail;
    throw new Error(detail || `Yêu cầu thất bại (${response.status}).`);
  }
  return response.status === 204 ? null : response.json();
}

function write(method, body) {
  return { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
}

function canEdit(hero) {
  return user && (user.role === "admin" || hero.owner_id === user.id);
}

function renderHeroes() {
  const tbody = $("#heroes");
  tbody.replaceChildren();
  $("#hero-count").textContent = heroes.length ? `${heroes.length} hero (tối đa 100 mỗi lần tải)` : "Chưa có hero nào.";
  for (const hero of heroes) {
    const row = document.createElement("tr");
    const values = [hero.name, hero.age ?? "—", teams.find((team) => team.id === hero.team_id)?.name ?? "—", hero.power ?? "—", hero.status === "active" ? "Đang hoạt động" : "Đã nghỉ"];
    for (const value of values) {
      const cell = document.createElement("td");
      // Treat API values as text so hero names cannot inject HTML/scripts.
      cell.textContent = String(value);
      row.append(cell);
    }
    const cell = document.createElement("td");
    if (canEdit(hero)) {
      const actions = document.createElement("div");
      actions.className = "actions";
      const edit = document.createElement("button");
      edit.type = "button";
      edit.className = "secondary";
      edit.textContent = "Sửa";
      edit.addEventListener("click", () => editHero(hero));
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "danger";
      remove.textContent = "Xóa";
      remove.addEventListener("click", async () => {
        if (!confirm(`Xóa hero “${hero.name}”?`)) return;
        try {
          await request(`/heroes/${hero.id}`, { method: "DELETE" });
          if (editingId === hero.id) resetEditor();
          await refresh();
          message("Đã xóa hero.");
        } catch (error) { message(error.message, true); }
      });
      actions.append(edit, remove);
      cell.append(actions);
    } else cell.textContent = "—";
    row.append(cell);
    tbody.append(row);
  }
}

function editHero(hero) {
  resetEditor();
  editingId = hero.id;
  const form = $("#hero-form");
  for (const name of ["name", "age", "team_id", "power", "status"]) form.elements[name].value = hero[name] ?? "";
  $("#secret-name").required = false;
  $("#editor-title").textContent = `Chỉnh sửa ${hero.name}`;
  $("#save-hero").textContent = "Lưu thay đổi";
  $("#cancel-edit").hidden = false;
  $("#editor-hint").textContent = "Để trống danh tính bí mật nếu bạn muốn giữ giá trị hiện tại.";
  form.scrollIntoView({ behavior: "smooth", block: "center" });
}

async function refresh() {
  [heroes, teams] = await Promise.all([request("/heroes?limit=100"), request("/teams")]);
  const select = $("#hero-team");
  const previous = select.value;
  select.replaceChildren(new Option("Không có biệt đội", ""));
  for (const team of teams) select.append(new Option(team.name, String(team.id)));
  select.value = previous;
  renderHeroes();
}

$("#login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const result = await request("/token", { method: "POST", body: new URLSearchParams(new FormData(event.target)) });
    token = result.access_token;
    sessionStorage.setItem("token", token);
    user = await request("/me");
    event.target.reset();
    renderAccount();
    await refresh();
    message("Đăng nhập thành công.");
  } catch (error) { message(error.message, true); }
});

$("#register-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const body = Object.fromEntries(new FormData(event.target));
  if (new TextEncoder().encode(body.password).length > 72) {
    message("Mật khẩu vượt quá 72 byte UTF-8.", true);
    return;
  }
  try {
    await request("/register", write("POST", body));
    $("#login-form").elements.username.value = body.username;
    event.target.reset();
    message("Đã tạo tài khoản. Bạn có thể đăng nhập ngay.");
  } catch (error) { message(error.message, true); }
});

$("#hero-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const body = Object.fromEntries(new FormData(event.target));
  body.age = body.age === "" ? null : Number(body.age);
  body.team_id = body.team_id === "" ? null : Number(body.team_id);
  body.power = body.power || null;
  if (editingId && !body.secret_name) delete body.secret_name;
  try {
    await request(editingId ? `/heroes/${editingId}` : "/heroes", write(editingId ? "PATCH" : "POST", body));
    resetEditor();
    await refresh();
    message("Đã lưu hero.");
  } catch (error) { message(error.message, true); }
});

$("#team-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await request("/teams", write("POST", Object.fromEntries(new FormData(event.target))));
    event.target.reset();
    await refresh();
    message("Đã tạo biệt đội.");
  } catch (error) { message(error.message, true); }
});

$("#logout").addEventListener("click", () => { logout(); message("Đã đăng xuất."); });
$("#cancel-edit").addEventListener("click", resetEditor);
$("#refresh").addEventListener("click", () => refresh().catch((error) => message(error.message, true)));

async function start() {
  renderAccount();
  if (token) {
    try { user = await request("/me"); renderAccount(); }
    catch (error) { message(error.message, true); }
  }
  try { await refresh(); }
  catch (error) { message(error.message, true); }
}
start();
