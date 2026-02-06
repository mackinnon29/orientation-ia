/**
 * Simple Mock AI Service pour simuler GLM 4.7
 */
const MockAiService = {
    step: 0,

    /**
     * Simule une réponse de GLM 4.7 basée sur l'historique ou le niveau de progression
     * @param {string} userMessage - Le dernier message de l'utilisateur
     * @returns {Promise<string>} - La réponse simulée
     */
    async getResponse(userMessage, onStatusUpdate, behavior = 'nice') {
        return new Promise((resolve) => {
            const delay = 1000 + Math.random() * 1500;

            setTimeout(() => {
                this.step++;
                resolve(this.generateMockResponse(userMessage, behavior));
            }, delay);
        });
    },

    generateMockResponse(input, behavior) {
        const text = input.toLowerCase();

        if (behavior === 'caustic') {
            return "Encore un indécis ? Écoute, j'ai pas toute la journée. Dis-moi ce que tu sais faire concrètement, si tant est que tu possèdes la moindre compétence utile. On avance ou tu préfères continuer à rêver ?";
        }

        if (this.step === 1) {
            return "C'est un excellent point de départ ! Pour mieux comprendre vos affinités, préférez-vous travailler avec des outils techniques (ordinateur, machines) ou plutôt avec des personnes (conseil, gestion d'équipe) ?";
        }

        if (text.includes('ordinateur') || text.includes('code') || text.includes('technique')) {
            return "Je vois que le côté technique vous attire. Avez-vous déjà pensé à des métiers comme Développeur, Data Scientist ou Ingénieur système ? Qu'est-ce qui vous plaît le plus dans la tech ?";
        }

        if (text.includes('aider') || text.includes('gens') || text.includes('humain')) {
            return "L'aspect humain semble primordial pour vous. C'est précieux ! Dans ce domaine, seriez-vous plus attiré par l'éducation, la santé ou le conseil en entreprise ?";
        }

        if (this.step > 5) {
            return "Nous avons bien avancé ! Suite à notre échange, je pourrais vous recommander les métiers de Développeur Logiciel ou d'Analyste Données. Souhaitez-vous explorer un de ces domaines en particulier ?";
        }

        return "C'est noté. Pourriez-vous me donner un exemple de projet ou d'activité qui vous a vraiment passionné récemment ?";
    }
};

/**
 * Service IA via OpenAI client (GLM 4.7)
 */
const OpenAIService = {
    async getResponse(userMessage, onStatusUpdate, behavior = 'nice') {
        const maxRetries = 5;
        let attempt = 0;
        const baseDelay = 1000;

        while (attempt < maxRetries) {
            attempt++;
            try {
                const response = await fetch('http://localhost:3000/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: userMessage, behavior: behavior })
                });

                if (response.ok) {
                    const data = await response.json();
                    return data.response;
                }

                if (response.status === 429 || response.status === 503) {
                    if (onStatusUpdate && attempt < maxRetries) {
                        onStatusUpdate('retry', attempt);
                    }

                    if (attempt >= maxRetries) {
                        throw new Error(`Échec après ${maxRetries} tentatives (statut ${response.status})`);
                    }

                    const delay = baseDelay * Math.pow(2, attempt - 1);
                    console.log(`Tentative ${attempt}/${maxRetries} échouée (${response.status}), nouvel essai dans ${delay}ms...`);
                    await new Promise(resolve => setTimeout(resolve, delay));
                } else {
                    throw new Error(`Erreur HTTP ${response.status}`);
                }

            } catch (error) {
                if (attempt >= maxRetries) {
                    console.warn("⚠️ Proxy OpenAI en erreur après tous les retries, fallback sur le MockService.", error);
                    const mockResponse = await MockAiService.getResponse(userMessage, onStatusUpdate, behavior);
                    return `[MODE MOCK] ${mockResponse}`;
                }

                const delay = baseDelay * Math.pow(2, attempt - 1);
                console.log(`Erreur de connexion, tentative ${attempt}/${maxRetries}, nouvel essai dans ${delay}ms...`);
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }

        const mockResponse = await MockAiService.getResponse(userMessage, onStatusUpdate, behavior);
        return `[MODE MOCK] ${mockResponse}`;
    }
};

/**
 * Sélecteur de service
 * Permet de basculer facilement. On utilise le Mock par défaut si on n'est pas sûr.
 */
const AiService = OpenAIService; // Changez pour MockAiService pour tester hors-ligne
