/**
 * Point d'entrée principal de l'application
 */
document.addEventListener('DOMContentLoaded', () => {
    console.log('Application Orientation IA chargée.');

    const startBtn = document.getElementById('start-btn');
    if (startBtn) {
        startBtn.addEventListener('click', () => {
            console.log('Démarrage de la conversation...');
            // Logique de transition vers le chat
        });
    }
});
