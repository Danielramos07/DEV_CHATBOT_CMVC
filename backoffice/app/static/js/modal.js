let faqIdAEliminar = null;

function pedirConfirmacao(id) {
  faqIdAEliminar = id;
  const modal = document.getElementById("modalConfirmacao");
  if (modal) modal.style.display = "flex";
}

function fecharModalConfirmacao() {
  const modal = document.getElementById("modalConfirmacao");
  if (modal) modal.style.display = "none";
}

document.addEventListener("DOMContentLoaded", () => {
  const confirmarBtn = document.getElementById("confirmarEliminacao");
  const cancelarBtn = document.getElementById("cancelarEliminacao");

  if (confirmarBtn) {
    confirmarBtn.addEventListener("click", () => {
      if (typeof eliminarFAQ === "function" && faqIdAEliminar !== null) {
        eliminarFAQ(faqIdAEliminar); 
      }
      fecharModalConfirmacao();
    });
  }

  if (cancelarBtn) {
    cancelarBtn.addEventListener("click", fecharModalConfirmacao);
  }
});

window.pedirConfirmacao = pedirConfirmacao;
window.fecharModalConfirmacao = fecharModalConfirmacao;

function mostrarModalVideoBusy(msg) {
  const modal = document.getElementById("modalVideoBusy");
  const msgEl = document.getElementById("modalVideoBusyMsg");
  if (msgEl && msg) msgEl.textContent = msg;
  if (modal) modal.style.display = "flex";
}

function fecharModalVideoBusy() {
  const modal = document.getElementById("modalVideoBusy");
  if (modal) modal.style.display = "none";
}

window.mostrarModalVideoBusy = mostrarModalVideoBusy;
window.fecharModalVideoBusy = fecharModalVideoBusy;