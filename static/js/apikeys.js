import { loadUserApiKeys } from './exchanges.js';
import { renderApiKey } from './apiKeyRenderer.js';



async function loadExchanges() {
    try {
        const response = await fetch('/get_exchanges');
        if (!response.ok) {
            throw new Error(`Failed to fetch exchanges: ${response.statusText}`);
        }

        const data = await response.json();
        const exchangeSelect = document.getElementById('exchange-id'); // Lista suspensa no formulário

        if (!exchangeSelect) {
            console.error("Exchange select element not found in DOM.");
            return;
        }

        exchangeSelect.innerHTML = ''; // Limpa o conteúdo atual

        data.exchanges.forEach((exchange) => {
            const option = document.createElement('option');
            option.value = exchange.id; // ID da exchange como valor
            option.textContent = exchange.name; // Nome da exchange como texto
            exchangeSelect.appendChild(option);
        });
    } catch (error) {
        console.error("Error loading exchanges:", error);
    }
}

export function getSelectedApiKeyId() {
    const selectedApiKey = document.querySelector('.selected-api-key');
    return selectedApiKey ? selectedApiKey.dataset.apiKeyId : null;
}

/**
 * Carrega as API Keys do backend e exibe na página.
 */
export async function loadApiKeys() {
    try {
        const response = await fetch('/get_user_apikeys');
        if (!response.ok) {
            throw new Error(`Failed to fetch API Keys: ${response.statusText}`);
        }

        const data = await response.json();
        const container = document.getElementById('api-keys-container');
        container.innerHTML = ''; // Limpa o container

        if (!data.user_apikeys || data.user_apikeys.length === 0) {
            container.innerHTML = `<p style="text-align: center; color: #666;">No API Keys found. Add one below.</p>`;
        } else {
            data.user_apikeys.forEach((apiKey) => renderApiKey(apiKey));
        }
    } catch (error) {
        console.error("Error loading API Keys:", error);
        const container = document.getElementById('api-keys-container');
        container.innerHTML = `<p style="text-align: center; color: red;">Error loading API Keys.</p>`;
    }
}

export function setupApiKeyButton() {
    const selectApiKeyButton = document.getElementById('select-api-key-button');
    const apiKeyPopup = document.getElementById('api-key-popup');
    const apiKeyContainer = document.getElementById('api-keys-container');
    const closePopupButton = document.getElementById('close-api-key-popup');
    const addApiKeyButton = document.getElementById('add-api-key-button');

    if (!selectApiKeyButton || !apiKeyPopup || !apiKeyContainer || !closePopupButton || !addApiKeyButton) {
        console.error("Elements for API Key popup not found in DOM.");
        return;
    }

    // Configura o evento para abrir o pop-up
    selectApiKeyButton.addEventListener('click', async () => {
        apiKeyPopup.style.display = 'flex'; // Mostra o pop-up

        try {
            await loadApiKeys(); // Carrega as API Keys e renderiza
        } catch (error) {
            console.error("Error loading API Keys:", error);
        }
    });

    // Configura o evento para redirecionar para a página de registro de nova API Key
    addApiKeyButton.addEventListener('click', () => {
        console.log("Redirecting to register API Key page."); // Log para debug
        window.location.href = '/register-api-key'; // Redireciona para a rota de registro
    });

    // Configura o evento para fechar o pop-up
    closePopupButton.addEventListener('click', () => {
        console.log("Closing API Key popup."); // Log para debug
        apiKeyPopup.style.display = 'none';
    });
}

/**
 * Lida com a seleção da API Key e fecha o pop-up.
 */
function handleApiKeySelection(apiKeyId, apiKeyName) {
    console.log(`API Key Selected: ${apiKeyId} (${apiKeyName})`);

    const apiKeyPopup = document.getElementById('api-key-popup');
    apiKeyPopup.style.display = 'none';

    const header = document.getElementById('header');
    const selectedKey = document.getElementById('selected-api-key');
    if (selectedKey) {
        selectedKey.textContent = `Selected API Key: ${apiKeyName}`;
    } else {
        const newSelectedKey = document.createElement('p');
        newSelectedKey.id = 'selected-api-key';
        newSelectedKey.textContent = `Selected API Key: ${apiKeyName}`;
        header.appendChild(newSelectedKey);
    }

    // Atualiza o localStorage e carrega instâncias associadas
    localStorage.setItem('selectedApiKeyId', apiKeyId);
    loadInstances(apiKeyId); // Chama a função para carregar instâncias
}

/**
 * Configura o botão para exibir o formulário de registro de nova API Key.
 */
export function setupAddApiKeyButton() {
    const addApiKeyButton = document.getElementById('add-api-key-button');
    const apiKeyForm = document.getElementById('api-key-form-container'); // Container do formulário

    if (!addApiKeyButton || !apiKeyForm) {
        console.error("Add API Key button or form container not found in DOM.");
        return;
    }

    // Exibe o formulário ao clicar no botão
    addApiKeyButton.addEventListener('click', async () => {
        apiKeyForm.style.display = 'block'; // Exibe o formulário
        await loadExchanges(); // Carrega as exchanges ao abrir o formulário
    });

    // Configura o botão de cancelamento no formulário
    const cancelButton = document.getElementById('close-api-key-modal');
    cancelButton.addEventListener('click', () => {
        apiKeyForm.style.display = 'none'; // Esconde o formulário
    });
}

/**
 * Configura o formulário de registro de nova API Key.
 */
export function setupApiKeyForm() {
    const form = document.getElementById('api-key-form');
    form.addEventListener('submit', async (event) => {
        event.preventDefault(); // Evita o recarregamento da página

        const formData = new FormData(form);
        const payload = {
            exchange_id: formData.get('exchange_id'),
            api_credentials: {
                api_key: formData.get('api_key'),
                secret_key: formData.get('secret_key'),
                passphrase: formData.get('passphrase'),
            },
        };

        try {
            const response = await fetch('/save_user_apikey', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                throw new Error(`Failed to save API Key: ${response.statusText}`);
            }

            // Recarrega as API Keys após salvar uma nova
            await loadApiKeys();
            form.reset(); // Limpa o formulário
            document.getElementById('api-key-form-container').style.display = 'none'; // Esconde o formulário
        } catch (error) {
            console.error("Error saving API Key:", error);
        }
    });
}

// Inicializa as funções ao carregar a página
document.addEventListener('DOMContentLoaded', async () => {
    await loadApiKeys();
    setupAddApiKeyButton();
    setupApiKeyForm();
});
