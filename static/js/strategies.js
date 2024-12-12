// strategies.js
import { getSymbols } from './symbols.js';
import { renderStrategy } from './strategyRenderer.js'
/**
 * Adiciona uma nova estratégia ao DOM.
 */
export function addStrategySet() {
    const symbols = getSymbols();
    if (!symbols || symbols.length === 0) {
        console.error("No symbols loaded.");
        return;
    }

    const strategy = {
        strategy_id: crypto.randomUUID(),
        symbol: symbols[0], // Default para o primeiro símbolo
        buy: {
            percent: 0.0,
            condition_limit: 1,
            interval: 1,
            simultaneous_operations: 1,
        },
        sell: {
            percent: 1.0,
            condition_limit: 1,
            interval: 1,
        },
        status: "unsaved", // Define como "unsaved" para diferenciar
    };

    renderStrategy(strategy);
}


/**
 * Carrega as estratégias existentes do backend.
 */
export async function loadStrategies() {
    try {
        const response = await fetch("/get_strategies");
        if (!response.ok) {
            throw new Error(`Failed to load strategies: ${response.statusText}`);
        }

        const data = await response.json();
        const strategies = data.operations || [];

        const container = document.getElementById("operations-container");
        container.innerHTML = ""; // Limpa a mensagem padrão

        if (strategies.length === 0) {
            container.innerHTML = `<p style="text-align: center; color: #666;">No strategies yet. Add one below.</p>`;
            return;
        }

        strategies.forEach(renderStrategy);
    } catch (error) {
        console.error("Error loading strategies:", error);
    }
}


export function saveStrategy(strategyId) {
    const strategyElement = document.getElementById(strategyId);

    const symbol = strategyElement.querySelector(`#symbol-${strategyId}`).value;

    const buyStrategy = {
        percent: parseFloat(strategyElement.querySelector(`#percent-buy-${strategyId}`).dataset.value) || 0,
        condition_limit: parseInt(strategyElement.querySelector(`#condition_limit-buy-${strategyId}`).value) || 0,
        interval: parseFloat(strategyElement.querySelector(`#interval-buy-${strategyId}`).value) || 0,
        simultaneous_operations: parseInt(strategyElement.querySelector(`#simultaneous_operations-buy-${strategyId}`).value) || 0
    };

    const sellStrategy = {
        percent: 1.0,
        condition_limit: parseInt(strategyElement.querySelector(`#condition_limit-sell-${strategyId}`).value) || 0,
        interval: parseFloat(strategyElement.querySelector(`#interval-sell-${strategyId}`).value) || 0
    };

    const payload = {
        strategy_id: strategyId,
        symbol: symbol,
        buy: buyStrategy,
        sell: sellStrategy
    };

    fetch('/save_strategy', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error(`Error saving strategy ${strategyId}:`, data.error);
            } else {
                console.log(`Strategy ${strategyId} saved successfully!`);

                // Atualiza os campos para desabilitados
                const inputs = strategyElement.querySelectorAll('input, select');
                inputs.forEach(input => input.disabled = true);

                // Habilita o botão Start
                const startButton = strategyElement.querySelector('button[onclick^="startStrategy"]');
                startButton.disabled = false;

                // Atualiza o atributo data-saved para "true"
                strategyElement.setAttribute('data-saved', 'true');
            }
        })
        .catch(error => console.error('Error:', error));
}



export function removeStrategySet(strategyId) {
    const strategyBox = document.getElementById(strategyId);

    if (!strategyBox) {
        console.error(`Strategy with ID ${strategyId} not found.`);
        return;
    }

    // Verifica se a estratégia foi salva
    const isSaved = strategyBox.getAttribute('data-saved') === 'true';

    if (!isSaved) {
        // Apenas remove o elemento do DOM
        console.log(`Strategy ${strategyId} is not saved. Removing from frontend only.`);
        strategyBox.remove();
        return;
    }

    // Estratégia salva: faz a requisição para deletar no backend
    fetch('/delete_strategy', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ strategy_id: strategyId }),
    })
        .then((response) => {
            if (!response.ok) {
                throw new Error(`Failed to delete strategy ${strategyId}`);
            }
            return response.json();
        })
        .then((data) => {
            if (data.error) {
                console.error(`Error deleting strategy ${strategyId}:`, data.error);
            } else {
                console.log(`Strategy ${strategyId} deleted successfully.`);
                strategyBox.remove();
            }
        })
        .catch((error) => console.error('Error deleting strategy:', error));
}


export function startStrategy(strategyId) {
    const strategyBox = document.getElementById(strategyId);
    if (!strategyBox) {
        console.error(`Strategy with ID ${strategyId} not found.`);
        return;
    }

    fetch('/start_strategy', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ strategy_id: strategyId }),
    })
        .then((response) => response.json())
        .then((data) => {
            if (data.error) {
                console.error(`Error starting strategy ${strategyId}:`, data.error);
            } else {
                console.log(`Strategy ${strategyId} started successfully.`);
                
                // Atualizar os botões no frontend
                const saveButton = strategyBox.querySelector(`button[onclick="saveStrategy('${strategyId}')"]`);
                const startButton = strategyBox.querySelector(`button[onclick="startStrategy('${strategyId}')"]`);
                const stopButton = strategyBox.querySelector(`button[onclick="stopStrategy('${strategyId}')"]`);

                saveButton.disabled = true;  // Desabilita o botão de salvar
                startButton.disabled = true; // Desabilita o botão de iniciar
                stopButton.disabled = false; // Habilita o botão de parar
            }
        })
        .catch((error) => console.error('Error:', error));
}

export function stopStrategy(strategyId) {
    const strategyBox = document.getElementById(strategyId);
    if (!strategyBox) {
        console.error(`Strategy with ID ${strategyId} not found.`);
        return;
    }

    fetch('/stop_strategy', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ strategy_id: strategyId }),
    })
        .then((response) => {
            if (!response.ok) {
                return response.json().then((data) => {
                    throw new Error(data.error || 'Failed to stop strategies');
                });
            }
            return response.json();
        })
        .then((data) => {
            console.log(data.message); // Log de sucesso

            // Atualizar os botões no frontend
            const saveButton = strategyBox.querySelector(`button[onclick="saveStrategy('${strategyId}')"]`);
            const startButton = strategyBox.querySelector(`button[onclick="startStrategy('${strategyId}')"]`);
            const stopButton = strategyBox.querySelector(`button[onclick="stopStrategy('${strategyId}')"]`);

            saveButton.disabled = false; // Habilita o botão de salvar
            startButton.disabled = false; // Habilita o botão de iniciar
            stopButton.disabled = true;  // Desabilita o botão de parar
        })
        .catch((error) => console.error('Error stopping strategy:', error.message));
}