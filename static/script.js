document.addEventListener('DOMContentLoaded', () => {
    loadSymbols(); // Carrega os símbolos
    loadStrategies(); // Carrega as estratégias do usuário
});

let symbols = []; // Lista de símbolos carregados do backend

// Carrega os símbolos do backend
async function loadSymbols() {
    try {
        const response = await fetch('/get_symbols');
        if (response.ok) {
            symbols = await response.json();
            console.log("Symbols loaded:", symbols);
        } else {
            console.error("Failed to load symbols:", response.statusText);
        }
    } catch (error) {
        console.error("Error fetching symbols:", error);
    }
}

// Adiciona uma nova estratégia com as caixas de Buy e Sell
function addStrategySet() {
    const strategyId = crypto.randomUUID();
    const strategyBox = document.createElement('div');
    strategyBox.classList.add('strategy-box');
    strategyBox.id = strategyId;

    // Caixa de Buy (verde)
    const buyBox = `
        <div class="buy-box">
            <h4>Buy Strategy</h4>
            <label for="percent-buy-${strategyId}">Percent:</label>
            <input type="text" id="percent-buy-${strategyId}" placeholder="Enter the percentage" required data-value="">
            
            <label for="condition_limit-buy-${strategyId}">Condition Limit:</label>
            <input type="number" id="condition_limit-buy-${strategyId}" min="1" placeholder="Enter condition limit" required>
            
            <label for="interval-buy-${strategyId}">Interval (minutes):</label>
            <input type="number" id="interval-buy-${strategyId}" step="0.01" placeholder="Enter interval in minutes" required>
            
            <label for="simultaneous_operations-buy-${strategyId}">Simultaneous Operations:</label>
            <input type="text" id="simultaneous_operations-buy-${strategyId}" placeholder="Enter number of simultaneous operations" required>
        </div>
    `;

    // Caixa de Sell (vermelho)
    const sellBox = `
        <div class="sell-box">
            <h4>Sell Strategy</h4>
            <label for="percent-sell-${strategyId}">Percent:</label>
            <input type="text" id="percent-sell-${strategyId}" value="100%" disabled>
            
            <label for="condition_limit-sell-${strategyId}">Condition Limit:</label>
            <input type="number" id="condition_limit-sell-${strategyId}" min="1" placeholder="Enter condition limit" required>
            
            <label for="interval-sell-${strategyId}">Interval (minutes):</label>
            <input type="number" id="interval-sell-${strategyId}" step="0.01" placeholder="Enter interval in minutes" required>
        </div>
    `;

    // Caixa Pai
    strategyBox.innerHTML = `
        <h3>Strategy ${strategyId}</h3>
        <label for="symbol-${strategyId}">Symbol:</label>
        <select id="symbol-${strategyId}" required>
            ${symbols.map(symbol => `<option value="${symbol}">${symbol}</option>`).join('')}
        </select>

        <div class="strategy-inner">
            ${buyBox}
            ${sellBox}
        </div>

        <div class="operation-controls">
            <button onclick="saveStrategy('${strategyId}')">Save</button>
            <button onclick="startStrategy('${strategyId}')" disabled>Start</button>
            <button onclick="stopStrategy('${strategyId}')" disabled>Stop</button>
            <button class="remove-button" onclick="removeStrategySet('${strategyId}')">Remove</button>
        </div>
    `;

    const container = document.getElementById('operations-container');
    container.appendChild(strategyBox);

    // Eventos para formatação do campo Percent e validação de números
    const percentInputBuy = document.getElementById(`percent-buy-${strategyId}`);
    percentInputBuy.addEventListener('input', formatPercentInput);

    const simultaneousInput = document.getElementById(`simultaneous_operations-buy-${strategyId}`);
    simultaneousInput.addEventListener('input', validateNumericInput);

    if (container.querySelector('p')) {
        container.querySelector('p').remove();
    }
}

// Valida que apenas números sejam inseridos
function validateNumericInput(event) {
    const input = event.target;
    input.value = input.value.replace(/[^0-9]/g, ''); // Remove caracteres não numéricos
}

