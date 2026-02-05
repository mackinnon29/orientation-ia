/**
 * Point d'entrée principal de l'application
 */
document.addEventListener('DOMContentLoaded', () => {
    const startBtn = document.getElementById('start-btn');
    const heroSection = document.getElementById('hero-section');
    const chatSection = document.getElementById('chat-section');
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');

    // Transition vers le chat
    startBtn.addEventListener('click', () => {
        heroSection.classList.add('hidden');
        chatSection.classList.remove('hidden');

        // Message de bienvenue initial
        setTimeout(() => {
            addMessage("Bonjour ! Je suis votre assistant d'orientation propulsé par Gemini. Pour commencer, parlez-moi un peu de vous : qu'allez-vous aimer faire durant une journée de travail idéale ?", 'ai');
        }, 500);
    });

    // Envoi de message
    const handleSend = async () => {
        const text = userInput.value.trim();
        if (text) {
            addMessage(text, 'user');
            userInput.value = '';

            // Simulation de chargement
            const loadingMsg = addLoadingIndicator();

            try {
                // Appel au service IA (Mock pour l'instant)
                const response = await MockAiService.getResponse(text);
                removeLoadingIndicator(loadingMsg);
                addMessage(response, 'ai');
            } catch (error) {
                removeLoadingIndicator(loadingMsg);
                addMessage("Désolé, j'ai rencontré une petite erreur de connexion. Pouvez-vous répéter ?", 'ai');
                console.error(error);
            }
        }
    };

    sendBtn.addEventListener('click', handleSend);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSend();
    });

    /**
     * Ajoute un indicateur de chargement
     */
    function addLoadingIndicator() {
        const msgDiv = document.createElement('div');
        msgDiv.classList.add('message', 'ai', 'loading');
        msgDiv.innerHTML = '<span>.</span><span>.</span><span>.</span>';
        chatMessages.appendChild(msgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return msgDiv;
    }

    /**
     * Supprime l'indicateur de chargement
     */
    function removeLoadingIndicator(el) {
        if (el && el.parentNode) {
            el.parentNode.removeChild(el);
        }
    }

    /**
     * Ajoute un message à l'interface
     * @param {string} text - Contenu du message
     * @param {'user'|'ai'} sender - Expéditeur
     */
    function addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender);
        messageDiv.textContent = text;
        chatMessages.appendChild(messageDiv);

        // Scroll automatique vers le bas
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
});
