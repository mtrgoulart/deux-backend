// symbols.js - Gerenciamento de símbolos

let symbols = []; // Lista de símbolos carregados do backend

/**
 * Carrega os símbolos do backend e armazena na variável global.
 */
export async function loadSymbols() {
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

/**
 * Retorna a lista de símbolos carregados.
 * @returns {Array} Lista de símbolos.
 */
export function getSymbols() {
    return symbols;
}
