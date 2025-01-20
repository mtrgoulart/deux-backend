import { getSymbols } from './symbols.js';

export async function renderStrategy(strategy, container) {
    const { strategy_id, strategy_uuid, symbol, buy = {}, sell = {}, status, instanceName } = strategy;

    try {
        // Buscar o template do servidor
        const response = await fetch(`/get_html_template/strategy`);
        if (!response.ok) {
            throw new Error(`Failed to load template: ${response.statusText}`);
        }

        let template = await response.text();

        // Obter os símbolos carregados
        const symbols = await getSymbols(); // Certifique-se de que getSymbols retorna uma Promise
        const symbolOptions = symbols
            .map(s => `<option value="${s}" ${s === symbol ? 'selected' : ''}>${s}</option>`)
            .join('');

        // Substituir placeholders no template
        template = template
            .replace(/{{strategy_id}}/g, strategy_uuid)
            .replace(/{{symbols}}/g, symbolOptions);

        // Criar o elemento no DOM
        const strategyBox = document.createElement('div');
        strategyBox.innerHTML = template;
        container.appendChild(strategyBox);

        // Referências aos campos
        const buyPercentInput = document.getElementById(`percent-buy-${strategy_uuid}`);
        const buyConditionInput = document.getElementById(`condition_limit-buy-${strategy_uuid}`);
        const buyIntervalInput = document.getElementById(`interval-buy-${strategy_uuid}`);
        const buySimultaneousInput = document.getElementById(`simultaneous_operations-buy-${strategy_uuid}`);
        const sellPercentInput = document.getElementById(`percent-sell-${strategy_uuid}`);
        const sellConditionInput = document.getElementById(`condition_limit-sell-${strategy_uuid}`);
        const sellIntervalInput = document.getElementById(`interval-sell-${strategy_uuid}`);
        const saveButton = document.getElementById(`save-button-${strategy_uuid}`);
        const fields = strategyBox.querySelectorAll('input, select');

        // Preencher os valores do formulário
        buyPercentInput.value = buy.percent ? (buy.percent * 100).toFixed(2) : '';
        buyConditionInput.value = buy.condition_limit || '';
        buyIntervalInput.value = buy.interval || '';
        buySimultaneousInput.value = buy.simultaneous_operations || '';

        sellPercentInput.value = sell.percent ? (sell.percent * 100).toFixed(2) : '';
        sellConditionInput.value = sell.condition_limit || '';
        sellIntervalInput.value = sell.interval || '';

        // Inicializar os campos bloqueados e o botão como Edit
        fields.forEach(field => (field.disabled = true));
        saveButton.textContent = 'Edit';

        // Configurar o comportamento do botão Save/Edit
        saveButton.addEventListener('click', async () => {
            const isEditing = saveButton.textContent === 'Edit';

            if (isEditing) {
                // Modo Edit
                fields.forEach(field => (field.disabled = false));
                saveButton.textContent = 'Save';
            } else {
                // Modo Save

                const apiKey = localStorage.getItem('selectedApiKeyId');
                if (!apiKey) {
                    console.error('API Key is missing.');
                    alert('API Key is required to save the strategy.');
                    return;
                }

                const updatedStrategy = {
                    strategy_id: strategy_id || strategy_uuid, // Usar strategy_id ou strategy_uuid
                    instance_id: strategy.instance_id || null, // Garantir que instance_id está presente
                    api_key : apiKey,
                    instanceName: instanceName || null,
                    symbol: document.getElementById(`symbol-${strategy_uuid}`)?.value || null,
                    buy: {
                        percent: parseFloat(buyPercentInput.value) / 100 || 0,
                        condition_limit: parseInt(buyConditionInput.value) || 0,
                        interval: parseInt(buyIntervalInput.value) || 0,
                        simultaneous_operations: parseInt(buySimultaneousInput.value) || 1,
                    },
                    sell: {
                        percent: parseFloat(sellPercentInput.value) / 100 || 0,
                        condition_limit: parseInt(sellConditionInput.value) || 0,
                        interval: parseInt(sellIntervalInput.value) || 0,
                    },
                };
                

                // Validação simples
                if (!updatedStrategy.strategy_id || !updatedStrategy.instance_id || !updatedStrategy.symbol) {
                    console.error('Strategy ID, Instance ID, and Symbol are required.');
                    alert('Please provide all required fields: Strategy ID, Instance ID, and Symbol.');
                    return;
                }

                try {
                    // Enviar a estratégia ao servidor
                    const response = await fetch('/save_strategy', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(updatedStrategy),
                    });

                    const result = await response.json();

                    if (response.ok) {
                        console.log('Strategy saved successfully:', result);
                    } else {
                        console.error('Error saving strategy:', result.error);
                        alert('Failed to save strategy. Please try again.');
                    }
                } catch (error) {
                    console.error('Error during save_strategy call:', error);
                }

                // Após salvar, bloquear os campos novamente
                fields.forEach(field => (field.disabled = true));
                saveButton.textContent = 'Edit';
            }
        });
    } catch (error) {
        console.error('Error rendering strategy:', error);
    }
}
