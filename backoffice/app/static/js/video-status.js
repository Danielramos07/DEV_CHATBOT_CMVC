async function atualizarIndicadorVideoJob() {
  const indicador = document.getElementById("indicadorVideoJob");
  const texto = document.getElementById("indicadorVideoJobTexto");
  const cancelBtn = document.getElementById("indicadorVideoJobCancelBtn");
  if (!indicador || !texto) return;

  try {
    const res = await fetch("/video/status");
    // Se o endpoint não existir neste contexto (ex.: página sem API montada),
    // parar o polling para não gerar spam/404 no console.
    if (res.status === 404 || res.status === 401 || res.status === 403) {
      indicador.style.display = "none";
      if (cancelBtn) cancelBtn.style.display = "none";
      if (window.__videoStatusPollIntervalId) {
        clearInterval(window.__videoStatusPollIntervalId);
        window.__videoStatusPollIntervalId = null;
      }
      return;
    }
    if (!res.ok) {
      indicador.style.display = "none";
      return;
    }
    const json = await res.json();
    const job = json.job || {};
    const status = job.status || "idle";

    if (status === "queued" || status === "processing") {
      indicador.style.display = "flex";
      const pct = typeof job.progress === "number" ? job.progress : 0;
      texto.textContent = job.message || "A gerar vídeo...";
      const barra = indicador.querySelector(".indicador-video-bar-inner");
      if (barra) barra.style.width = Math.max(5, Math.min(100, pct)) + "%";
      if (cancelBtn) cancelBtn.style.display = "inline-block";
      try {
        localStorage.setItem("videoJobPolling", "1");
      } catch (e) {}
    } else {
      indicador.style.display = "none";
      if (cancelBtn) cancelBtn.style.display = "none";
      // Se não há job ativo, parar o polling para não spammar o endpoint.
      if (typeof window.stopVideoStatusPolling === "function") {
        window.stopVideoStatusPolling();
      } else if (window.__videoStatusPollIntervalId) {
        clearInterval(window.__videoStatusPollIntervalId);
        window.__videoStatusPollIntervalId = null;
      }
      try {
        localStorage.removeItem("videoJobPolling");
      } catch (e) {}
    }
  } catch (e) {
    indicador.style.display = "none";
    if (cancelBtn) cancelBtn.style.display = "none";
  }
}

function startVideoStatusPolling() {
  // Evitar múltiplos intervals
  if (window.__videoStatusPollIntervalId) return;
  atualizarIndicadorVideoJob();
  window.__videoStatusPollIntervalId = setInterval(atualizarIndicadorVideoJob, 15000);
  try {
    localStorage.setItem("videoJobPolling", "1");
  } catch (e) {}
}

function stopVideoStatusPolling() {
  if (window.__videoStatusPollIntervalId) {
    clearInterval(window.__videoStatusPollIntervalId);
    window.__videoStatusPollIntervalId = null;
  }
  try {
    localStorage.removeItem("videoJobPolling");
  } catch (e) {}
}

function abrirModalCancelVideoJob(msg) {
  const modal = document.getElementById("modalCancelVideoJob");
  const msgEl = document.getElementById("modalCancelVideoJobMsg");
  if (msgEl && msg) msgEl.textContent = msg;
  if (modal) modal.style.display = "flex";
}

function fecharModalCancelVideoJob() {
  const modal = document.getElementById("modalCancelVideoJob");
  if (modal) modal.style.display = "none";
}

document.addEventListener("DOMContentLoaded", () => {
  // Por defeito NÃO fazer polling contínuo.
  // Fazemos 1 check inicial (caso tenha havido refresh durante um job).
  // Se o check indicar job ativo (ou se o UI marcou o flag), ligamos o interval.
  atualizarIndicadorVideoJob()
    .then(() => {
      try {
        if (localStorage.getItem("videoJobPolling") === "1") {
          startVideoStatusPolling();
        }
      } catch (e) {}
    })
    .catch(() => {});

  const cancelBtn = document.getElementById("indicadorVideoJobCancelBtn");
  const confirmarBtn = document.getElementById("btnConfirmarCancelVideoJob");
  let pendingDeleteChatbot = false;

  if (cancelBtn) {
    cancelBtn.addEventListener("click", async () => {
      try {
        const res = await fetch("/video/status");
        const json = await res.json();
        const job = (json && json.job) || {};
        const kind = job.kind;
        pendingDeleteChatbot = false;
        if (kind === "chatbot") {
          pendingDeleteChatbot = true;
          abrirModalCancelVideoJob(
            "Ao cancelar os vídeos (greeting + idle) este chatbot será eliminado. Confirmar?"
          );
        } else {
          abrirModalCancelVideoJob(
            "Cancelar a geração do vídeo desta FAQ? Isto irá eliminar os ficheiros temporários."
          );
        }
      } catch (e) {
        abrirModalCancelVideoJob("Cancelar geração do vídeo?");
      }
    });
  }

  if (confirmarBtn) {
    confirmarBtn.addEventListener("click", async () => {
      let cancelledKind = null;
      let cancelledChatbotId = null;
      try {
        const res = await fetch("/video/cancel", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ delete_chatbot: pendingDeleteChatbot }),
        });
        const json = await res.json().catch(() => ({}));
        if (json && json.success) {
          cancelledKind = json.kind || null;
          cancelledChatbotId = json.chatbot_id || null;
        }
      } catch (e) {}
      fecharModalCancelVideoJob();
      atualizarIndicadorVideoJob();

      // Se foi um cancel de chatbot (que o elimina), refrescar a página para refletir na lista.
      try {
        if (cancelledKind === "chatbot" && pendingDeleteChatbot) {
          window.location.reload();
          return;
        }
        // Se for FAQ, refrescar a tabela de FAQs se existir nesta página.
        if (cancelledKind === "faq") {
          if (typeof window.carregarTabelaFAQsBackoffice === "function") {
            window.carregarTabelaFAQsBackoffice();
          } else if (typeof window.mostrarRespostas === "function") {
            window.mostrarRespostas();
          }
        }
      } catch (e) {}
    });
  }

  // Close on overlay click
  const cancelModal = document.getElementById("modalCancelVideoJob");
  if (cancelModal) {
    cancelModal.addEventListener("click", (e) => {
      if (e.target === cancelModal) {
        fecharModalCancelVideoJob();
      }
    });
  }
});

window.fecharModalCancelVideoJob = fecharModalCancelVideoJob;
window.startVideoStatusPolling = startVideoStatusPolling;
window.stopVideoStatusPolling = stopVideoStatusPolling;
