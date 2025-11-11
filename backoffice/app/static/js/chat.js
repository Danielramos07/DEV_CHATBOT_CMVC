const TEXTO_RGPD = "Antes de iniciar a conversa, gostaria de informar que, de acordo com o Regulamento Geral de Proteção de Dados (RGPD), esta conversa está registada. Se não concordar com este registo, por favor utilize outro canal.";

function shadeColor(color, percent) {
  let R = parseInt(color.substring(1,3),16);
  let G = parseInt(color.substring(3,5),16);
  let B = parseInt(color.substring(5,7),16);
  R = Math.round(R * (100 + percent) / 100);
  G = Math.round(G * (100 + percent) / 100);
  B = Math.round(B * (100 + percent) / 100);
  R = (R < 255) ? R : 255;
  G = (G < 255) ? G : 255;
  B = (B < 255) ? B : 255;
  let RR = ((R.toString(16).length==1)?"0":"") + R.toString(16);
  let GG = ((G.toString(16).length==1)?"0":"") + G.toString(16);
  let BB = ((B.toString(16).length==1)?"0":"") + B.toString(16);
  return "#" + RR + GG + BB;
}

function atualizarCorChatbot() {
  const corBot = localStorage.getItem("corChatbot") || "#d4af37";
  const btnToggle = document.getElementById("chatToggleBtn");
  if (btnToggle) {
    btnToggle.style.backgroundColor = corBot;
  }
  const btnEnviar = document.querySelector(".chat-input button");
  if (btnEnviar) {
    btnEnviar.style.backgroundColor = corBot;
    btnEnviar.onmouseenter = () => btnEnviar.style.backgroundColor = shadeColor(corBot, 12);
    btnEnviar.onmouseleave = () => btnEnviar.style.backgroundColor = corBot;
  }
}

document.addEventListener("DOMContentLoaded", function() {
  atualizarCorChatbot();
});

function getIdiomaAtual() {
  return localStorage.getItem("idiomaAtivo") || "pt";
}

function formatarDataMensagem(date) {
  const meses = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
  ];
  const dia = String(date.getDate()).padStart(2, '0');
  const mes = meses[date.getMonth()];
  const ano = date.getFullYear();
  const horas = String(date.getHours()).padStart(2, '0');
  const minutos = String(date.getMinutes()).padStart(2, '0');
  return `${dia} de ${mes} de ${ano} ${horas}:${minutos}`;
}

function gerarDataHoraFormatada() {
  const agora = new Date();
  return agora.toLocaleDateString("pt-PT", {
      day: "2-digit",
      month: "long",
      year: "numeric"
    }) +
    " " +
    agora.toLocaleTimeString("pt-PT", {
      hour: "2-digit",
      minute: "2-digit"
    });
}

async function atualizarNomeChatHeader() {
  const headerNome = document.getElementById('chatHeaderNomeBot');
  const headerImg = document.querySelector('.chat-header-avatar');
  let nomeBot = localStorage.getItem("nomeBot") || "Assistente Municipal";
  let corBot = localStorage.getItem("corChatbot") || "#d4af37";
  let iconBot = localStorage.getItem("iconBot") || "/static/images/chatbot-icon.png";
  const chatbotId = parseInt(localStorage.getItem("chatbotAtivo"));
  if (chatbotId && !isNaN(chatbotId)) {
    try {
      const res = await fetch(`/chatbot/${chatbotId}`);
      const data = await res.json();
      if (data.success && data.nome) {
        nomeBot = data.nome;
        localStorage.setItem("nomeBot", nomeBot);
      }
      if (data.success && data.cor) {
        corBot = data.cor;
        localStorage.setItem("corChatbot", corBot);
      }
      if (data.success && data.icon) {
        iconBot = data.icon;
        localStorage.setItem("iconBot", iconBot);
        if (headerImg) {
          headerImg.src = iconBot;
        }
      }
    } catch (e) {
      const botsData = JSON.parse(localStorage.getItem("chatbotsData") || "[]");
      const bot = botsData.find(b => b.chatbot_id === chatbotId || b.chatbot_id === String(chatbotId));
      if (bot && bot.nome) {
        nomeBot = bot.nome;
        localStorage.setItem("nomeBot", nomeBot);
      }
      if (bot && bot.cor) {
        corBot = bot.cor;
        localStorage.setItem("corChatbot", corBot);
      }
      if (bot && bot.icon_path) {
        iconBot = bot.icon_path;
        localStorage.setItem("iconBot", iconBot);
        if (headerImg) {
          headerImg.src = iconBot;
        }
      }
    }
  }
  if (headerNome) {
    headerNome.textContent = nomeBot !== "..." ? nomeBot : "Assistente Municipal";
  }
  if (headerImg) {
    headerImg.src = iconBot;
  }
  const chatHeader = document.querySelector('.chat-header');
  if (chatHeader) {
    chatHeader.style.background = corBot;
  }
  atualizarFonteBadge();
  atualizarCorChatbot();
}

