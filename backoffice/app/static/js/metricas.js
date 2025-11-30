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

async function carregarMetricasNaoRespondidas() {
  const tabelaDiv = document.getElementById("tabelaMetricas");
  if (!tabelaDiv) return;
  tabelaDiv.innerHTML = "<p>A carregar métricas...</p>";

  try {
    const res = await fetch("/perguntas-nao-respondidas/metricas");
    const json = await res.json();

    if (!json.success || !Array.isArray(json.metricas)) {
      tabelaDiv.innerHTML =
        "<p style='color:red;'>Erro ao carregar métricas de perguntas não respondidas.</p>";
      console.error("Resposta inesperada de /perguntas-nao-respondidas/metricas:", json);
      return;
    }

    const metricas = json.metricas;

    const total = metricas.reduce((acc, m) => acc + (m.total || 0), 0);
    const pendentes = metricas.reduce((acc, m) => acc + (m.pendentes || 0), 0);
    const tratadas = metricas.reduce((acc, m) => acc + (m.tratadas || 0), 0);
    const ignoradas = metricas.reduce((acc, m) => acc + (m.ignoradas || 0), 0);

    const resumoTotal = document.getElementById("resumoTotal");
    const resumoPendentes = document.getElementById("resumoPendentes");
    const resumoTratadas = document.getElementById("resumoTratadas");
    const resumoIgnoradas = document.getElementById("resumoIgnoradas");

    if (resumoTotal) resumoTotal.textContent = total;
    if (resumoPendentes) resumoPendentes.textContent = pendentes;
    if (resumoTratadas) resumoTratadas.textContent = tratadas;
    if (resumoIgnoradas) resumoIgnoradas.textContent = ignoradas;

    if (metricas.length === 0) {
      tabelaDiv.innerHTML = "<p>Não existem métricas de perguntas não respondidas.</p>";
      return;
    }

    tabelaDiv.innerHTML = `
      <table class="faq-tabela-backoffice">
        <thead>
          <tr>
            <th>Chatbot</th>
            <th>Total</th>
            <th>Pendentes</th>
            <th>Tratadas</th>
            <th>Ignoradas</th>
            <th>Última pergunta</th>
          </tr>
        </thead>
        <tbody>
          ${metricas
            .map((m) => {
              const nome = m.nome || `Chatbot ${m.chatbot_id}`;
              const ultima = formatarDataHoraISO(m.ultimo_registo);
              return `
                <tr>
                  <td>${nome}</td>
                  <td>${m.total || 0}</td>
                  <td>${m.pendentes || 0}</td>
                  <td>${m.tratadas || 0}</td>
                  <td>${m.ignoradas || 0}</td>
                  <td>${ultima}</td>
                </tr>
              `;
            })
            .join("")}
        </tbody>
      </table>
    `;
  } catch (err) {
    console.error("Erro ao carregar métricas de perguntas não respondidas:", err);
    tabelaDiv.innerHTML =
      "<p style='color:red;'>Erro ao carregar métricas de perguntas não respondidas.</p>";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  carregarMetricasNaoRespondidas();
});
