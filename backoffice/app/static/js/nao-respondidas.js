window.chatbotsMapNaoResp = {};
let perguntasNaoRespondidasCache = [];
let perguntaSelecionada = null;

async function carregarChatbotsNaoRespondidas() {
  try {
    const res = await fetch("/chatbots");
    const chatbots = await res.json();

    const filtroChatbot = document.getElementById("filtroChatbotNaoResp");
    if (filtroChatbot) {
      filtroChatbot.innerHTML =
        '<option value="">Todos os Chatbots</option>' +
        chatbots
          .map(
            (bot) =>
              `<option value="${String(bot.chatbot_id)}">${bot.nome}</option>`
          )
          .join("");
    }

    window.chatbotsMapNaoResp = {};
    chatbots.forEach((bot) => {
      window.chatbotsMapNaoResp[bot.chatbot_id] = bot.nome;
    });
  } catch (err) {
    console.error("❌ Erro ao carregar chatbots (não respondidas):", err);
  }
}

/**
 * Formata uma data ISO (string) para dd/mm/yyyy hh:mm.
 */
function formatarDataHoraISO(isoString) {
  if (!isoString) return "-";
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return isoString;

    const dia = String(d.getDate()).padStart(2, "0");
    const mes = String(d.getMonth() + 1).padStart(2, "0");
    const ano = d.getFullYear();
    const horas = String(d.getHours()).padStart(2, "0");
    const mins = String(d.getMinutes()).padStart(2, "0");

    return `${dia}/${mes}/${ano} ${horas}:${mins}`;
  } catch {
    return isoString;
  }
}

/**
 * Carrega as perguntas não respondidas do backend
 * e renderiza a tabela com filtros (chatbot, estado, pesquisa).
 */
async function carregarTabelaNaoRespondidas() {
  const lista = document.getElementById("listaNaoRespondidas");
  const titulo = document.getElementById("tituloNaoRespondidas");

  if (!lista) return;

  lista.innerHTML = "<p>A carregar perguntas não respondidas...</p>";
  if (titulo) titulo.textContent = "";

  const textoPesquisa = (
    document.getElementById("pesquisaNaoRespondida")?.value || ""
  )
    .toLowerCase()
    .trim();
  const filtroChatbot =
    document.getElementById("filtroChatbotNaoResp")?.value || "";
  const filtroEstado =
    document.getElementById("filtroEstadoNaoResp")?.value || "";

  try {
    const res = await fetch("/perguntas-nao-respondidas");
    const json = await res.json();

    // Se o backend devolver {success: false, erro: "..."}
    if (!Array.isArray(json)) {
      lista.innerHTML =
        "<p style='color:red;'>Erro ao carregar perguntas não respondidas.</p>";
      console.error("Resposta inesperada de /nao-respondidas:", json);
      return;
    }

    let perguntas = json;
    perguntasNaoRespondidasCache = perguntas;

    let filtradas = perguntas.filter((p) => {
      let okPesquisa = true;
      if (textoPesquisa) {
        const target = (p.pergunta || "") + " " + (p.fonte || "");
        okPesquisa = target.toLowerCase().includes(textoPesquisa);
      }

      let okChatbot = true;
      if (filtroChatbot) {
        okChatbot = String(p.chatbot_id) === String(filtroChatbot);
      }

      let okEstado = true;
      if (filtroEstado) {
        okEstado =
          (p.estado || "").toLowerCase() === filtroEstado.toLowerCase();
      }

      return okPesquisa && okChatbot && okEstado;
    });

    if (filtradas.length === 0) {
      lista.innerHTML =
        "<p>Não existem perguntas não respondidas para os filtros selecionados.</p>";
      if (titulo) titulo.textContent = "0 perguntas encontradas.";
      return;
    }

    if (titulo) {
      const total = filtradas.length;
      const pendentes = filtradas.filter(
        (p) => (p.estado || "").toLowerCase() === "pendente"
      ).length;
      titulo.textContent = `${total} pergunta${
        total > 1 ? "s" : ""
      } no total (${pendentes} pendente${pendentes === 1 ? "" : "s"}).`;
    }

    const chatbotsMap = window.chatbotsMapNaoResp || {};

    lista.innerHTML = `
      <table class="faq-tabela-backoffice">
        <thead>
          <tr>
            <th>Chatbot</th>
            <th>Pergunta</th>
            <th>Fonte</th>
            <th>Estado</th>
            <th>Criada em</th>
            <th>Ações</th>
          </tr>
        </thead>
        <tbody>
          ${filtradas
            .map((p) => {
              const nomeBot = chatbotsMap[p.chatbot_id] || "-";
              const fonte = p.fonte || "-";
              const score =
                typeof p.max_score === "number" ? p.max_score.toFixed(2) : "-";
              const estado = (p.estado || "pendente").toLowerCase();
              let estadoLabel = estado;

              if (estado === "pendente") {
                estadoLabel = '<span style="color:#cc8c00;">Pendente</span>';
              } else if (estado === "tratada") {
                estadoLabel = '<span style="color:green;">Tratada</span>';
              } else if (estado === "ignorada") {
                estadoLabel = '<span style="color:#999;">Ignorada</span>';
              }

              const criadoEm = formatarDataHoraISO(p.criado_em);

              return `
              <tr>
                <td>${nomeBot}</td>
                <td>${p.pergunta || "-"}</td>
                <td>${fonte}</td>
                <td style="text-align:center;">${estadoLabel}</td>
                <td>${criadoEm || "-"}</td>
                <td>
                  <button class="btn-remover" onclick="removerPergunta(${
                    p.id
                  })">Remover</button>
                  <button class="btn-editar" onclick="abrirModalTratarPergunta(${
                    p.id
                  })">Editar</button>
                </td>
              </tr>
            `;
            })
            .join("")}
        </tbody>
      </table>
    `;
  } catch (err) {
    console.error(" Erro ao carregar perguntas não respondidas:", err);
    lista.innerHTML =
      "<p style='color:red;'>Erro ao carregar perguntas não respondidas.</p>";
  }
}