function atualizarFonteBadge() {
  const badgeDiv = document.getElementById("chatFonteBadge");
  const chatbotId = parseInt(localStorage.getItem("chatbotAtivo"));
  if (!badgeDiv) return;
  if (!chatbotId || isNaN(chatbotId)) {
    badgeDiv.innerHTML = "";
    return;
  }
  const fonte = localStorage.getItem(`fonteSelecionada_bot${chatbotId}`) || "faq";
  let badgeHTML = "";
  if (fonte === "faq" || fonte === "faiss") {
    badgeHTML = `
      <span style="display:inline-flex;align-items:center;gap:7px;font-weight:500;font-size:14px;color:#fff;border-radius:7px;padding:3px 7px 3px 2px;margin-top:4px;margin-left: 0px;">
        <img src="/static/images/imediato.png" alt="Imediato" style="width:18px;height:18px;object-fit:contain;">
        Respostas imediatas.
      </span>
    `;
  } else if (fonte === "faq+raga") {
    badgeHTML = `
      <span style="display:inline-flex;align-items:center;gap:7px;font-weight:500;font-size:14px;color:#fff;border-radius:7px;padding:3px 7px 3px 2px;margin-top:4px;margin-left:20px;">
        <img src="/static/images/ia.png" alt="IA" style="width:18px;height:18px;object-fit:contain;">
        Baseado em IA.
      </span>
    `;
  }
  badgeDiv.innerHTML = badgeHTML;
}

function criarBlocoFeedback(msgId) {
  return `
    <div class="feedback-icons" data-msg-id="${msgId}">
      <img src="/static/images/like.png" class="like-btn" title="Boa resposta" alt="Like">
      <img src="/static/images/dislike.png" class="dislike-btn" title="Má resposta" alt="Dislike">
      <span class="feedback-label" style="display:none;"></span>
    </div>
  `;
}

function isSaudacao(msg) {
  if (!msg) return false;
  const s = msg.trim().toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  const saudacoes = [
    "olá","ola","bom dia","boa tarde","boa noite","hello","hi","good morning","good afternoon","good evening"
  ];
  for (let saud of saudacoes) {
    if (s === saud || s.startsWith(saud)) return true;
  }
  return false;
}

