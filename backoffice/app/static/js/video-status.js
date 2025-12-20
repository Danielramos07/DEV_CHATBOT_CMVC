async function atualizarIndicadorVideoJob() {
  const indicador = document.getElementById("indicadorVideoJob");
  const texto = document.getElementById("indicadorVideoJobTexto");
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
    } else {
      indicador.style.display = "none";
    }
  } catch (e) {
    indicador.style.display = "none";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  // Atualizar logo no início e depois de 5 em 5 segundos
  atualizarIndicadorVideoJob();
  setInterval(atualizarIndicadorVideoJob, 5000);
});