function abrirModalTratarPergunta(perguntaId) {
  const modal = document.getElementById("modalTratarPergunta");
  const textoEl = document.getElementById("perguntaSelecionadaTexto");
  const selectAcao = document.getElementById("acaoPergunta");

  if (!modal || !textoEl || !selectAcao) return;

  perguntaSelecionada = perguntasNaoRespondidasCache.find(
    (p) => String(p.id) === String(perguntaId)
  );

  if (!perguntaSelecionada) {
    console.error("Pergunta não encontrada no cache", perguntaId);
    return;
  }

  textoEl.textContent = perguntaSelecionada.pergunta || "";
  selectAcao.value = "criar_faq";
  modal.style.display = "flex";
}

async function confirmarTratarPergunta() {
  const modal = document.getElementById("modalTratarPergunta");
  const selectAcao = document.getElementById("acaoPergunta");
  if (!perguntaSelecionada || !selectAcao) return;

  const acao = selectAcao.value;

  if (acao === "marcar_tratada" || acao === "marcar_ignorada") {
    const novoEstado = acao === "marcar_tratada" ? "tratada" : "ignorada";
    const res = await fetch(
      `/perguntas-nao-respondidas/${perguntaSelecionada.id}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ estado: novoEstado }),
      }
    );
    const json = await res.json();
    if (json.success) {
      if (modal) modal.style.display = "none";
      perguntaSelecionada = null;
      carregarTabelaNaoRespondidas();
    }
  } else if (acao === "criar_faq") {
    // Guardar a pergunta para futura criação de FAQ na página de respostas
    localStorage.setItem(
      "perguntaParaNovaFAQ",
      perguntaSelecionada.pergunta || ""
    );
    window.location.href = "/respostas";
  }
}

async function removerPergunta(perguntaId) {
  const res = await fetch(`/perguntas-nao-respondidas/${perguntaId}`, {
    method: "DELETE",
  });
  const json = await res.json();
  if (json.success) {
    carregarTabelaNaoRespondidas();
  }
}

window.carregarChatbotsNaoRespondidas = carregarChatbotsNaoRespondidas;
window.carregarTabelaNaoRespondidas = carregarTabelaNaoRespondidas;

document.addEventListener("DOMContentLoaded", () => {
  carregarChatbotsNaoRespondidas().then(() => {
    carregarTabelaNaoRespondidas();
  });

  const pesquisaInput = document.getElementById("pesquisaNaoRespondida");
  const filtroChatbot = document.getElementById("filtroChatbotNaoResp");
  const filtroEstado = document.getElementById("filtroEstadoNaoResp");

  if (pesquisaInput)
    pesquisaInput.addEventListener("input", carregarTabelaNaoRespondidas);
  if (filtroChatbot)
    filtroChatbot.addEventListener("change", carregarTabelaNaoRespondidas);
  if (filtroEstado)
    filtroEstado.addEventListener("change", carregarTabelaNaoRespondidas);

  const btnConfirmar = document.getElementById("confirmarTratarPergunta");
  const btnCancelar = document.getElementById("cancelarTratarPergunta");
  const modal = document.getElementById("modalTratarPergunta");

  if (btnConfirmar) btnConfirmar.onclick = confirmarTratarPergunta;
  if (btnCancelar && modal)
    btnCancelar.onclick = function () {
      modal.style.display = "none";
      perguntaSelecionada = null;
    };
});
