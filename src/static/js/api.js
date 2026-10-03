"use strict";

const Api = (() => {
  async function request(path, options = {}) {
    const config = {
      method: options.method || "GET",
      credentials: "same-origin",
      headers: { Accept: "application/json", ...options.headers },
    };

    if (["POST", "PUT", "PATCH", "DELETE"].includes(config.method.toUpperCase())) {
      config.headers["Content-Type"] = "application/json";
    }
    if (options.body !== undefined) {
      config.body = JSON.stringify(options.body);
    }

    let response;
    try {
      response = await fetch(path, config);
    } catch {
      throw new Error("Não foi possível conectar ao servidor. Confira sua conexão e tente novamente.");
    }

    let body = {};
    if (response.status !== 204) {
      try {
        body = await response.json();
      } catch {
        if (response.ok) {
          throw new Error("O servidor retornou uma resposta inválida.");
        }
      }
    }

    if (!response.ok) {
      const error = new Error(body.erro?.mensagem || messageForStatus(response.status));
      error.status = response.status;
      error.fields = body.erro?.campos || {};
      error.code = body.erro?.codigo;
      throw error;
    }

    return body;
  }

  function messageForStatus(status) {
    const messages = {
      401: "Sua sessão expirou. Entre novamente para continuar.",
      404: "O item solicitado não foi encontrado.",
      422: "Confira os dados informados e tente novamente.",
    };
    return messages[status] || "Não foi possível concluir a solicitação. Tente novamente.";
  }

  return { request };
})();
