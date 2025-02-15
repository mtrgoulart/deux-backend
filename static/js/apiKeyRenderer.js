export function renderApiKey(apiKey) {
    const container = document.getElementById('api-keys-container');
    if (!container) {
        console.error("API Keys container not found in the DOM.");
        return;
    }

    const apiKeyElement = document.createElement('div');
    apiKeyElement.classList.add('api-key-item');

    const apiCredentials = apiKey.api_credentials || {};
    const apiKeyDisplay = apiCredentials.api_key || 'Not provided';
    const secretKeyDisplay = apiCredentials.secret_key || 'Not provided';
    const passphraseDisplay = apiCredentials.passphrase || 'Not provided';

    apiKeyElement.innerHTML = `
        <p><strong>Exchange:</strong> ${apiKey.exchange_name}</p>
        <p><strong>API Key:</strong> ${apiKeyDisplay}</p>
        <p><strong>Secret Key:</strong> ${secretKeyDisplay}</p>
        <p><strong>Passphrase:</strong> ${passphraseDisplay}</p>
        <p><strong>Created At:</strong> ${new Date(apiKey.created_at).toLocaleString()}</p>
        <div style="margin-top: 10px;">
            <button class="select-api-key-button" data-id="${apiKey.api_key_id}">Select</button>
            <button class="remove-api-key-button" data-id="${apiKey.api_key_id}">Remove</button>
        </div>
    `;

    apiKeyElement.querySelector('.select-api-key-button').addEventListener('click', () => {
        handleApiKeySelection(apiKey.api_key_id, apiKey.exchange_name);
    });

    apiKeyElement.querySelector('.remove-api-key-button').addEventListener('click', async () => {
        try {
            const response = await fetch('/remove_user_apikey', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ api_key_id: apiKey.api_key_id }),
            });

            if (!response.ok) {
                throw new Error(`Failed to remove API Key: ${response.statusText}`);
            }

            apiKeyElement.remove();
        } catch (error) {
            console.error('Error removing API Key:', error);
        }
    });

    container.appendChild(apiKeyElement);
}

import { loadInstances } from './instances.js'; // Certifique-se de importar a função correta

export function handleApiKeySelection(apiKeyId, apiKeyName) {
    console.log(`API Key Selected: ${apiKeyId} (${apiKeyName})`);

    // Fecha o pop-up
    const apiKeyPopup = document.getElementById('api-key-popup');
    apiKeyPopup.style.display = 'none';

    // Atualiza o cabeçalho ou exibe a API Key selecionada
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

    // Chama `loadInstances` para carregar as instâncias vinculadas
    loadInstances(apiKeyId);
}