function adicionarMensagem(tipo, texto, avatarUrl = null, autor = null, timestamp = null, isRgpd = false) {
  const chat = document.getElementById("chatBody");
  let wrapper = document.createElement("div");
  wrapper.className = `message-wrapper ${tipo}${isRgpd ? ' rgpd-wrapper' : ''}`;
  
  if (!isRgpd) {
    const authorDiv = document.createElement("div");
    authorDiv.className = "chat-author " + tipo;
    authorDiv.textContent = tipo === "user" ? "Eu" : (autor || "Assistente Municipal");
    wrapper.appendChild(authorDiv);
  }
  
  const messageContent = document.createElement("div");
  messageContent.className = "message-content";
  
  if (tipo === "bot" && avatarUrl && !isRgpd) {
    const avatarDiv = document.createElement("div");
    avatarDiv.className = "bot-avatar-outer";
    const avatar = document.createElement("img");
    avatar.src = avatarUrl;
    avatar.alt = "Bot";
    avatar.className = "bot-avatar";
    avatarDiv.appendChild(avatar);
    messageContent.appendChild(avatarDiv);
  }
  
  const bubbleCol = document.createElement("div");
  bubbleCol.style.display = "flex";
  bubbleCol.style.flexDirection = "column";
  bubbleCol.style.alignItems = tipo === "user" ? "flex-end" : "flex-start";
  
  const msgDiv = document.createElement("div");
  msgDiv.className = `message ${tipo}${isRgpd ? ' rgpd' : ''}`;
  msgDiv.style.whiteSpace = "pre-line";
  msgDiv.textContent = texto;
  
  let corBot = localStorage.getItem("corChatbot") || "#d4af37";
  if (tipo === "bot" && !isRgpd) {
    msgDiv.style.backgroundColor = corBot;
    msgDiv.style.color = "#fff";
  }
  if (tipo === "user" && !isRgpd) {
    msgDiv.style.backgroundColor = shadeColor(corBot, -18);
    msgDiv.style.color = "#fff";
  }
  
  bubbleCol.appendChild(msgDiv);
  
  if (!isRgpd && tipo === "bot" &&
    texto !== "Fico contente por ter ajudado." &&
    texto !== "Lamento não ter conseguido responder. Tente reformular a pergunta." &&
    texto !== "I'm glad I could help." &&
    texto !== "I'm sorry I couldn't answer. Please try rephrasing the question." &&
    !isSaudacao(texto)
  ) {
    const feedbackId = "feedback-" + Math.random().toString(36).substr(2, 9);
    const feedbackDiv = document.createElement("div");
    feedbackDiv.innerHTML = criarBlocoFeedback(feedbackId);
    bubbleCol.appendChild(feedbackDiv);
  }
  
  if (!isRgpd && !timestamp) timestamp = gerarDataHoraFormatada();
  if (!isRgpd) {
    const timestampDiv = document.createElement("div");
    timestampDiv.className = "chat-timestamp";
    timestampDiv.textContent = timestamp;
    bubbleCol.appendChild(timestampDiv);
  }
  
  messageContent.appendChild(bubbleCol);
  wrapper.appendChild(messageContent);
  chat.appendChild(wrapper);
  chat.scrollTop = chat.scrollHeight;
  
  if (!isRgpd) {
    setTimeout(() => {
      document.querySelectorAll('.feedback-icons').forEach(feedback => {
        if (!feedback.dataset.eventBound) {
          feedback.dataset.eventBound = true;
          const likeBtn = feedback.querySelector('.like-btn');
          const dislikeBtn = feedback.querySelector('.dislike-btn');
          const label = feedback.querySelector('.feedback-label');
          likeBtn.onclick = () => {
            if (label.nextElementSibling && label.nextElementSibling.classList.contains('feedback-badge')) {
              label.nextElementSibling.remove();
            }
            label.style.display = "none";
            const badge = document.createElement('div');
            badge.className = "feedback-badge positive";
            badge.innerHTML = `<div class="feedback-line"></div><div class="feedback-label-box">Boa resposta</div>`;
            label.parentNode.insertBefore(badge, label.nextSibling);
            likeBtn.classList.add('active');
            dislikeBtn.classList.remove('active');
          };
          dislikeBtn.onclick = () => {
            if (label.nextElementSibling && label.nextElementSibling.classList.contains('feedback-badge')) {
              label.nextElementSibling.remove();
            }
            label.style.display = "none";
            const badge = document.createElement('div');
            badge.className = "feedback-badge negative";
            badge.innerHTML = `<div class="feedback-line"></div><div class="feedback-label-box">Má resposta</div>`;
            label.parentNode.insertBefore(badge, label.nextSibling);
            dislikeBtn.classList.add('active');
            likeBtn.classList.remove('active');
          };
        }
      });
    }, 10);
  }
}

