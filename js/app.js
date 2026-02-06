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
    const aiBehavior = document.getElementById('ai-behavior');

    // État du questionnaire
    let currentQuestionIndex = 0;
    let isGeneralPhase = true;
    const userAnswers = [];

    const GENERAL_QUESTIONS = [
        {
            text: "Préfères-tu travailler...",
            options: [
                { letter: 'A', text: "Seul(e)" },
                { letter: 'B', text: "En équipe" }
            ]
        },
        {
            text: "Préfères-tu être...",
            options: [
                { letter: 'A', text: "Dehors" },
                { letter: 'B', text: "En intérieur" }
            ]
        },
        {
            text: "Quel environnement t'attire le plus ?",
            options: [
                { letter: 'A', text: "Bureau / Moderne" },
                { letter: 'B', text: "Chantier / Atelier" },
                { letter: 'C', text: "Nature / Grand air" },
                { letter: 'D', text: "Hôpital / Social" }
            ]
        },
        {
            text: "Ton super-pouvoir est plutôt...",
            options: [
                { letter: 'A', text: "La logique (résoudre des énigmes)" },
                { letter: 'B', text: "La créativité (imaginer des choses)" },
                { letter: 'C', text: "L'empathie (écouter et aider)" },
                { letter: 'D', text: "L'organisation (planifier et diriger)" }
            ]
        },
        {
            text: "Face à une machine en panne, tu...",
            options: [
                { letter: 'A', text: "Prends les outils pour la réparer" },
                { letter: 'B', text: "Cherches le manuel en ligne" },
                { letter: 'C', text: "Appelles un expert" },
                { letter: 'D', text: "En profites pour faire une pause café" }
            ]
        },
        {
            text: "Le plus important pour toi dans un job :",
            options: [
                { letter: 'A', text: "Un gros salaire" },
                { letter: 'B', text: "Du temps libre (équilibre)" },
                { letter: 'C', text: "Se sentir utile aux autres" },
                { letter: 'D', text: "Relever des défis techniques" }
            ]
        },
        {
            text: "Ton rythme idéal est...",
            options: [
                { letter: 'A', text: "Calme et structuré" },
                { letter: 'B', text: "Rapide et imprévisible" },
                { letter: 'C', text: "Basé sur les horaires de bureau" },
                { letter: 'D', text: "Flexible (nomade)" }
            ]
        }
    ];

    // Transition vers le chat
    startBtn.addEventListener('click', () => {
        heroSection.classList.add('hidden');
        chatSection.classList.remove('hidden');
        showNextGeneralQuestion();
    });

    /**
     * Affiche la question suivante du questionnaire général
     */
    function showNextGeneralQuestion() {
        if (currentQuestionIndex < GENERAL_QUESTIONS.length) {
            const question = GENERAL_QUESTIONS[currentQuestionIndex];
            addIMessage(question.text, 'ai', question.options);
        } else {
            isGeneralPhase = false;
            const summary = userAnswers.map(a => a.text).join(', ');

            // Envoyer les réponses au serveur pour le contexte futur
            AiService.setGeneralAnswers(userAnswers);

            addMessage(`Merci pour ces réponses ! J'ai bien noté que tu préfères : ${summary}. Par quoi souhaites-tu commencer notre exploration ?`, 'ai');
        }
    }

    /**
     * Gère la sélection d'un choix
     */
    window.handleChoice = (qIndex, choiceIndex) => {
        const question = GENERAL_QUESTIONS[qIndex];
        const choice = question.options[choiceIndex];

        // Bloquer le conteneur actuel
        const containers = document.querySelectorAll('.choices-container');
        const lastContainer = containers[containers.length - 1];
        if (lastContainer) lastContainer.style.pointerEvents = 'none';

        addMessage(`${choice.letter}. ${choice.text}`, 'user');
        userAnswers.push(choice);
        currentQuestionIndex++;

        setTimeout(showNextGeneralQuestion, 600);
    };

    // Envoi de message
    const handleSend = async () => {
        if (isGeneralPhase) return;

        const text = userInput.value.trim();
        if (text) {
            addMessage(text, 'user');
            userInput.value = '';

            const loadingMsg = addLoadingIndicator();
            let statusMsg = null;
            let funnyMsgInterval = null;

            const funnyMessages = [
                "L'IA réfléchit...",
                "Réflexion intense...",
                "L'IA cherche ses mots...",
                "Calcul en cours..."
            ];

            funnyMsgInterval = setTimeout(() => {
                const randomMsg = funnyMessages[Math.floor(Math.random() * funnyMessages.length)];
                statusMsg = addStatusMessage(randomMsg, 'funny-waiting-msg');
            }, 3000);

            try {
                const onStatusUpdate = (status, attempt) => {
                    if (status === 'retry') {
                        clearTimeout(funnyMsgInterval);
                        if (statusMsg) removeElement(statusMsg);
                        statusMsg = addStatusMessage("IA surchargée, nouvelle tentative...", "dimmed");
                    }
                };

                const behavior = aiBehavior ? aiBehavior.value : 'nice';
                const response = await AiService.getResponse(text, onStatusUpdate, behavior);

                clearTimeout(funnyMsgInterval);
                removeLoadingIndicator(loadingMsg);
                if (statusMsg) removeElement(statusMsg);

                addMessage(response, 'ai');
            } catch (error) {
                clearTimeout(funnyMsgInterval);
                removeLoadingIndicator(loadingMsg);
                if (statusMsg) removeElement(statusMsg);
                addMessage("Désolé, j'ai rencontré un petit souci. Ressaie ?", 'ai');
            }
        }
    };

    /**
     * Ajoute un message avec options si présentes
     */
    function addIMessage(text, sender, options = null) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender);
        messageDiv.textContent = text;
        chatMessages.appendChild(messageDiv);

        if (options) {
            const choicesDiv = document.createElement('div');
            choicesDiv.classList.add('choices-container');
            options.forEach((opt, idx) => {
                const btn = document.createElement('button');
                btn.className = 'choice-btn';
                btn.innerHTML = `<span class="letter">${opt.letter}</span> ${opt.text}`;
                btn.onclick = () => window.handleChoice(currentQuestionIndex, idx);
                choicesDiv.appendChild(btn);
            });
            chatMessages.appendChild(choicesDiv);
        }

        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function addStatusMessage(text, className = '') {
        const msgDiv = document.createElement('div');
        msgDiv.classList.add('status-msg');
        if (className) msgDiv.classList.add(className);
        msgDiv.textContent = text;
        chatMessages.appendChild(msgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return msgDiv;
    }

    function removeElement(el) {
        if (el && el.parentNode) el.parentNode.removeChild(el);
    }

    sendBtn.addEventListener('click', handleSend);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSend();
    });

    function addLoadingIndicator() {
        const msgDiv = document.createElement('div');
        msgDiv.classList.add('message', 'ai', 'loading');
        msgDiv.innerHTML = '<span>.</span><span>.</span><span>.</span>';
        chatMessages.appendChild(msgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return msgDiv;
    }

    function removeLoadingIndicator(el) {
        if (el && el.parentNode) el.parentNode.removeChild(el);
    }

    function addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender);

        if (sender === 'ai' && typeof marked !== 'undefined') {
            messageDiv.innerHTML = marked.parse(text);
        } else {
            messageDiv.textContent = text;
        }
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
});
