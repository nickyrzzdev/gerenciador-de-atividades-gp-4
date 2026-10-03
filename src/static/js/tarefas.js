"use strict";

const taskState = {
  items: [],
  filtered: [],
  page: 1,
  perPage: 8,
  user: null,
  toastTimer: null,
};

const taskList = document.getElementById("task-list");
const taskDialog = document.getElementById("task-dialog");
const taskForm = document.getElementById("task-form");
const statusLabels = {
  a_fazer: "Pendente",
  em_andamento: "Em andamento",
  concluida: "Concluída",
};

function initials(name) {
  const words = name.trim().split(/\s+/).filter(Boolean);
  if (!words.length) return "?";
  return words.length === 1
    ? words[0].slice(0, 2).toUpperCase()
    : `${words[0][0]}${words[words.length - 1][0]}`.toUpperCase();
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[character]);
}

function isOverdue(task) {
  return task.status !== "concluida" && task.prazo && new Date(task.prazo) < new Date();
}

function formatDeadline(value) {
  if (!value) return "Sem prazo";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Prazo informado";
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "short",
    year: date.getFullYear() === new Date().getFullYear() ? undefined : "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date).replace(".", "");
}

function formatToday() {
  return new Intl.DateTimeFormat("pt-BR", {
    weekday: "long",
    day: "numeric",
    month: "long",
  }).format(new Date());
}

function showToast(message, kind = "success") {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.className = `toast is-visible ${kind === "error" ? "toast-error" : ""}`;
  window.clearTimeout(taskState.toastTimer);
  taskState.toastTimer = window.setTimeout(() => {
    toast.classList.remove("is-visible");
  }, 3600);
}

function showFormMessage(message, text, kind = "error") {
  message.textContent = text;
  message.classList.toggle("is-success", kind === "success");
  message.classList.toggle("is-visible", Boolean(text));
}

function showFieldErrors(form, fields = {}) {
  form.querySelectorAll("[data-error-for]").forEach((element) => {
    const text = fields[element.dataset.errorFor] || "";
    element.textContent = text;
    element.classList.toggle("is-visible", Boolean(text));
  });
}

async function loadAllTasks() {
  const tasks = [];
  let page = 1;
  let totalPages = 1;
  do {
    const response = await Api.request(`/api/tarefas?pagina=${page}&por_pagina=50`);
    tasks.push(...response.itens);
    totalPages = response.paginacao.total_paginas;
    page += 1;
  } while (page <= totalPages);
  taskState.items = tasks;
  renderTasks();
}

function updateSummary() {
  const count = { a_fazer: 0, em_andamento: 0, concluida: 0 };
  for (const task of taskState.items) {
    if (Object.hasOwn(count, task.status)) count[task.status] += 1;
  }
  document.getElementById("count-pending").textContent = count.a_fazer;
  document.getElementById("count-progress").textContent = count.em_andamento;
  document.getElementById("count-done").textContent = count.concluida;
}