function adicionarFeedbackResolvido(onClick, idioma = "pt", isSaudacaoMsg = false) {
  if (isSaudacaoMsg) return;
  const chat = document.getElementById("chatBody");
  const wrapper = document.createElement("div");
  wrapper.className = "message-wrapper bot feedback-resolvido";
  const messageContent = document.createElement("div");
  messageContent.className = "message-content";
  const bubbleCol = document.createElement("div");
  bubbleCol.style.display = "flex";
  bubbleCol.style.flexDirection = "column";
  bubbleCol.style.alignItems = "flex-start";
  const msgDiv = document.createElement("div");
  msgDiv.className = "message bot";
  let corBot = localStorage.getItem("corChatbot") || "#d4af37";
  msgDiv.style.backgroundColor = corBot;
  msgDiv.style.color = "#fff";
  msgDiv.style.display = "flex";
  msgDiv.style.alignItems = "center";
  let textoPergunta = "A sua questão foi resolvida?";
  let btnSim = "Sim";
  let btnNao = "Não";
  if (idioma === "en") {
    textoPergunta = "Was your issue resolved?";
    btnSim = "Yes";
    btnNao = "No";
  }
  msgDiv.innerHTML = `
    <span style="font-weight: 500;">${textoPergunta}</span>
    <button class="btn-feedback-sim" style="margin-left:12px; margin-right:6px; background: #fff; color:${corBot}; border: 1.5px solid ${corBot}; border-radius: 6px; padding: 4px 14px; font-weight: 600; cursor:pointer; transition:0.18s;">${btnSim}</button>
    <button class="btn-feedback-nao" style="background: #fff; color:${corBot}; border: 1.5px solid ${corBot}; border-radius: 6px; padding: 4px 14px; font-weight: 600; cursor:pointer; transition:0.18s;">${btnNao}</button>
  `;
  bubbleCol.appendChild(msgDiv);
  messageContent.appendChild(bubbleCol);
  wrapper.appendChild(messageContent);
  chat.appendChild(wrapper);
  chat.scrollTop = chat.scrollHeight;
  setTimeout(() => {
    msgDiv.querySelector(".btn-feedback-sim").onclick = function() {
      if (typeof onClick === "function") onClick("sim", wrapper);
      wrapper.remove();
    };
    msgDiv.querySelector(".btn-feedback-nao").onclick = function() {
      if (typeof onClick === "function") onClick("nao", wrapper);
      wrapper.remove();
    };
  }, 60);
}

let autoMensagemTimeout = null;
let autoFecharTimeout = null;
let initialMessageShown = false;
function iniciarTimerAutoMensagem() {
  limparTimersAutoChat();
  autoMensagemTimeout = setTimeout(() => {
    enviarMensagemAutomatica();
  }, 30000);
}

function enviarMensagemAutomatica() {
  adicionarMensagem(
    "bot",
    "Se precisar de ajuda, basta escrever a sua pergunta!",
    localStorage.getItem("iconBot") || "images/chatbot-icon.png",
    localStorage.getItem("nomeBot") || "Assistente Municipal"
  );
  autoFecharTimeout = setTimeout(() => {
    fecharChat();
  }, 15000);
}

function limparTimersAutoChat() {
  if (autoMensagemTimeout) {
    clearTimeout(autoMensagemTimeout);
    autoMensagemTimeout = null;
  }
  if (autoFecharTimeout) {
    clearTimeout(autoFecharTimeout);
    autoFecharTimeout = null;
  }
}

function abrirChat() {
  document.getElementById('chatSidebar').style.display = 'flex';
  initialMessageShown = false;
  apresentarMensagemInicial();
  iniciarTimerAutoMensagem();
  atualizarCorChatbot();
  const toggleCard = document.querySelector('.chat-toggle-card');
  if (toggleCard) toggleCard.style.display = 'none';
}
window.fecharChat = function() {
  document.getElementById('chatSidebar').style.display = 'none';
  limparTimersAutoChat();
  initialMessageShown = false;
  const toggleCard = document.querySelector('.chat-toggle-card');
  if (toggleCard) toggleCard.style.display = '';
};

async function apresentarMensagemInicial() {
  if (initialMessageShown) return;
  
  let nomeBot, corBot, iconBot;
  const chatbotId = parseInt(localStorage.getItem("chatbotAtivo"));
  if (chatbotId && !isNaN(chatbotId)) {
    try {
      const res = await fetch(`/chatbot/${chatbotId}`);
      const data = await res.json();
      nomeBot = data.success && data.nome ? data.nome : "Assistente Municipal";
      corBot = data.success && data.cor ? data.cor : "#d4af37";
      iconBot = data.success && data.icon ? data.icon : "/static/images/chatbot-icon.png";
      localStorage.setItem("nomeBot", nomeBot);
      localStorage.setItem("corChatbot", corBot);
      localStorage.setItem("iconBot", iconBot);
    } catch (e) {
      const botsData = JSON.parse(localStorage.getItem("chatbotsData") || "[]");
      const bot = botsData.find(b => b.chatbot_id === chatbotId || b.chatbot_id === String(chatbotId));
      nomeBot = bot && bot.nome ? bot.nome : "Assistente Municipal";
      corBot = bot && bot.cor ? bot.cor : "#d4af37";
      iconBot = bot && bot.icon_path ? bot.icon_path : "/static/images/chatbot-icon.png";
      localStorage.setItem("nomeBot", nomeBot);
      localStorage.setItem("corChatbot", corBot);
      localStorage.setItem("iconBot", iconBot);
    }
  } else {
    nomeBot = "Assistente Municipal";
    corBot = "#d4af37";
    iconBot = "/static/images/chatbot-icon.png";
    localStorage.setItem("nomeBot", nomeBot);
    localStorage.setItem("corChatbot", corBot);
    localStorage.setItem("iconBot", iconBot);
  }
  atualizarCorChatbot();
  
  adicionarMensagem("bot", TEXTO_RGPD, null, null, null, true);

  const msg = `Olá!
Eu sou o ${nomeBot}, o seu assistente virtual.
Faça uma pergunta de cada vez que eu procurarei esclarecer todas as suas dúvidas.`;
  adicionarMensagem("bot", msg, iconBot, nomeBot);
  initialMessageShown = true;
  await atualizarNomeChatHeader();
  mostrarPerguntasSugestivasDB();
}

