export async function openIndicatorPopup(strategyId, side) {
    try {
        // Busca o template do indicador
        const response = await fetch(`/get_html_template/indicators`);
        if (!response.ok) {
            throw new Error(`Failed to load template: ${response.statusText}`);
        }

        // Substitui os placeholders no template
        let template = await response.text();
        template = template
            .replace(/{{strategy_id}}/g, strategyId)
            .replace(/{{side}}/g, side);

        // Cria o elemento do popup e adiciona ao DOM
        const popup = document.createElement('div');
        popup.id = `popup-${strategyId}-${side}`;
        popup.innerHTML = template;
        document.body.appendChild(popup);

        // Carrega os indicadores existentes
        await loadIndicators(strategyId, side);

        // Configura os eventos dos botões
        document.getElementById(`add-indicator-${strategyId}-${side}`).onclick = () =>
            addIndicator(strategyId, side);

        document.getElementById(`save-indicators-${strategyId}-${side}`).onclick = () =>
            saveIndicators(strategyId, side);

        document.getElementById(`close-popup-${strategyId}-${side}`).onclick = () =>
            popup.remove();
    } catch (error) {
        console.error('Error opening indicator popup:', error);
    }
}

async function loadIndicators(strategyId, side) {
    try {
        // Busca os indicadores do backend
        const response = await fetch(`/get_indicators?strategy_id=${strategyId}&side=${side}`);
        if (!response.ok) {
            throw new Error(`Failed to load indicators: ${response.statusText}`);
        }
        const { indicators } = await response.json();

        // Atualiza a lista de indicadores
        const indicatorsList = document.getElementById(`indicators-list-${strategyId}-${side}`);
        indicatorsList.innerHTML = ''; // Limpa a lista atual
        indicators.forEach((indicator) => addIndicatorElement(indicatorsList, indicator));
    } catch (error) {
        console.error('Error loading indicators:', error);
    }
}

function addIndicator(strategyId, side) {
    const indicatorId = crypto.randomUUID();
    const indicator = {
        id: indicatorId,
        strategy_id: strategyId,
        side: side,
        mandatory: false,
    };

    const indicatorsList = document.getElementById(`indicators-list-${strategyId}-${side}`);
    if (!indicatorsList) {
        console.error(`Indicators list not found for strategy ${strategyId} and side ${side}.`);
        return;
    }

    addIndicatorElement(indicatorsList, indicator);
}

function addIndicatorElement(container, indicator) {
    const indicatorDiv = document.createElement('div');
    indicatorDiv.id = `indicator-${indicator.id}`;
    indicatorDiv.innerHTML = `
        <p>Indicator ID: ${indicator.id}</p>
        <label>
            Mandatory: <input type="checkbox" id="mandatory-${indicator.id}" ${indicator.mandatory ? 'checked' : ''}>
        </label>
        <button id="remove-indicator-${indicator.id}">Remove</button>
    `;

    // Adicionar evento ao botão de remover
    indicatorDiv.querySelector(`#remove-indicator-${indicator.id}`).onclick = () =>
        removeIndicator(indicator.id);

    container.appendChild(indicatorDiv);

    // Verificação de existência do checkbox
    const mandatoryCheckbox = document.getElementById(`mandatory-${indicator.id}`);
    if (!mandatoryCheckbox) {
        console.error(`Failed to append mandatory checkbox for indicator ID ${indicator.id}.`);
    }
}

let removedIndicators = [];

function removeIndicator(indicatorId) {
    const indicatorElement = document.getElementById(`indicator-${indicatorId}`);
    if (indicatorElement) {
        // Adiciona o ID do indicador removido à lista
        removedIndicators.push(indicatorId);

        // Remove o elemento do DOM
        indicatorElement.remove();
    } else {
        console.error(`Indicator element not found for ID ${indicatorId}.`);
    }
}

async function saveIndicators(strategyId, side) {
    const indicatorsList = document.getElementById(`indicators-list-${strategyId}-${side}`);
    const currentIndicators = []; // Indicadores na tela

    // Certifique-se de que a lista de indicadores está presente
    if (!indicatorsList) {
        console.error(`Indicators list not found for strategy ${strategyId} and side ${side}.`);
        return;
    }

    // Coleta os dados dos indicadores na lista
    indicatorsList.querySelectorAll('div[id^="indicator-"]').forEach((indicatorElement) => {
        const indicatorId = indicatorElement.id.replace('indicator-', ''); // Remove o prefixo "indicator-"
        const mandatoryCheckbox = document.getElementById(`mandatory-${indicatorId}`);
        
        // Verifica se o checkbox existe antes de continuar
        if (!mandatoryCheckbox) {
            console.error(`Mandatory checkbox not found for indicator ID ${indicatorId}.`);
            return; // Ignora este indicador
        }

        const mandatory = mandatoryCheckbox.checked;
        currentIndicators.push({ id: indicatorId, strategy_id: strategyId, side, mandatory });
    });

    try {
        // Remove os indicadores no backend
        if (removedIndicators.length > 0) {
            console.log(`Removing indicators: ${removedIndicators}`);
            await fetch('/remove_indicators', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ indicators: removedIndicators }),
            });
            removedIndicators = []; // Limpa a lista de indicadores removidos
        }

        // Salva os indicadores restantes
        if (currentIndicators.length > 0) {
            const response = await fetch('/save_indicators', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ indicators: currentIndicators }),
            });

            const result = await response.json();
            if (response.ok) {
                console.log('Indicators saved successfully:', result);
                document.getElementById(`popup-${strategyId}-${side}`).remove();
            } else {
                console.error('Error saving indicators:', result.error);
            }
        }
    } catch (error) {
        console.error('Error saving indicators:', error);
    }
}