// Formata o valor no campo Percent dinamicamente
function formatPercentInput(event) {
    const input = event.target;
    let rawValue = parseFloat(input.value.replace(/[^0-9.]/g, '')); // Remove caracteres não numéricos

    if (!isNaN(rawValue)) {
        if (rawValue > 100) {
            rawValue = 100; // Corrige para 100 se o valor for maior
        }
        input.dataset.value = (rawValue / 100).toFixed(4); // Armazena como float no atributo data-value
        input.value = `${rawValue}%`; // Mostra como porcentagem
    } else {
        input.dataset.value = ""; // Limpa o valor armazenado
        input.value = ""; // Limpa o campo
    }
}

// Formata o valor no campo Percent dinamicamente
function formatPercentInput(event) {
    const input = event.target;
    let rawValue = parseFloat(input.value.replace(/[^0-9.]/g, '')); // Remove caracteres não numéricos

    if (!isNaN(rawValue)) {
        if (rawValue > 100) {
            rawValue = 100; // Corrige para 100 se o valor for maior
        }
        input.dataset.value = (rawValue / 100).toFixed(4); // Armazena como float no atributo data-value
        input.value = `${rawValue}%`; // Mostra como porcentagem
    } else {
        input.dataset.value = ""; // Limpa o valor armazenado
        input.value = ""; // Limpa o campo
    }
}

// Salva a estratégia no backend
function saveStrategy(strategyId) {
    const strategyElement = document.getElementById(strategyId);

    // Pega o símbolo da estratégia pai
    const symbol = strategyElement.querySelector(`#symbol-${strategyId}`).value;

    // Prepara os dados da estratégia de Buy
    const buyStrategy = {
        percent: parseFloat(strategyElement.querySelector(`#percent-buy-${strategyId}`).dataset.value) || 0,
        condition_limit: parseInt(strategyElement.querySelector(`#condition_limit-buy-${strategyId}`).value) || 0,
        interval: parseFloat(strategyElement.querySelector(`#interval-buy-${strategyId}`).value) || 0,
        simultaneous_operations: parseInt(strategyElement.querySelector(`#simultaneous_operations-buy-${strategyId}`).value) || 0
    };

    // Prepara os dados da estratégia de Sell
    const sellStrategy = {
        percent: 1.0, // Fixado em 100%
        condition_limit: parseInt(strategyElement.querySelector(`#condition_limit-sell-${strategyId}`).value) || 0,
        interval: parseFloat(strategyElement.querySelector(`#interval-sell-${strategyId}`).value) || 0
    };

    // Monta o payload para o POST
    const payload = {
        strategy_id: strategyId,
        symbol: symbol,
        buy: buyStrategy,
        sell: sellStrategy
    };

    // Faz o POST para a rota /save_strategy
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

                // Bloqueia os campos após salvar
                const inputs = strategyElement.querySelectorAll('input, select');
                inputs.forEach(input => input.disabled = true);

                // Habilita o botão Start
                const startButton = strategyElement.querySelector('button[onclick^="startStrategy"]');
                startButton.disabled = false;
            }
        })
        .catch(error => console.error('Error:', error));
}

// Remove a estratégia
function removeStrategySet(strategyId) {
    const element = document.getElementById(strategyId);
    if (element) {
        element.remove();
    }
    console.log(`Strategy ${strategyId} removed!`);
}

// Simula logout
function logout() {
    console.log("Logged out successfully!");
}

// Envia a estratégia para o backend e inicia as operações de Buy e Sell
function startStrategy(strategyId) {
    const payload = { strategy_id: strategyId };

    // Faz o POST para a rota /start_strategy
    fetch('/start_strategy', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
    })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Failed to start strategy: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                console.error(`Error starting strategy ${strategyId}:`, data.error);
            } else {
                console.log(`Strategy ${strategyId} started successfully!`);

                // Atualiza a interface
                const strategyElement = document.getElementById(strategyId);
                const stopButton = strategyElement.querySelector('button[onclick^="stopStrategy"]');
                const removeButton = strategyElement.querySelector('button[onclick^="removeStrategySet"]');
                stopButton.disabled = false;
                removeButton.disabled = true;
            }
        })
        .catch(error => console.error('Error:', error));
}

