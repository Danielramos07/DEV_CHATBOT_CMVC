function fecharModalNovoBot() {
  document.getElementById("modalNovoBot").style.display = "none";
}

document.addEventListener("DOMContentLoaded", () => {
  const novoBotBtn = document.getElementById("novoBotBtn");
  const modalNovoBot = document.getElementById("modalNovoBot");
  const novoBotForm = document.getElementById("novoBotForm");
  const mensagemNovoBot = document.getElementById("mensagemNovoBot");

  if (!novoBotBtn || !modalNovoBot || !novoBotForm || !mensagemNovoBot) {
    return;
  }

  novoBotBtn.addEventListener("click", () => {
    modalNovoBot.style.display = "flex";
    mensagemNovoBot.textContent = "";
  });

  modalNovoBot.addEventListener("click", (e) => {
    if (e.target === modalNovoBot) fecharModalNovoBot();
  });

  novoBotForm.addEventListener("submit", function (e) {
    e.preventDefault();
    mensagemNovoBot.textContent = "";

    const fd = new FormData();
    fd.append("nome", (this.nome?.value || "").trim());
    fd.append("descricao", (this.descricao?.value || "").trim());
    fd.append("genero", this.genero ? this.genero.value : "");
    fd.append(
      "mensagem_sem_resposta",
      this.mensagem_sem_resposta ? this.mensagem_sem_resposta.value.trim() : ""
    );
    fd.append("cor", this.cor ? this.cor.value : "#d4af37");
    fd.append(
      "video_enabled",
      this.video_enabled && this.video_enabled.checked ? "true" : "false"
    );
    const iconInput = this.querySelector('input[type="file"][name="icon"]');
    if (iconInput && iconInput.files && iconInput.files.length > 0) {
      fd.append("icon", iconInput.files[0]);
    }

    fetch("/chatbots", {
      method: "POST",
      body: fd,
    })
      .then((r) => r.json())
      .then((resp) => {
        if (resp.success) {
          mensagemNovoBot.style.color = "green";
          mensagemNovoBot.textContent = "Chatbot criado com sucesso!";
          if (resp.video_busy && typeof mostrarModalVideoBusy === "function") {
            mostrarModalVideoBusy(
              "O chatbot foi criado, mas já existe um vídeo a ser gerado neste momento. Os vídeos (greeting + idle) vão ter de ser gerados mais tarde."
            );
          }
          // Se o backend começou (ou vai começar) a geração dos vídeos do chatbot, ligar o polling do indicador.
          if (resp.video_queued || resp.video_processing || resp.video_started) {
            try {
              localStorage.setItem("videoJobPolling", "1");
            } catch (e) {}
            if (typeof window.startVideoStatusPolling === "function") {
              window.startVideoStatusPolling();
            }
          } else {
            // fallback: se o utilizador marcou "gerar vídeo" no form, ligar polling (evita perda do indicador)
            try {
              const ve =
                this.video_enabled && this.video_enabled.checked ? true : false;
              if (ve) {
                localStorage.setItem("videoJobPolling", "1");
                if (typeof window.startVideoStatusPolling === "function") {
                  window.startVideoStatusPolling();
                }
              }
            } catch (e) {}
          }
          setTimeout(() => {
            fecharModalNovoBot();
            window.location.reload();
          }, 1200);
        } else {
          mensagemNovoBot.style.color = "red";
          mensagemNovoBot.textContent = resp.error || "Erro ao criar chatbot.";
        }
      })
      .catch(() => {
        mensagemNovoBot.style.color = "red";
        mensagemNovoBot.textContent = "Erro de comunicação com o servidor.";
      });
  });
});
