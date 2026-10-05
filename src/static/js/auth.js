"use strict";

document.querySelectorAll("[data-password-toggle]").forEach((button) => {
  button.addEventListener("click", () => {
    const input = document.getElementById(button.dataset.passwordToggle);
    const visible = input.type === "password";
    input.type = visible ? "text" : "password";
    button.setAttribute("aria-pressed", String(visible));
    button.setAttribute("aria-label", visible ? "Ocultar senha" : "Mostrar senha");
  });
});

function showFormMessage(element, message, kind = "error") {
  element.textContent = message;
  element.classList.toggle("is-success", kind === "success");
  element.classList.toggle("is-visible", Boolean(message));
}

function showFieldErrors(form, fields = {}) {
  form.querySelectorAll("[data-error-for]").forEach((element) => {
    const message = fields[element.dataset.errorFor] || "";
    element.textContent = message;
    element.classList.toggle("is-visible", Boolean(message));
  });
}

function setFormBusy(form, busy, idleText) {
  const button = form.querySelector('button[type="submit"]');
  button.disabled = busy;
  button.querySelector("span").textContent = busy ? "Aguarde..." : idleText;
}

const loginForm = document.getElementById("login-form");
if (loginForm) {
  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = document.getElementById("login-message");
    showFormMessage(message, "");
    if (!loginForm.reportValidity()) return;

    setFormBusy(loginForm, true, "Entrar");
    try {
      await Api.request("/api/auth/login", {
        method: "POST",
        body: {
          email: loginForm.elements.email.value.trim(),
          senha: loginForm.elements.senha.value,
          lembrar: document.getElementById("login-remember").checked,
        },
      });
      await Api.request("/api/auth/me");
      window.location.assign("/tarefas");
    } catch (error) {
      showFormMessage(message, error.message);
      setFormBusy(loginForm, false, "Entrar");
    }
  });
}

const signupForm = document.getElementById("signup-form");
if (signupForm) {
  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = document.getElementById("signup-message");
    showFormMessage(message, "");
    showFieldErrors(signupForm);
    if (!signupForm.reportValidity()) return;

    const password = signupForm.elements.senha.value;
    const confirmPassword = signupForm.elements.confirmar_senha.value;
    const clientErrors = {};
    if (password.length < 8 || !/[A-Z]/.test(password) || !/\d/.test(password)) {
      clientErrors.senha = "Use 8 caracteres ou mais, com uma letra maiúscula e um número.";
    }
    if (password !== confirmPassword) {
      clientErrors.confirmar_senha = "As senhas não conferem.";
    }
    if (Object.keys(clientErrors).length) {
      showFieldErrors(signupForm, clientErrors);
      return;
    }

    setFormBusy(signupForm, true, "Criar conta");
    try {
      await Api.request("/api/auth/cadastro", {
        method: "POST",
        body: {
          nome: signupForm.elements.nome.value.trim(),
          email: signupForm.elements.email.value.trim(),
          senha: password,
          confirmar_senha: confirmPassword,
          perfil: "individual",
        },
      });
      window.location.assign("/login?cadastro=sucesso");
    } catch (error) {
      showFieldErrors(signupForm, error.fields);
      showFormMessage(message, error.message);
      setFormBusy(signupForm, false, "Criar conta");
    }
  });
}

if (window.location.pathname === "/login" && new URLSearchParams(window.location.search).get("cadastro") === "sucesso") {
  const message = document.getElementById("login-message");
  if (message) showFormMessage(message, "Conta criada com sucesso. Agora você já pode entrar.", "success");
}