// Para a estratégia enviando o ID para a rota /stop_strategy
function stopStrategy(strategyId) {
    const payload = {
        strategy_id: strategyId
    };

    // Faz o POST para a rota /stop_strategy
    fetch('/stop_strategy', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error(`Error stopping strategy ${strategyId}:`, data.error);
            } else {
                console.log(`Strategy ${strategyId} stopped successfully!`);

                // Atualiza a interface
                const strategyElement = document.getElementById(strategyId);
                const stopButton = strategyElement.querySelector('button[onclick^="stopStrategy"]');
                const removeButton = strategyElement.querySelector('button[onclick^="removeStrategySet"]');
                stopButton.disabled = true;
                removeButton.disabled = false;
            }
        })
        .catch(error => console.error('Error:', error));
}


export async function loadStrategies() {
    try {
        const response = await fetch('/get_strategies');
        if (response.ok) {
            const data = await response.json();
            const strategies = data.operations;

            const container = document.getElementById('operations-container');
            if (!container) {
                console.error("Container not found");
                return;
            }

            if (strategies && strategies.length > 0) {
                container.innerHTML = ""; // Limpa mensagens padrão ou conteúdo anterior

                strategies.forEach(strategy => {
                    const { strategy_id, symbol, side, percent, condition_limit, interval, simultaneous_operations, status } = strategy;

                    // Verifica se a estratégia já existe
                    let strategyBox = document.getElementById(strategy_id);
                    if (!strategyBox) {
                        strategyBox = document.createElement('div');
                        strategyBox.classList.add('strategy-box');
                        strategyBox.id = strategy_id;

                        // Cria o layout principal da estratégia
                        strategyBox.innerHTML = `
                            <h3>Strategy ${strategy_id || "Unnamed"}</h3>
                            <label for="symbol-${strategy_id}">Symbol:</label>
                            <select id="symbol-${strategy_id}" disabled>
                                ${symbols.map(s => `<option value="${s}" ${s === symbol ? "selected" : ""}>${s}</option>`).join('')}
                            </select>
                            <div class="strategy-inner"></div>
                            <div class="operation-controls">
                                <button onclick="startStrategy('${strategy_id}')" ${status === 'active' ? 'disabled' : ''}>Start</button>
                                <button onclick="stopStrategy('${strategy_id}')" ${status === 'stopped' ? 'disabled' : ''}>Stop</button>
                                <button class="remove-button" onclick="removeStrategySet('${strategy_id}')" ${status === 'active' ? 'disabled' : ''}>Remove</button>
                            </div>
                        `;

                        container.appendChild(strategyBox);
                    }

                    // Adiciona os detalhes da estratégia (Buy ou Sell)
                    const strategyInner = strategyBox.querySelector('.strategy-inner');
                    const boxType = side === 'buy' ? 'buy-box' : 'sell-box';
                    const existingBox = strategyInner.querySelector(`.${boxType}`);

                    if (!existingBox) {
                        const boxHTML = `
                            <div class="${boxType}">
                                <h4>${side.charAt(0).toUpperCase() + side.slice(1)} Strategy</h4>
                                <label>Percent:</label>
                                <input type="text" value="${(percent * 100).toFixed(2)}%" disabled>
                                <label>Condition Limit:</label>
                                <input type="number" value="${condition_limit}" disabled>
                                <label>Interval (minutes):</label>
                                <input type="number" value="${interval}" disabled>
                                ${side === 'buy' ? `<label>Simultaneous Operations:</label><input type="number" value="${simultaneous_operations || ''}" disabled>` : ''}
                            </div>
                        `;
                        strategyInner.innerHTML += boxHTML;
                    }
                });
            } else {
                // Caso não existam estratégias
                container.innerHTML = `<p style="text-align: center; color: #666;">No strategies yet. Add one below.</p>`;
            }
        } else {
            console.error("Failed to load strategies:", response.statusText);
        }
    } catch (error) {
        console.error("Error fetching strategies:", error);
    }
}