function enviarPergunta() {
  const input = document.getElementById("chatInput");
  const texto = input.value.trim();
  if (!texto) return;
  adicionarMensagem("user", texto);
  input.value = "";
  limparTimersAutoChat();
  iniciarTimerAutoMensagem();
  responderPergunta(texto);
}

function responderPergunta(pergunta) {
  const chatbotId = parseInt(localStorage.getItem("chatbotAtivo"));
  if (!chatbotId || isNaN(chatbotId)) {
    return adicionarMensagem(
      "bot",
      "⚠️ Nenhum chatbot está ativo. Por favor, selecione um chatbot ativo no menu de recursos.",
      localStorage.getItem("iconBot") || "images/chatbot-icon.png",
      localStorage.getItem("nomeBot") || "Assistente Municipal"
    );
  }
  if (window.awaitingRagConfirmation) {
    adicionarMensagem(
      "bot",
      "Por favor, utilize o link acima para confirmar se pretende pesquisar nos documentos PDF."
    );
    return;
  }
  const fonte = localStorage.getItem(`fonteSelecionada_bot${chatbotId}`) || "faq";
  const idioma = getIdiomaAtual();
  let corBot = localStorage.getItem("corChatbot") || "#d4af37";
  let iconBot = localStorage.getItem("iconBot") || "/static/images/chatbot-icon.png";
  fetch("/obter-resposta", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      pergunta,
      chatbot_id: chatbotId,
      fonte,
      idioma
    })
  })
    .then(res => res.json())
    .then(data => {
      let faqPergunta = data.pergunta_faq || pergunta;
      let faqIdioma = (data.faq_idioma || idioma || "pt").toLowerCase();
      if (data.success) {
        let resposta = data.resposta || "";
        if (data.documentos && Array.isArray(data.documentos) && data.documentos.length > 0) {
          resposta += `
            <div class="fonte-docs-wrapper" style="margin-top: 18px; display: flex; align-items: center; gap: 10px;">
              <span class="fonte-label" style="font-weight: 600; margin-right: 7px; color: #fff;">Fonte:</span>
              <a href="${data.documentos[0]}" target="_blank" rel="noopener" class="fonte-doc-link"
                 style="background: #fff; color: ${corBot}; border-radius: 7px; padding: 6px 18px; text-decoration: none; font-weight: 600; border: 1.5px solid ${corBot}; transition: all 0.18s; font-size: 15px; display: inline-flex; align-items: center; gap: 5px; cursor: pointer;"
                 onmouseover="this.style.background='${corBot}'; this.style.color='#fff'; this.style.borderColor='${corBot}';"
                 onmouseout="this.style.background='#fff'; this.style.color='${corBot}'; this.style.borderColor='${corBot}';"
                 title="Abrir fonte do documento em nova aba">
                <span>Link</span>
                <span style="font-size: 12px;">↗</span>
              </a>
            </div>
          `;
        }
        adicionarMensagemComHTML("bot", resposta, iconBot, localStorage.getItem("nomeBot"));
        const saudacao = isSaudacao(faqPergunta) || isSaudacao(resposta);
        adicionarFeedbackResolvido((respostaFeedback, bloco) => {
          if (respostaFeedback === "sim") {
            if (faqIdioma === "en") {
              adicionarMensagem(
                "bot",
                "I'm glad I could help.",
                iconBot,
                localStorage.getItem("nomeBot")
              );
            } else {
              adicionarMensagem(
                "bot",
                "Fico contente por ter ajudado.",
                iconBot,
                localStorage.getItem("nomeBot")
              );
            }
            obterPerguntasSemelhantes(faqPergunta, chatbotId, faqIdioma);
          } else if (respostaFeedback === "nao") {
            if (faqIdioma === "en") {
              adicionarMensagem(
                "bot",
                "I'm sorry I couldn't answer. Please try rephrasing the question.",
                iconBot,
                localStorage.getItem("nomeBot")
              );
            } else {
              adicionarMensagem(
                "bot",
                "Lamento não ter conseguido responder. Tente reformular a pergunta.",
                iconBot,
                localStorage.getItem("nomeBot")
              );
            }
            obterPerguntasSemelhantes(faqPergunta, chatbotId, faqIdioma);
          }
        }, faqIdioma, saudacao);
        window.awaitingRagConfirmation = false;
      }
      else if (
        data.prompt_rag ||
        (data.erro && data.erro.toLowerCase().includes("deseja tentar encontrar uma resposta nos documentos pdf"))
      ) {
        window.awaitingRagConfirmation = true;
        const chat = document.getElementById("chatBody");
        let wrapper = document.createElement("div");
        wrapper.className = "message-wrapper bot";
        const authorDiv = document.createElement("div");
        authorDiv.className = "chat-author bot";
        authorDiv.textContent = localStorage.getItem("nomeBot") || "Assistente Municipal";
        wrapper.appendChild(authorDiv);
        const messageContent = document.createElement("div");
        messageContent.className = "message-content";
        const bubbleCol = document.createElement("div");
        bubbleCol.style.display = "flex";
        bubbleCol.style.flexDirection = "column";
        bubbleCol.style.alignItems = "flex-start";
        const msgDiv = document.createElement("div");
        msgDiv.className = "message bot";
        msgDiv.style.whiteSpace = "pre-line";
        msgDiv.style.backgroundColor = corBot;
        msgDiv.style.color = "#fff";
        msgDiv.innerHTML = `Pergunta não encontrada nas FAQs.<br>
        <a id="confirmar-rag-link" href="#" style="
          color: #fff; background: ${corBot}; border: 2px solid #fff;
          border-radius: 8px; padding: 5px 17px; font-weight: bold;
          text-decoration: underline; display: inline-block; margin-top: 7px; cursor: pointer;"
        >Clique aqui para tentar encontrar uma resposta nos documentos PDF.</a>
        <br><span style="font-size:13px; opacity:.86;">Pode demorar alguns segundos.</span>`;
        bubbleCol.appendChild(msgDiv);
        const timestampDiv = document.createElement("div");
        timestampDiv.className = "chat-timestamp";
        timestampDiv.textContent = gerarDataHoraFormatada();
        bubbleCol.appendChild(timestampDiv);
        messageContent.appendChild(bubbleCol);
        wrapper.appendChild(messageContent);
        chat.appendChild(wrapper);
        chat.scrollTop = chat.scrollHeight;
        setTimeout(() => {
          const confirmarRag = document.getElementById("confirmar-rag-link");
          if (confirmarRag) {
            confirmarRag.onclick = function(e) {
              e.preventDefault();
              window.awaitingRagConfirmation = false;
              confirmarRag.style.pointerEvents = "none";
              confirmarRag.style.opacity = "0.6";
              confirmarRag.textContent = "A procurar nos documentos PDF...";
              fetch("/obter-resposta", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  pergunta,
                  chatbot_id: chatbotId,
                  fonte: "faq+raga",
                  feedback: "try_rag",
                  idioma
                })
              })
                .then(res => res.json())
                .then(ragData => {
                  if (ragData.success) {
                    adicionarMensagemComHTML("bot", ragData.resposta || "", iconBot, localStorage.getItem("nomeBot"));
                  } else {
                    adicionarMensagem(
                      "bot",
                      ragData.erro || "❌ Nenhuma resposta encontrada nos documentos PDF.",
                      iconBot,
                      localStorage.getItem("nomeBot")
                    );
                  }
                })
                .catch(() => {
                  adicionarMensagem(
                    "bot",
                    "❌ Erro ao comunicar com o servidor (RAG).",
                    iconBot,
                    localStorage.getItem("nomeBot")
                  );
                });
            };
          }
        }, 60);
      } else {
        adicionarMensagem(
          "bot",
          data.erro || "❌ Nenhuma resposta encontrada para a pergunta fornecida.",
          iconBot,
          localStorage.getItem("nomeBot")
        );
        window.awaitingRagConfirmation = false;
      }
    })
    .catch(() => {
      adicionarMensagem(
        "bot",
        "❌ Erro ao comunicar com o servidor. Verifique se o servidor está ativo.",
        iconBot,
        localStorage.getItem("nomeBot")
      );
      window.awaitingRagConfirmation = false;
    });
}

