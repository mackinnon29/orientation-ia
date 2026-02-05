/**
 * Simple Mock AI Service pour simuler Gemini
 */
const MockAiService = {
    step: 0,

    /**
     * Simule une réponse de Gemini basée sur l'historique ou le niveau de progression
     * @param {string} userMessage - Le dernier message de l'utilisateur
     * @returns {Promise<string>} - La réponse simulée
     */
    async getResponse(userMessage) {
        return new Promise((resolve) => {
            // Simulation de temps de réflexion
            const delay = 1000 + Math.random() * 1500;

            setTimeout(() => {
                this.step++;
                resolve(this.generateMockResponse(userMessage));
            }, delay);
        });
    },

    generateMockResponse(input) {
        const text = input.toLowerCase();

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
 * Service IA Réel (via Proxy local)
 */
const GeminiService = {
    async getResponse(userMessage) {
        try {
            const response = await fetch('http://localhost:3000/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: userMessage })
            });

            if (!response.ok) throw new Error('Erreur proxy');

            const data = await response.json();
            return data.response;
        } catch (error) {
            console.warn("Proxy inaccessible, fallback sur le MockService.");
            return MockAiService.getResponse(userMessage);
        }
    }
};

/**
 * Sélecteur de service
 * Permet de basculer facilement. On utilise le Mock par défaut si on n'est pas sûr.
 */
const AiService = GeminiService; // Changez pour MockAiService pour tester hors-ligne
