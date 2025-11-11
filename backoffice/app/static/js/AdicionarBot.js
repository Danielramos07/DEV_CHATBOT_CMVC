function fecharModalNovoBot() {
  document.getElementById("modalNovoBot").style.display = "none";
}

document.addEventListener("DOMContentLoaded", () => {
  const novoBotBtn = document.getElementById("novoBotBtn");
  const modalNovoBot = document.getElementById("modalNovoBot");
  const novoBotForm = document.getElementById("novoBotForm");
  const mensagemNovoBot = document.getElementById("mensagemNovoBot");

  novoBotBtn.addEventListener("click", () => {
    modalNovoBot.style.display = "flex";
    mensagemNovoBot.textContent = "";
  });

  modalNovoBot.addEventListener("click", (e) => {
    if (e.target === modalNovoBot) fecharModalNovoBot();
  });

  novoBotForm.addEventListener("submit", function(e) {
    e.preventDefault();
    mensagemNovoBot.textContent = "";

    const nome = this.nome.value.trim();
    const descricao = this.descricao.value.trim();

    const data = {
      nome,
      descricao
    };

    fetch("/chatbots", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    })
    .then(r => r.json())
    .then(resp => {
      if (resp.success) {
        mensagemNovoBot.style.color = "green";
        mensagemNovoBot.textContent = "Chatbot criado com sucesso!";
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