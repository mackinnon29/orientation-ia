# PRD - Assistant d'Orientation Scolaire IA

## 1. Vision du Produit
Créer une application web interactive et intuitive qui aide les étudiants à découvrir leur futur métier grâce à un dialogue fluide avec l'intelligence artificielle Gemini. L'objectif est de transformer une recherche souvent stressante en une expérience conversationnelle enrichissante.

## 2. Objectifs
- **Engagement** : Proposer une interface simple et moderne qui incite à l'échange.
- **Pertinence** : Utiliser la puissance de Gemini pour poser des questions qui sortent des sentiers battus des tests d'orientation classiques.
- **Clarté** : Fournir des recommandations concrètes et motivées.

## 3. Public Cible
- Étudiants (Collège, Lycée, Études supérieures) en pleine réflexion sur leur avenir.
- Jeunes adultes cherchant une spécialisation.
- Toute personne souhaitant explorer de nouvelles pistes de carrière.

## 4. Fonctionnalités Clés
- **Interface de Chat Interactive** : Un flux de discussion dynamique où l'utilisateur répond aux questions de l'IA.
- **Algorithme de Profilage (via Gemini)** : L'IA n'utilise pas de script fixe mais adapte ses questions en fonction des réponses précédentes.
- **Système de Recommandation** : En fin de parcours, l'IA génère une fiche détaillée pour 1 à 3 métiers.
- **Architecture d'IA Flexible** :
    - **Service Mock** : Permet de tester l'interface utilisateur sans appels API réels (gain de temps et économie de quota).
    - **Service Gemini Réel** : Intégration avec l'API Google Generative AI pour l'intelligence réelle.

## 5. Parcours Utilisateur
1. **Landing Page** : L'utilisateur arrive sur une page d'accueil accueillante expliquant le concept.
2. **Initialisation** : L'IA se présente et lance la première question ouverte.
3. **Dialogue** : Entre 5 et 8 échanges pour cerner la personnalité et les compétences de l'utilisateur.
4. **Traitement** : Une animation de chargement élégante pendant que Gemini compile les résultats.
5. **Rapport Final** : Affichage des métiers recommandés avec la possibilité de recommencer ou d'en savoir plus.

## 6. Spécifications Techniques
- **Langages** : HTML5, CSS3, JavaScript (Vanilla pour plus de légèreté et de contrôle).
- **Design System** : Utilisation de variables CSS pour un thème cohérent (Dark mode par défaut ou commutable).
- **Backend/IA** : Gestion de l'API key Gemini via un petit proxy pour la sécurité des clés.

## 7. Critères d'Excellence Visuelle (Aesthetics)
- **Typographie** : Utilisation de polices modernes (type 'Inter' ou 'Outfit').
- **Effets** : Glassmorphism, dégradés subtils, et micro-animations sur les boutons et bulles de chat.
- **Réactivité** : Design parfaitement adapté aux mobiles.
