document.addEventListener('DOMContentLoaded', () => {
  const chatToggleBtn = document.getElementById('chatToggleBtn');
  const chatSidebar = document.getElementById('chatSidebar');
  const chatCloseBtn = document.querySelector('.chat-close-btn');

  if (chatToggleBtn) {
    chatToggleBtn.addEventListener('click', () => {
      chatSidebar.style.display = 'flex';
      chatToggleBtn.style.display = 'none';
      if (typeof abrirChat === "function") {
        abrirChat();
      }
    });
  }

  if (chatCloseBtn) {
    chatCloseBtn.addEventListener('click', fecharChat);
  }

  const footer = document.querySelector('footer.rodape');
  if (chatToggleBtn && footer) {
    function adjustChatBtn() {
      const footerRect = footer.getBoundingClientRect();
      const windowHeight = window.innerHeight;
      if (footerRect.top < windowHeight) {
        const overlap = windowHeight - footerRect.top + 32;
        chatToggleBtn.style.bottom = overlap + 'px';
      } else {
        chatToggleBtn.style.bottom = '32px';
      }
    }

    window.addEventListener('scroll', adjustChatBtn);
    window.addEventListener('resize', adjustChatBtn);
    adjustChatBtn();
  }
});

function fecharChat() {
  const chatSidebar = document.getElementById('chatSidebar');
  const chatToggleBtn = document.getElementById('chatToggleBtn');
  if (chatSidebar) {
    chatSidebar.style.display = 'none';
  }
  if (chatToggleBtn) {
    chatToggleBtn.style.display = 'flex';
  }
}