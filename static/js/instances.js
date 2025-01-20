import { renderStrategy } from './strategyRenderer.js';


/**
 * Carrega as instâncias associadas ao usuário e exibe suas estratégias vinculadas.
 */
export async function loadInstances(apiKeyId) {
    const loadingOverlay = document.getElementById('loading-overlay'); // Referência ao overlay

    // Exibe o overlay antes de iniciar o carregamento
    loadingOverlay.style.display = 'flex';

    try {
        console.log(`Loading instances for API Key: ${apiKeyId}`);
        const response = await fetch(`/get_instances?api_key_id=${apiKeyId}`);
        if (!response.ok) {
            throw new Error(`Failed to load instances: ${response.statusText}`);
        }

        const data = await response.json();
        const instancesContainer = document.getElementById('instances-container');

        // Limpa as instâncias existentes antes de carregar as novas
        instancesContainer.innerHTML = '';

        // Renderiza cada instância retornada
        data.instances.forEach(instance => renderInstance(instance, instancesContainer));
    } catch (error) {
        console.error("Error loading instances:", error);
        alert("Failed to load instances. Please try again.");
    } finally {
        // Remove o overlay após o carregamento
        loadingOverlay.style.display = 'none';
    }
}

/**
 * Renderiza uma instância e suas estratégias vinculadas.
 */
export async function renderInstance(instance) {
    console.log("Rendering instance:", instance);

    const container = document.getElementById("instances-container");

    // Cria o elemento para a instância
    const instanceElement = document.createElement('div');
    instanceElement.classList.add('instance-item');
    instanceElement.id = `instance-${instance.id}`;
    instanceElement.innerHTML = `
        <h3>${instance.name}</h3>
        <p><strong>Status:</strong> ${instance.status === 1 ? 'Active' : 'Inactive'}</p>
        <p><strong>Created At:</strong> ${new Date(instance.created_at).toLocaleString()}</p>
        <p><strong>Updated At:</strong> ${new Date(instance.updated_at).toLocaleString()}</p>
        <div class="strategies-container" id="strategies-container-${instance.id}">
            <h4>Strategies:</h4>
        </div>
        <div class="instance-actions">
            <button onclick="startInstance(${instance.id})">Start Instance</button>
            <button onclick="stopInstance(${instance.id})">Stop Instance</button>
            <button id="export-button-${instance.id}" class="export-button">Export Data</button>
        </div>
    `;

    container.appendChild(instanceElement);

    const strategiesContainer = document.getElementById(`strategies-container-${instance.id}`);

    try {
        // Busca as estratégias para esta instância
        const response = await fetch(`/get_instance_strategies/${instance.id}`);
        if (!response.ok) {
            throw new Error(`Failed to fetch strategies for instance ${instance.id}: ${response.statusText}`);
        }

        const data = await response.json();
        const strategies = data.strategies || [];

        if (strategies.length === 0) {
            strategiesContainer.innerHTML += `<p>No strategies found for this instance.</p>`;
            return;
        }

        // Renderiza cada estratégia
        strategies.forEach((strategy) => {
            renderStrategy(strategy, strategiesContainer);
        });
    } catch (error) {
        console.error(`Error fetching strategies for instance ${instance.id}:`, error);
    }

    // Adiciona o evento de clique ao botão Exportar Dados
    const exportButton = document.getElementById(`export-button-${instance.id}`);
    exportButton.addEventListener('click', async () => {
        try {
            const exportResponse = await fetch(`/get_instance_operations`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    instance_id: instance.id
                }),
            });
    
            if (!exportResponse.ok) {
                throw new Error(`Failed to export data: ${exportResponse.statusText}`);
            }
    
            // Extrair o CSV como blob
            const csvBlob = await exportResponse.blob();
    
            // Criar um link para download
            const downloadLink = document.createElement('a');
            const url = URL.createObjectURL(csvBlob);
            downloadLink.href = url;
            downloadLink.download = `instance_${instance.id}_data.csv`;
            document.body.appendChild(downloadLink);
    
            // Simular o clique para baixar
            downloadLink.click();
    
            // Remover o link após o download
            document.body.removeChild(downloadLink);
    
            console.log("Data exported successfully!");
        } catch (error) {
            console.error(`Error exporting data for instance ${instance.id}:`, error);
            alert("Failed to export data. Please try again.");
        }
    });
}


/**
 * Remove uma instância e suas estratégias associadas.
 */
export function removeInstance(instanceId) {
    const instanceElement = document.getElementById(`instance-${instanceId}`);

    if (!instanceElement) {
        console.error(`Instance with ID ${instanceId} not found.`);
        return;
    }

    fetch('/remove_instance', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ instance_id: instanceId }),
    })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Failed to remove instance: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                console.error(`Error removing instance ${instanceId}:`, data.error);
            } else {
                console.log(`Instance ${instanceId} removed successfully.`);
                instanceElement.remove();
            }
        })
        .catch(error => console.error("Error removing instance:", error));
}

/**
 * Salva uma nova instância com as estratégias associadas.
 */
export async function saveInstance(userId, apiKeyId, strategyId, instanceName) {
    try {
        const payload = {
            user_id: userId,
            api_key: apiKeyId,
            strategy: strategyId,
            name: instanceName,
        };

        const response = await fetch('/save_instance', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            throw new Error(`Failed to save instance: ${response.statusText}`);
        }

        const data = await response.json();

        if (!data.instance_id) {
            throw new Error("Backend did not return a valid instance ID.");
        }

        console.log(`Instance saved successfully with ID: ${data.instance_id}`);
        return {
            id: data.instance_id,
            name: instanceName,
            status: 1, // Padrão
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
        };
    } catch (error) {
        console.error("Error saving instance:", error);
        throw error;
    }
}


export function startInstance(instanceId, strategyId) {
    fetch('/start_instance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instance_id: instanceId, strategy_id: strategyId }),
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error(`Error starting instance ${instanceId}:`, data.error);
            } else {
                console.log(`Instance ${instanceId} started successfully.`);
                // Atualize a UI conforme necessário
            }
        })
        .catch(error => console.error('Error:', error));
}


export function stopInstance(instanceId) {
    fetch('/stop_instance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instance_id: instanceId }),
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error(`Error stopping instance ${instanceId}:`, data.error);
            } else {
                console.log(`Instance ${instanceId} stopped successfully.`);
                // Atualize a UI conforme necessário
            }
        })
        .catch(error => console.error('Error:', error));
}