function adicionarMensagemComHTML(tipo, html, avatarUrl = null, autor = null, timestamp = null) {
  const chat = document.getElementById("chatBody");
  let wrapper = document.createElement("div");
  wrapper.className = "message-wrapper " + tipo;
  const authorDiv = document.createElement("div");
  authorDiv.className = "chat-author " + tipo;
  authorDiv.textContent = tipo === "user" ? "Eu" : (autor || "Assistente Municipal");
  wrapper.appendChild(authorDiv);
  const messageContent = document.createElement("div");
  messageContent.className = "message-content";
  if (tipo === "bot" && avatarUrl) {
    const avatarDiv = document.createElement("div");
    avatarDiv.className = "bot-avatar-outer";
    const avatar = document.createElement("img");
    avatar.src = avatarUrl;
    avatar.alt = "Bot";
    avatar.className = "bot-avatar";
    avatarDiv.appendChild(avatar);
    messageContent.appendChild(avatarDiv);
  }
  const bubbleCol = document.createElement("div");
  bubbleCol.style.display = "flex";
  bubbleCol.style.flexDirection = "column";
  bubbleCol.style.alignItems = tipo === "user" ? "flex-end" : "flex-start";
  const msgDiv = document.createElement("div");
  msgDiv.className = `message ${tipo}`;
  msgDiv.style.whiteSpace = "pre-line";
  msgDiv.innerHTML = html;
  let corBot = localStorage.getItem("corChatbot") || "#d4af37";
  if (tipo === "bot") {
    msgDiv.style.backgroundColor = corBot;
    msgDiv.style.color = "#fff";
  }
  if (tipo === "user") {
    msgDiv.style.backgroundColor = shadeColor(corBot, -18);
    msgDiv.style.color = "#fff";
  }
  bubbleCol.appendChild(msgDiv);
  if (
    tipo === "bot" &&
    html !== "Fico contente por ter ajudado." &&
    html !== "Lamento não ter conseguido responder. Tente reformular a pergunta." &&
    html !== "I'm glad I could help." &&
    html !== "I'm sorry I couldn't answer. Please try rephrasing the question." &&
    !isSaudacao(html)
  ) {
    const feedbackId = "feedback-" + Math.random().toString(36).substr(2, 9);
    const feedbackDiv = document.createElement("div");
    feedbackDiv.innerHTML = criarBlocoFeedback(feedbackId);
    bubbleCol.appendChild(feedbackDiv);
  }
  if (!timestamp) timestamp = gerarDataHoraFormatada();
  const timestampDiv = document.createElement("div");
  timestampDiv.className = "chat-timestamp";
  timestampDiv.textContent = timestamp;
  bubbleCol.appendChild(timestampDiv);
  messageContent.appendChild(bubbleCol);
  wrapper.appendChild(messageContent);
  chat.appendChild(wrapper);
  chat.scrollTop = chat.scrollHeight;
  setTimeout(() => {
    document.querySelectorAll('.feedback-icons').forEach(feedback => {
      if (!feedback.dataset.eventBound) {
        feedback.dataset.eventBound = true;
        const likeBtn = feedback.querySelector('.like-btn');
        const dislikeBtn = feedback.querySelector('.dislike-btn');
        const label = feedback.querySelector('.feedback-label');
        likeBtn.onclick = () => {
          label.textContent = "Boa resposta";
          label.style.color = "#388e3c";
          label.style.display = "inline-block";
          likeBtn.style.opacity = 1;
          dislikeBtn.style.opacity = 0.3;
        };
        dislikeBtn.onclick = () => {
          label.textContent = "Má resposta";
          label.style.color = "#d32f2f";
          label.style.display = "inline-block";
          dislikeBtn.style.opacity = 1;
          likeBtn.style.opacity = 0.3;
        };
      }
    });
  }, 10);
}

