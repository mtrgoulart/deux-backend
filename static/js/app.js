import { loadSymbols } from './symbols.js';
import { loadStrategies, addStrategySet } from './strategies.js';

document.addEventListener('DOMContentLoaded', async () => {
    console.log("DOMContentLoaded triggered"); // Log para confirmar carregamento
    try {
        await loadSymbols(); // Carrega os símbolos do backend
        console.log("Symbols loaded"); // Log para confirmar

        await loadStrategies(); // Carrega as estratégias do usuário
        console.log("Strategies loaded"); // Log para confirmar

        // Adiciona o evento de clique para o botão "Add Strategy"
        const addOperationButton = document.getElementById('add-operation');
        console.log("Add Operation Button:", addOperationButton); // Log para confirmar se o botão foi encontrado

        addOperationButton.addEventListener('click', () => {
            console.log("Add Strategy Button clicked"); // Log para confirmar o evento
            addStrategySet();
        });
    } catch (error) {
        console.error("Error initializing the page:", error);
    }
});



import { removeStrategySet } from './strategies.js';

// Registra a função no escopo global
window.removeStrategySet = removeStrategySet;


import { saveStrategy } from './strategies.js';

// Registra a função globalmente
window.saveStrategy = saveStrategy;


import { startStrategy, stopStrategy } from './strategies.js';

// Registra as funções no escopo global
window.startStrategy = startStrategy;
window.stopStrategy = stopStrategy;


import { openIndicatorPopup } from './indicators.js';

// Registra a função no escopo global
window.openIndicatorPopup = openIndicatorPopup;