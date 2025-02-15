// utilities.js - Funções utilitárias

/**
 * Valida que apenas números sejam inseridos.
 * @param {Event} event - Evento de entrada.
 */
export function validateNumericInput(event) {
    const input = event.target;
    input.value = input.value.replace(/[^0-9]/g, ''); // Remove caracteres não numéricos
}

/**
 * Formata o valor no campo Percent dinamicamente.
 * @param {Event} event - Evento de entrada.
 */
export function formatPercentInput(event) {
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
