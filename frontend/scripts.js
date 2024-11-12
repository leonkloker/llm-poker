document.addEventListener('DOMContentLoaded', () => {
    fetchStandings();
    fetchRandomGame();
});

function fetchStandings() {
    fetch('https://your-backend-domain.com/standings')
        .then(response => response.json())
        .then(data => {
            const standingsList = document.getElementById('standings-list');
            standingsList.innerHTML = '';
            for (const [model, score] of Object.entries(data)) {
                const listItem = document.createElement('li');
                listItem.textContent = `${model}: ${score}`;
                standingsList.appendChild(listItem);
            }
        })
        .catch(error => console.error('Error fetching standings:', error));
}

function fetchRandomGame() {
    fetch('https://your-backend-domain.com/random_game')
        .then(response => response.json())
        .then(data => {
            const gameAnimation = document.getElementById('game-animation');
            gameAnimation.textContent = `Game State: Pot - ${data.pot}`;
            // Implement animation based on game_state
        })
        .catch(error => console.error('Error fetching game:', error));
}