function obterPerguntasSemelhantes(perguntaOriginal, chatbotId, idioma = null) {
  if (!chatbotId || isNaN(chatbotId)) return;
  if (!idioma) idioma = getIdiomaAtual();
  fetch("/perguntas-semelhantes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      pergunta: perguntaOriginal,
      chatbot_id: chatbotId,
      idioma: idioma
    })
  })
    .then(res => res.json())
    .then(data => {
      document.querySelectorAll('.sugestoes-similares').forEach(el => el.remove());
      if (data.success && Array.isArray(data.sugestoes) && data.sugestoes.length > 0) {
        const chat = document.getElementById("chatBody");
        const sugestoesWrapper = document.createElement("div");
        sugestoesWrapper.className = "sugestoes-similares";
        sugestoesWrapper.style.marginTop = "10px";
        sugestoesWrapper.style.marginBottom = "8px";
        sugestoesWrapper.style.maxWidth = "540px";
        const titulo = document.createElement("div");
        titulo.className = "sugestoes-title";
        titulo.style.fontWeight = "600";
        titulo.style.fontSize = "15.5px";
        const corBot = localStorage.getItem("corChatbot") || "#d4af37";
        titulo.style.color = corBot;
        titulo.style.marginBottom = "7px";
        let sugestoesTitulo = "📌 Perguntas que também podem interessar:";
        if (idioma === "en") {
          sugestoesTitulo = "📌 Questions you might also be interested in:";
        }
        titulo.textContent = sugestoesTitulo;
        sugestoesWrapper.appendChild(titulo);
        const btnContainer = document.createElement("div");
        btnContainer.className = "suggested-questions-bar";
        data.sugestoes.forEach(pergunta => {
          const btn = document.createElement("button");
          btn.className = "suggested-question-btn";
          btn.textContent = pergunta;
          btn.style.background = "#fff";
          btn.style.borderColor = corBot;
          btn.style.color = corBot;
          btn.onmouseover = () => {
            btn.style.background = corBot;
            btn.style.color = "#fff";
          };
          btn.onmouseout = () => {
            btn.style.background = "#fff";
            btn.style.color = corBot;
          };
          btn.onclick = () => {
            adicionarMensagem("user", pergunta);
            responderPergunta(pergunta);
            sugestoesWrapper.remove();
          };
          btnContainer.appendChild(btn);
        });
        sugestoesWrapper.appendChild(btnContainer);
        chat.appendChild(sugestoesWrapper);
        chat.scrollTop = chat.scrollHeight;
      }
    })
    .catch(() => {});
}