function taskCard(task) {
  const overdue = isOverdue(task);
  const completed = task.status === "concluida";
  const status = overdue ? "Atrasada" : statusLabels[task.status] || "Pendente";
  const statusClass = overdue ? "overdue" : task.status;
  const nextAction = completed
    ? `<button class="task-action action-reopen" type="button" data-task-action="reopen" data-task-id="${task.id}">Reabrir</button>`
    : task.status === "a_fazer"
      ? `<button class="task-action action-start" type="button" data-task-action="start" data-task-id="${task.id}">Iniciar</button><button class="task-action action-complete" type="button" data-task-action="complete" data-task-id="${task.id}" aria-label="Concluir tarefa">✓</button>`
      : `<button class="task-action action-complete" type="button" data-task-action="complete" data-task-id="${task.id}">Concluir</button><button class="task-action action-reset" type="button" data-task-action="reset" data-task-id="${task.id}" aria-label="Mover para pendentes">↶</button>`;
  const description = task.descricao
    ? `<p class="task-description">${escapeHtml(task.descricao)}</p>`
    : `<p class="task-description task-no-description">Sem descrição</p>`;

  return `
    <article class="task-card ${completed ? "is-completed" : ""}" data-task-card="${task.id}">
      <button class="task-check ${completed ? "is-checked" : ""}" type="button" data-task-action="${completed ? "reopen" : "complete"}" data-task-id="${task.id}" aria-label="${completed ? "Reabrir tarefa" : "Marcar tarefa como concluída"}">${completed ? "✓" : ""}</button>
      <div class="task-main">
        <div class="task-title-row"><h3>${escapeHtml(task.titulo)}</h3><span class="status-pill status-${statusClass}"><span class="status-dot"></span>${status}</span></div>
        ${description}
        <div class="task-meta">
          <span class="deadline ${overdue ? "deadline-overdue" : ""}">
            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="3.5" y="5" width="17" height="16" rx="2" stroke="currentColor" stroke-width="1.7"/><path d="M7 3v4m10-4v4M4 9h16" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>
            ${escapeHtml(formatDeadline(task.prazo))}
          </span>
        </div>
      </div>
      <div class="task-actions">
        ${nextAction}
        <button class="icon-button task-edit" type="button" data-task-action="edit" data-task-id="${task.id}" aria-label="Editar ${escapeHtml(task.titulo)}" title="Editar tarefa">
          <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="m14 6 4 4M4 20l4-.8L19 8a2.8 2.8 0 0 0-4-4L4 15l-.8 5Z" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </button>
        <button class="icon-button task-delete" type="button" data-task-action="delete" data-task-id="${task.id}" aria-label="Excluir ${escapeHtml(task.titulo)}" title="Excluir tarefa">
          <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M4 7h16m-10 4v6m4-6v6M6 7l1 14h10l1-14M9 7V4h6v3" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </button>
      </div>
    </article>`;
}

function filterTasks() {
  const query = document.getElementById("task-search").value.trim().toLocaleLowerCase("pt-BR");
  const status = document.getElementById("status-filter").value;
  taskState.filtered = taskState.items.filter((task) => {
    const matchesQuery = !query
      || task.titulo.toLocaleLowerCase("pt-BR").includes(query)
      || (task.descricao || "").toLocaleLowerCase("pt-BR").includes(query);
    const matchesStatus = status === "todas"
      || (status === "atrasada" ? Boolean(isOverdue(task)) : task.status === status);
    return matchesQuery && matchesStatus;
  });
}

function renderEmptyState() {
  const hasAnyTasks = taskState.items.length > 0;
  const title = hasAnyTasks ? "Nenhuma tarefa encontrada" : "Seu espaço está prontinho";
  const message = hasAnyTasks
    ? "Tente mudar a busca ou o filtro para encontrar uma tarefa."
    : "Que tal começar adicionando uma tarefa? Seu próximo passo pode ser pequeno.";
  const action = hasAnyTasks
    ? ""
    : `<button class="button button-primary" type="button" data-open-new-task><svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 5v14m-7-7h14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg> Criar minha primeira tarefa</button>`;
  taskList.innerHTML = `
    <div class="empty-state">
      <div class="empty-art" aria-hidden="true"><span class="empty-sparkle sparkle-left">✦</span><span class="empty-sparkle sparkle-right">✧</span><div class="empty-paper"><span class="empty-paper-check">✓</span><i></i><i></i><i></i></div></div>
      <h3>${title}</h3><p>${message}</p>${action}
    </div>`;
}

function renderTasks() {
  updateSummary();
  filterTasks();
  const total = taskState.filtered.length;
  const pages = Math.max(1, Math.ceil(total / taskState.perPage));
  taskState.page = Math.min(taskState.page, pages);
  const start = (taskState.page - 1) * taskState.perPage;
  const visible = taskState.filtered.slice(start, start + taskState.perPage);
  document.getElementById("task-result-count").textContent =
    `${total} ${total === 1 ? "tarefa encontrada" : "tarefas encontradas"}`;

  if (!visible.length) {
    renderEmptyState();
    document.getElementById("pagination").hidden = true;
    return;
  }

  taskList.innerHTML = visible.map(taskCard).join("");
  const pagination = document.getElementById("pagination");
  pagination.hidden = total <= taskState.perPage;
  document.getElementById("pagination-summary").textContent =
    `Mostrando ${start + 1}–${Math.min(start + taskState.perPage, total)} de ${total}`;
  document.getElementById("page-number").textContent = `${taskState.page} / ${pages}`;
  document.getElementById("previous-page").disabled = taskState.page <= 1;
  document.getElementById("next-page").disabled = taskState.page >= pages;
}

