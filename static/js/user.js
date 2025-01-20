// user.js

/**
 * Carrega o nome do usuário do backend e atualiza no DOM.
 */
export async function loadUserName() {
    try {
        const response = await fetch('/get_user'); // Endpoint para obter os dados do usuário
        if (response.ok) {
            const data = await response.json();
            const userNameElement = document.getElementById('user-name');
            if (userNameElement) {
                userNameElement.textContent = data.name; // Atualiza o nome do usuário no DOM
            } else {
                console.error("User name element not found in DOM.");
            }
        } else {
            console.error("Failed to load user data:", response.statusText);
        }
    } catch (error) {
        console.error("Error loading user data:", error);
    }
}

/**
 * Configura o botão de logout.
 */
export function setupLogoutButton() {
    const logoutButton = document.getElementById('logout-button');

    if (!logoutButton) {
        console.error("Logout button not found in DOM.");
        return;
    }

    logoutButton.addEventListener('click', async () => {
        try {
            const response = await fetch('/logout', { method: 'POST' }); // Envia requisição para logout
            if (response.ok) {
                console.log("Logout successful");
                window.location.href = '/login'; // Redireciona para a página de login
            } else {
                console.error("Logout failed:", response.statusText);
                alert("Logout failed! Please try again.");
            }
        } catch (error) {
            console.error("Logout error:", error);
            alert("An error occurred while logging out.");
        }
    });
}
