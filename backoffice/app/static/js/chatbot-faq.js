function adicionarListenersFormulariosFAQ(allBots = []) {
  document.querySelectorAll(".faqForm").forEach(form => {
    form.onsubmit = null;
  });

  document.querySelectorAll(".faqForm").forEach(form => {
    form.onsubmit = async function(event) {
      event.preventDefault();
      const data = {};
      new FormData(form).forEach((value, key) => data[key] = value);

      data.idioma = data.idioma?.trim() || "pt";
      const msgDiv = form.querySelector("#mensagemFAQ") || document.getElementById("mensagemFAQ");

      if (!data.idioma) {
        if (msgDiv) msgDiv.innerHTML = `<span style="color:#dc2626;">Tem de escolher um idioma.</span>`;
        return;
      }

      if (!data.chatbot_id) {
        if (msgDiv) msgDiv.innerHTML = `<span style="color:#dc2626;">Tem de escolher um chatbot.</span>`;
        return;
      }

      if (data.chatbot_id === "todos") {
        try {
          const bots = allBots.length > 0 ? allBots : (await (await fetch("/chatbots")).json());
          let sucesso = 0, erro = 0;
          for (const bot of bots) {
            const dataCopia = { ...data, chatbot_id: bot.chatbot_id };
            const res = await fetch("/faqs", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(dataCopia)
            });
            if (res.ok) sucesso++; else erro++;
          }
          form.reset();
          if (msgDiv) msgDiv.innerHTML = `<span style="color:#2ecc40;">FAQ adicionada a ${sucesso} chatbot(s)${erro > 0 ? ` (${erro} falharam)` : ""}!</span>`;
        } catch (err) {
          if (msgDiv) msgDiv.innerHTML = `<span style="color:#dc2626;">Erro ao inserir FAQs em todos os chatbots.</span>`;
        }
      } else {
        try {
          const res = await fetch("/faqs", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
          });
          if (res.ok) {
            form.reset();
            if (msgDiv) msgDiv.innerHTML = `<span style="color:#2ecc40;">FAQ adicionada com sucesso!</span>`;
          } else {
            const resultado = await res.json().catch(() => ({}));
            const erro = resultado.error || resultado.erro || await res.text();
            if (msgDiv) msgDiv.innerHTML = `<span style="color:#dc2626;">Erro ao adicionar FAQ: ${erro}</span>`;
          }
        } catch (err) {
          if (msgDiv) msgDiv.innerHTML = `<span style="color:#dc2626;">Erro de ligação ao servidor!</span>`;
        }
      }
    };
  });
}

function adicionarListenersUploadDocx(allBots = []) {
  document.querySelectorAll(".uploadForm").forEach(form => {
    form.onsubmit = null;
  });

  document.querySelectorAll(".uploadForm").forEach(form => {
    form.onsubmit = async function(event) {
      event.preventDefault();
      const chatbotId = form.querySelector('[name="chatbot_id"]').value;
      const idioma = form.querySelector('[name="idioma"]')?.value?.trim() || "pt";
      const fileInput = form.querySelector('input[type="file"]');
      const statusDiv = form.querySelector(".uploadStatus") || document.getElementById("mensagemAdicionarFAQ");

      if (!chatbotId || !fileInput || !fileInput.files.length || !idioma) {
        if (statusDiv) statusDiv.innerHTML = "Tem de escolher um chatbot, um ficheiro e um idioma!";
        return;
      }

      if (chatbotId === "todos") {
        try {
          const bots = allBots.length > 0 ? allBots : (await (await fetch("/chatbots")).json());
          let sucesso = 0, erro = 0;
          for (const bot of bots) {
            const formDataBot = new FormData();
            formDataBot.append("chatbot_id", bot.chatbot_id);
            formDataBot.append("idioma", idioma);
            for (let f = 0; f < fileInput.files.length; f++) {
              formDataBot.append("files", fileInput.files[f]);
            }
            const res = await fetch("/upload-faq-docx-multiplos", {
              method: "POST",
              body: formDataBot
            });
            if (res.ok) sucesso++; else erro++;
          }
          form.reset();
          if (statusDiv) {
            statusDiv.innerHTML = `Documento(s) carregado(s) em ${sucesso} chatbot(s)${erro > 0 ? ` (${erro} falharam)` : ""}!`;
            statusDiv.style.color = "#2ecc40";
          }
        } catch (err) {
          if (statusDiv) {
            statusDiv.innerHTML = "Erro ao carregar documento(s) em todos os chatbots!";
            statusDiv.style.color = "#dc2626";
          }
        }
      } else {
        try {
          const formData = new FormData(form);
          formData.set("idioma", idioma);
          const res = await fetch("/upload-faq-docx-multiplos", {
            method: "POST",
            body: formData
          });
          if (res.ok) {
            form.reset();
            if (statusDiv) {
              statusDiv.innerHTML = "Documento(s) carregado(s) com sucesso!";
              statusDiv.style.color = "#2ecc40";
            }
          } else {
            const resultado = await res.json().catch(() => ({}));
            const erro = resultado.error || resultado.erro || await res.text();
            if (statusDiv) {
              statusDiv.innerHTML = "Erro ao carregar: " + erro;
              statusDiv.style.color = "#dc2626";
            }
          }
        } catch (err) {
          if (statusDiv) {
            statusDiv.innerHTML = "Erro de ligação ao servidor!";
            statusDiv.style.color = "#dc2626";
          }
        }
      }
    };
  });
}

window.adicionarListenersFormulariosFAQ = adicionarListenersFormulariosFAQ;
window.adicionarListenersUploadDocx = adicionarListenersUploadDocx;