function openTaskDialog() {
  taskForm.reset();
  document.getElementById("task-id").value = "";
  document.getElementById("dialog-title").textContent = "Nova tarefa";
  document.getElementById("save-task-button").querySelector("span").textContent = "Salvar tarefa";
  showFieldErrors(taskForm);
  showFormMessage(document.getElementById("task-form-message"), "");
  taskDialog.showModal();
  window.setTimeout(() => document.getElementById("task-title").focus(), 50);
}

async function openEditDialog(taskId) {
  try {
    const response = await Api.request(`/api/tarefas/${taskId}`);
    const task = response.tarefa;
    taskForm.reset();
    document.getElementById("task-id").value = task.id;
    document.getElementById("task-title").value = task.titulo;
    document.getElementById("task-description").value = task.descricao || "";
    document.getElementById("task-deadline").value = task.prazo
      ? task.prazo.replace(" ", "T").slice(0, 16)
      : "";
    document.getElementById("dialog-title").textContent = "Editar tarefa";
    document.getElementById("save-task-button").querySelector("span").textContent = "Salvar alterações";
    showFieldErrors(taskForm);
    showFormMessage(document.getElementById("task-form-message"), "");
    taskDialog.showModal();
    window.setTimeout(() => document.getElementById("task-title").focus(), 50);
  } catch (error) {
    if (error.status === 401) {
      window.location.assign("/login");
      return;
    }
    showToast(error.message, "error");
  }
}

function taskPayload() {
  const rawDeadline = document.getElementById("task-deadline").value;
  return {
    titulo: document.getElementById("task-title").value.trim(),
    descricao: document.getElementById("task-description").value.trim() || null,
    prazo: rawDeadline ? rawDeadline.replace("T", " ") : "",
  };
}

async function saveTask(event) {
  event.preventDefault();
  const message = document.getElementById("task-form-message");
  showFormMessage(message, "");
  showFieldErrors(taskForm);
  if (!taskForm.reportValidity()) return;

  const id = document.getElementById("task-id").value;
  const button = document.getElementById("save-task-button");
  button.disabled = true;
  button.querySelector("span").textContent = id ? "Salvando..." : "Criando...";
  try {
    await Api.request(id ? `/api/tarefas/${id}` : "/api/tarefas", {
      method: id ? "PUT" : "POST",
      body: taskPayload(),
    });
    taskDialog.close();
    await loadAllTasks();
    showToast(id ? "Tarefa atualizada com sucesso." : "Tarefa criada com sucesso.");
  } catch (error) {
    if (error.status === 401) {
      window.location.assign("/login");
      return;
    }
    showFieldErrors(taskForm, error.fields);
    showFormMessage(message, error.message);
  } finally {
    button.disabled = false;
    button.querySelector("span").textContent = id ? "Salvar alterações" : "Salvar tarefa";
  }
}

async function updateTaskStatus(taskId, status) {
  const task = taskState.items.find((item) => item.id === taskId);
  if (!task) return;
  try {
    await Api.request(`/api/tarefas/${taskId}/status`, {
      method: "PATCH",
      body: { status },
    });
    await loadAllTasks();
    const message = status === "concluida"
      ? "Tarefa concluída. Muito bem!"
      : status === "em_andamento"
        ? "Tarefa movida para em andamento."
        : "Tarefa reaberta.";
    showToast(message);
  } catch (error) {
    if (error.status === 401) {
      window.location.assign("/login");
      return;
    }
    showToast(error.message, "error");
  }
}

async function deleteTask(taskId) {
  const task = taskState.items.find((item) => item.id === taskId);
  if (!task || !window.confirm(`Excluir a tarefa “${task.titulo}”? Esta ação não pode ser desfeita.`)) return;
  try {
    await Api.request(`/api/tarefas/${taskId}`, { method: "DELETE" });
    await loadAllTasks();
    showToast("Tarefa excluída.");
  } catch (error) {
    if (error.status === 401) {
      window.location.assign("/login");
      return;
    }
    showToast(error.message, "error");
  }
}

