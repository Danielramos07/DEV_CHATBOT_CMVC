window.chatbotSelecionado = null;
window.fonteSelecionada = "faq";

window.getUrlParam = function (key) {
  try {
    return new URLSearchParams(window.location.search).get(key);
  } catch {
    return null;
  }
};

window.setUrlParam = function (key, value) {
  try {
    const url = new URL(window.location.href);
    if (value === null || value === undefined || String(value).trim() === "") {
      url.searchParams.delete(key);
    } else {
      url.searchParams.set(key, String(value));
    }
    window.history.replaceState({}, "", url.toString());
  } catch {
    // ignore
  }
};

window.getActiveChatbotId = function () {
  const raw = window.getUrlParam("chatbot_id");
  const id = raw ? parseInt(raw, 10) : NaN;
  return Number.isFinite(id) ? id : null;
};

window.setActiveChatbotId = function (chatbotId) {
  window.setUrlParam("chatbot_id", chatbotId);
};

window.getFonteSelecionada = function () {
  const fonte = window.getUrlParam("fonte");
  return (fonte || "faq").toLowerCase();
};

window.setFonteSelecionada = function (fonte) {
  window.setUrlParam("fonte", fonte);
  window.fonteSelecionada = (fonte || "faq").toLowerCase();
};
