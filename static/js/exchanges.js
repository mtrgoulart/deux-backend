// exchanges.js - Gerenciamento de exchanges e credenciais de API

let selectedApiKey = null; // Armazena a credencial de API selecionada

/**
 * Carrega as credenciais de API do usuário do backend.
 */
export async function loadUserApiKeys() {
    try {
        const response = await fetch('/get_user_apikeys'); // Endpoint para carregar as API Keys
        if (response.ok) {
            const data = await response.json();
            console.log("User API keys loaded:", data.user_apikeys);
            return data.user_apikeys || []; // Retorna um array vazio se não houver API keys
        } else {
            console.error("Failed to load user API keys:", response.statusText);
            return [];
        }
    } catch (error) {
        console.error("Error fetching user API keys:", error);
        return [];
    }
}


/**
 * Retorna a credencial de API selecionada.
 * @returns {Object|null} A credencial de API selecionada ou null.
 */
export function getSelectedApiKey() {
    return selectedApiKey;
}