async function loadUser() {
  const response = await Api.request("/api/auth/me");
  taskState.user = response.usuario;
  const name = response.usuario.nome;
  document.getElementById("user-name").textContent = name;
  document.getElementById("user-email").textContent = response.usuario.email;
  document.getElementById("user-avatar").textContent = initials(name);
  document.getElementById("welcome-name").textContent = name.split(/\s+/)[0].toLocaleUpperCase("pt-BR");
}

document.getElementById("today-label").textContent = formatToday();
document.getElementById("new-task-button").addEventListener("click", openTaskDialog);
document.getElementById("task-search").addEventListener("input", () => {
  taskState.page = 1;
  renderTasks();
});
document.getElementById("status-filter").addEventListener("change", () => {
  taskState.page = 1;
  renderTasks();
});
document.getElementById("refresh-button").addEventListener("click", async () => {
  try {
    await loadAllTasks();
    showToast("Sua lista está atualizada.");
  } catch (error) {
    showToast(error.message, "error");
  }
});
document.getElementById("previous-page").addEventListener("click", () => {
  taskState.page -= 1;
  renderTasks();
});
document.getElementById("next-page").addEventListener("click", () => {
  taskState.page += 1;
  renderTasks();
});
document.getElementById("close-dialog-button").addEventListener("click", () => taskDialog.close());
document.getElementById("cancel-dialog-button").addEventListener("click", () => taskDialog.close());
taskDialog.addEventListener("click", (event) => {
  if (event.target === taskDialog) taskDialog.close();
});
taskForm.addEventListener("submit", saveTask);
taskForm.querySelectorAll("input, textarea").forEach((field) => {
  field.addEventListener("input", () => {
    const error = taskForm.querySelector(`[data-error-for="${field.name}"]`);
    if (error) {
      error.textContent = "";
      error.classList.remove("is-visible");
    }
  });
});
taskList.addEventListener("click", (event) => {
  const createButton = event.target.closest("[data-open-new-task]");
  if (createButton) {
    openTaskDialog();
    return;
  }
  const button = event.target.closest("[data-task-action]");
  if (!button) return;
  const taskId = Number(button.dataset.taskId);
  const action = button.dataset.taskAction;
  if (action === "complete") updateTaskStatus(taskId, "concluida");
  if (action === "reopen") updateTaskStatus(taskId, "a_fazer");
  if (action === "start") updateTaskStatus(taskId, "em_andamento");
  if (action === "reset") updateTaskStatus(taskId, "a_fazer");
  if (action === "edit") openEditDialog(taskId);
  if (action === "delete") deleteTask(taskId);
});
document.getElementById("logout-button").addEventListener("click", async () => {
  const button = document.getElementById("logout-button");
  button.disabled = true;
  try {
    await Api.request("/api/auth/logout", { method: "POST", body: {} });
    window.location.assign("/login");
  } catch (error) {
    button.disabled = false;
    showToast(error.message, "error");
  }
});
document.getElementById("mobile-menu-button").addEventListener("click", (event) => {
  const expanded = event.currentTarget.getAttribute("aria-expanded") === "true";
  event.currentTarget.setAttribute("aria-expanded", String(!expanded));
  document.getElementById("sidebar").classList.toggle("is-open", !expanded);
});
document.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
    event.preventDefault();
    document.getElementById("task-search").focus();
  }
});

(async () => {
  taskList.setAttribute("aria-busy", "true");
  try {
    await loadUser();
    await loadAllTasks();
  } catch (error) {
    if (error.status === 401) {
      window.location.assign("/login");
      return;
    }
    taskList.setAttribute("aria-busy", "false");
    taskList.innerHTML = `<div class="load-error"><p>${escapeHtml(error.message)}</p><button class="button button-secondary" id="retry-load" type="button">Tentar novamente</button></div>`;
    document.getElementById("retry-load").addEventListener("click", () => window.location.reload());
  } finally {
    taskList.setAttribute("aria-busy", "false");
  }
})();
