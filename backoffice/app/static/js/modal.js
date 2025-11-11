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