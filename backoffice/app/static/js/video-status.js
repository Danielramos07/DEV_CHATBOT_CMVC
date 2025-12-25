async function atualizarIndicadorVideoJob() {
  const indicador = document.getElementById("indicadorVideoJob");
  const texto = document.getElementById("indicadorVideoJobTexto");
  const cancelBtn = document.getElementById("indicadorVideoJobCancelBtn");
  if (!indicador || !texto) return;

  try {
    const res = await fetch("/video/status");
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
    } else {
      indicador.style.display = "none";
      if (cancelBtn) cancelBtn.style.display = "none";
    }
  } catch (e) {
    indicador.style.display = "none";
    if (cancelBtn) cancelBtn.style.display = "none";
  }
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
  // Atualizar logo no início e depois de 5 em 5 segundos
  atualizarIndicadorVideoJob();
  setInterval(atualizarIndicadorVideoJob, 5000);

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