async function mostrarPerguntasSugestivasDB() {
  const chat = document.getElementById("chatBody");
  if (!chat) return;
  const idioma = getIdiomaAtual();
  const chatbotId = parseInt(localStorage.getItem("chatbotAtivo"));
  if (!chatbotId || isNaN(chatbotId)) return;
  try {
    const res = await fetch("/faqs-aleatorias", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        idioma: idioma,
        n: 3,
        chatbot_id: chatbotId
      })
    });
    const data = await res.json();
    if (data.success && data.faqs && data.faqs.length > 0) {
      const title = document.createElement("div");
      title.className = "sugestoes-title";
      title.textContent = "Possíveis perguntas:";
      const corBot = localStorage.getItem("corChatbot") || "#d4af37";
      title.style.color = corBot;
      chat.appendChild(title);
      const btnContainer = document.createElement("div");
      btnContainer.className = "suggested-questions-bar";
      data.faqs.forEach(faq => {
        const btn = document.createElement("button");
        btn.className = "suggested-question-btn";
        btn.textContent = faq.pergunta;
        btn.style.background = corBot + "15";
        btn.style.borderColor = corBot;
        btn.style.color = corBot;
        btn.onmouseover = () => {
          btn.style.background = corBot;
          btn.style.color = "#fff";
        };
        btn.onmouseout = () => {
          btn.style.background = corBot + "15";
          btn.style.color = corBot;
        };
        btn.onclick = () => {
          adicionarMensagem("user", faq.pergunta);
          responderPergunta(faq.pergunta);
          btnContainer.remove();
          title.remove();
        };
        btnContainer.appendChild(btn);
      });
      chat.appendChild(btnContainer);
      chat.scrollTop = chat.scrollHeight;
    }
  } catch (e) {
  }
}

window.setIdiomaAtivo = function(idioma) {
  localStorage.setItem("idiomaAtivo", idioma);
};
window.apresentarMensagemInicial = apresentarMensagemInicial;
window.enviarPergunta = enviarPergunta;
window.responderPergunta = responderPergunta;
window.perguntarCategoria = function(){};
window.atualizarNomeChatHeader = atualizarNomeChatHeader;
window.atualizarFonteBadge = atualizarFonteBadge;