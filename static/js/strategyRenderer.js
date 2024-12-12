import { getSymbols } from './symbols.js';
import { removeStrategySet } from './strategies.js';
import { openIndicatorPopup } from './indicators.js';

export async function renderStrategy(strategy) {
    const { strategy_id, symbol, buy = {}, sell = {}, status } = strategy;

    try {
        const response = await fetch(`/get_html_template/strategy`);
        if (!response.ok) {
            throw new Error(`Failed to load template: ${response.statusText}`);
        }

        let template = await response.text();

        // Substituir placeholders
        template = template
            .replace(/{{strategy_id}}/g, strategy_id)
            .replace(/{{status}}/g, status)
            .replace(
                /{{symbols}}/g,
                getSymbols()
                    .map((s) => `<option value="${s}" ${s === symbol ? 'selected' : ''}>${s}</option>`)
                    .join('')
            );

        // Criação do elemento no DOM
        const strategyBox = document.createElement('div');
        strategyBox.classList.add('strategy-box');
        strategyBox.id = strategy_id;

        // Define o atributo `data-saved` com base no status
        const isSaved = status === 'running' || status === 'stopped';
        strategyBox.setAttribute('data-saved', isSaved ? 'true' : 'false');
        strategyBox.innerHTML = template;

        const container = document.getElementById('operations-container');
        container.appendChild(strategyBox);

        // Preencher os valores do formulário
        if (buy) {
            document.getElementById(`percent-buy-${strategy_id}`).value = `${(buy.percent * 100).toFixed(2)}%`;
            document.getElementById(`condition_limit-buy-${strategy_id}`).value = buy.condition_limit || '';
            document.getElementById(`interval-buy-${strategy_id}`).value = buy.interval || '';
            document.getElementById(`simultaneous_operations-buy-${strategy_id}`).value = buy.simultaneous_operations || '';
        
            // REMOVIDO: Criação do botão de Indicators
        }
        
        if (sell) {
            document.getElementById(`percent-sell-${strategy_id}`).value = `${(sell.percent * 100).toFixed(2)}%`;
            const conditionLimitSell = document.getElementById(`condition_limit-sell-${strategy_id}`);
            const intervalSell = document.getElementById(`interval-sell-${strategy_id}`);
            conditionLimitSell.value = sell.condition_limit || '';
            intervalSell.value = sell.interval || '';
        
            if (status === 'stopped') {
                conditionLimitSell.disabled = false;
                intervalSell.disabled = false;
            }

            // Campos de "Sell" habilitados apenas se a estratégia estiver "stopped"
            if (status === 'stopped') {
                conditionLimitSell.disabled = false;
                intervalSell.disabled = false;
            }

            
        }

        // Configuração dos botões
        const saveButton = strategyBox.querySelector(`button[onclick="saveStrategy('${strategy_id}')"]`);
        const startButton = strategyBox.querySelector(`button[onclick="startStrategy('${strategy_id}')"]`);
        const stopButton = strategyBox.querySelector(`button[onclick="stopStrategy('${strategy_id}')"]`);
        const removeButton = strategyBox.querySelector(`button[onclick="removeStrategySet('${strategy_id}')"]`);

        // Ajuste dos botões com base no status
        if (status === 'running') {
            saveButton.disabled = true;
            startButton.disabled = true;
            stopButton.disabled = false;
        } else if (status === 'stopped') {
            saveButton.disabled = false;
            startButton.disabled = false;
            stopButton.disabled = true;
        }

        // Configura o botão de remoção
        removeButton.onclick = () => {
            const isSaved = strategyBox.getAttribute('data-saved') === 'true';
            if (!isSaved) {
                // Apenas remove o elemento do DOM
                console.log(`Strategy ${strategy_id} is not saved. Removing from frontend only.`);
                strategyBox.remove();
            } else {
                // Remove a estratégia salva no backend
                removeStrategySet(strategy_id);
            }
        };
    } catch (error) {
        console.error('Error rendering strategy:', error);
    }
}
