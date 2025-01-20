import { loadUserName, setupLogoutButton } from './user.js';
import { setupApiKeyButton } from './apikeys.js';
import { loadInstances, startInstance, stopInstance, saveInstance, renderInstance } from './instances.js';
import { removeStrategySet, saveStrategy, startStrategy, stopStrategy } from './strategies.js';
import { openIndicatorPopup } from './indicators.js';
import { loadSymbols } from './symbols.js';
import { renderStrategy } from './strategyRenderer.js';

document.addEventListener('DOMContentLoaded', async () => {
    console.log("DOMContentLoaded triggered");

    // Mostra o overlay de carregamento
    const loadingOverlay = document.getElementById('loading-overlay');
    loadingOverlay.style.display = 'flex';

    try {
        // Inicializa a página
        await initializePage();

        // Verifica se há uma API Key selecionada no localStorage
        let selectedApiKeyId = localStorage.getItem('selectedApiKeyId');

        // Se não houver, solicita ao usuário que selecione
        if (!selectedApiKeyId) {
            console.warn("No API Key found in localStorage. Prompting user for selection.");
            selectedApiKeyId = await ensureApiKeySelected();
            if (!selectedApiKeyId) {
                console.error("User did not select an API Key. Cannot proceed further.");
                return; // Encerra o carregamento se nenhuma API Key for selecionada
            }
            localStorage.setItem('selectedApiKeyId', selectedApiKeyId); // Salva no localStorage
        } else {
            console.log(`Using stored API Key ID: ${selectedApiKeyId}`);
        }

        // Carrega instâncias vinculadas à API Key selecionada
        await loadInstances(selectedApiKeyId);

        // Configura o botão de adicionar instância
        setupAddInstanceButton();
    } catch (error) {
        console.error("Error initializing the page:", error);
    } finally {
        // Remove o overlay de carregamento após inicialização
        loadingOverlay.style.display = 'none';
    }
});

async function initializePage() {
    await loadSymbols();
    await loadUserName();
    setupLogoutButton();
    setupApiKeyButton();
}


/**
 * Garante que uma API Key seja selecionada antes de continuar.
 */
async function ensureApiKeySelected() {
    return new Promise((resolve) => {
        const apiKeyPopup = document.getElementById('api-key-popup');
        const apiKeyContainer = document.getElementById('api-keys-container');

        // Mostra o pop-up de seleção de API Key
        apiKeyPopup.style.display = 'flex';

        // Configura o evento de clique na lista de API Keys
        apiKeyContainer.addEventListener('click', (event) => {
            const button = event.target.closest('.select-api-key-button');
            if (button) {
                const apiKeyId = button.dataset.id;
                console.log(`API Key Selected: ${apiKeyId}`); // Log para depuração
                apiKeyPopup.style.display = 'none'; // Fecha o pop-up
                resolve(apiKeyId); // Retorna o ID da API Key selecionada
            }
        });
    });
}



import { saveStrategyData } from './strategies.js'; // Importe a nova função

function setupAddInstanceButton() {
    const addOperationButton = document.getElementById('add-operation');
    if (!addOperationButton) {
        console.error("Add Instance Button not found.");
        return;
    }

    addOperationButton.addEventListener('click', () => {
        console.log("Add Instance Button clicked");

        const instanceName = prompt("Enter a name for the new instance:");
        if (!instanceName) {
            alert("Instance name is required.");
            return;
        }

        // Gera um UUID para a instância e a estratégia associada
        const instanceId = crypto.randomUUID();
        const strategyId = crypto.randomUUID();

        // Cria a estrutura da instância no DOM
        const container = document.getElementById("instances-container");
        const instanceElement = document.createElement('div');
        instanceElement.classList.add('instance-item');
        instanceElement.id = `instance-${instanceId}`;
        instanceElement.innerHTML = `
            <h3>${instanceName}</h3>
            <div class="strategies-container" id="strategies-container-${instanceId}">
                <h4>Strategies:</h4>
            </div>
        `;

        container.appendChild(instanceElement);

        const strategiesContainer = document.getElementById(`strategies-container-${instanceId}`);

        // Cria a estratégia padrão no DOM
        const defaultStrategy = {
            strategy_id: strategyId,
            instance_id: instanceId,
            symbol: "BTC/USD",
            instanceName: instanceName,
            buy: { percent: 0.5, condition_limit: 10.0, interval: 30, simultaneous_operations: 1 },
            sell: { percent: 0.3, condition_limit: 5.0, interval: 15 },
            status: "unsaved", // Inicialmente não salva
        };

        renderStrategy(defaultStrategy, strategiesContainer);
    });
}


async function createDefaultStrategy(instanceId) {
    try {
        const response = await fetch('/create_strategy', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ instance_id: instanceId }),
        });

        if (!response.ok) {
            throw new Error(`Failed to create default strategy: ${response.statusText}`);
        }

        return await response.json();
    } catch (error) {
        console.error("Error creating default strategy:", error);
        return null;
    }
}

// Registra funções globais para uso em outros scripts
window.removeStrategySet = removeStrategySet;
window.saveStrategy = saveStrategy;
window.startStrategy = startStrategy;
window.stopStrategy = stopStrategy;
window.openIndicatorPopup = openIndicatorPopup;

// Torna as funções startInstance e stopInstance globais
window.startInstance = startInstance;
window.stopInstance = stopInstance;