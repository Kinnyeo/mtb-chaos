from flask import Flask, render_template_string, request, redirect, session, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
import os, random, time, json, threading, datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
socketio = SocketIO(app, async_mode='threading')

# Stan gry
players = []
player_data = {}  # {nick: {'knowledge': 0, 'speed': 0, 'spalony': False, 'exchange_used': []}}
user_sids = {}      # globalnie na początku pliku
current_round = 0
current_minigame = None
server_room = "server_monitoring"
minigame_state = {}
exchange_offers = []
current_host = None  # Aktualny prowadzący
COLORS = ['biały', 'żółty', 'pomarańczowy', 'czerwony', 'różowy', 'fioletowy',
          'limonkowy', 'ciemnozielony', 'błękitny', 'niebieski', 'brązowy', 'szary', 'czarny']

# Load questions
with open('questions_ziemniak.json', 'r', encoding='utf-8') as f:
    questions_ziemniak = json.load(f)

used_questions = list()

# Styl CSS inspirowany serwerem Arduino
APP_CSS = '''
<style>
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

body {
  background: linear-gradient(135deg, #1a2a6c, #b21f1f, #1a2a6c);
  color: #fff;
  min-height: 100vh;
  padding: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

header {
  width: 100%;
  max-width: 1200px;
  background: rgba(0, 0, 0, 0.7);
  border-radius: 10px;
  padding: 20px;
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5);
}

.logo {
  font-size: 2.5rem;
  font-weight: bold;
  background: linear-gradient(to right, #ff8a00, #da1b60);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.player-info {
  background: rgba(255, 255, 255, 0.1);
  padding: 10px 20px;
  border-radius: 50px;
  font-size: 1.2rem;
  display: flex;
  align-items: center;
  gap: 15px;
}

.player-stats {
  display: flex;
  gap: 10px;
}

.stat {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 15px;
  border-radius: 20px;
  background: rgba(0, 0, 0, 0.4);
}

.stat-value {
  font-weight: bold;
  color: #ffcc00;
}

.container {
  width: 100%;
  max-width: 1200px;
  display: flex;
  gap: 20px;
  flex-direction: column;
}

.game-area {
  flex: 3;
  background: rgba(0, 0, 0, 0.7);
  border-radius: 15px;
  padding: 30px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.6);
  display: flex;
  flex-direction: column;
  min-height: 70vh;
}

.sidebar {
  flex: 1;
  background: rgba(0, 0, 0, 0.7);
  border-radius: 15px;
  padding: 20px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.6);
  display: flex;
  flex-direction: column;
  order: -1; /* Dla mobilnego - na górze */
}

.sidebar-horizontal {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
  margin-bottom: 20px;
}

.exchange-section-mobile {
  flex: 1;
  min-width: 250px;
}

.section-title {
  font-size: 1.5rem;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 2px solid #ff8a00;
  color: #ffcc00;
}

.players-list {
  list-style: none;
  margin-bottom: 20px;
}

.player-item {
  display: flex;
  justify-content: space-between;
  padding: 12px;
  margin: 8px 0;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  transition: all 0.3s;
}

.player-item:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: translateY(-2px);
}

.player-name {
  font-weight: bold;
}

.player-stats-mini {
  display: flex;
  gap: 10px;
}

.mini-stat {
  font-size: 0.9rem;
  color: #ffcc00;
}

.minigame-title {
  text-align: center;
  font-size: 4rem;
  margin: 20px 0;
  color: #ffcc00;
  text-shadow: 0 0 10px rgba(255, 204, 0, 0.5);
}

.minigame-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 30px;
  padding: 20px;
}

.countdown {
  font-size: 5rem;
  font-weight: bold;
  color: #ff8a00;
  text-shadow: 0 0 20px rgba(255, 138, 0, 0.8);
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0% { transform: scale(1); }
  50% { transform: scale(1.1); }
  100% { transform: scale(1); }
}

.question-box {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 15px;
  padding: 25px;
  width: 90%;
  text-align: center;
  font-size: 3rem;
  line-height: 1.6;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.4);
}

.controls {
  display: flex;
  justify-content: center;
  gap: 20px;
  flex-wrap: wrap;
  margin-top: 30px;
}

.btn {
  font-size: 2rem;
  padding: 30px 60px;
  border: none;
  border-radius: 50px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.3s;
  background: linear-gradient(to right, #ff8a00, #da1b60);
  color: white;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3);
}

.btn:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 15px rgba(0, 0, 0, 0.4);
}

.btn:active {
  transform: translateY(1px);
}

.btn:disabled {
  background: #555;
  cursor: not-allowed;
}

.answer-buttons {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  width: 80%;
  margin-top: 20px;
}

.answer-btn {
  height: 350px;
  padding: 20px;
  font-size: 6rem;
  border-radius: 10px;
  background: white;
  border: none;
  color: black;
  cursor: pointer;
  transition: all 0.3s;
}

.selected-answer {
    background: #4CAF50 !important; /* Zielony dla wybranej odpowiedzi */
    color: white !important;
    transform: scale(1.05);
    box-shadow: 0 0 20px rgba(76, 175, 80, 0.6);
}

.unselected-answer {
    background: #9E9E9E !important; /* Szary dla pozostałych */
    color: #616161 !important;
}

.selected-difficulty {
    background: #4CAF50 !important; /* Zielony dla wybranego poziomu */
    color: white !important;
}

.unselected-difficulty {
    background: #9E9E9E !important; /* Szary dla pozostałych */
    color: #616161 !important;
}

.answer-btn.selected-answer {
    background: #4CAF50 !important; /* Zielony dla wybranej odpowiedzi */
    color: white !important;
    transform: scale(1.05);
    box-shadow: 0 0 20px rgba(76, 175, 80, 0.6);
}

.answer-btn.disabled-answer {
    background: #9E9E9E !important; /* Szary dla pozostałych */
    color: #616161 !important;
    cursor: not-allowed;
}

.answer-btn.disabled-answer:hover {
    transform: none;
    box-shadow: none;
}

.answer-btn2 {
  height: 200px;
  padding: 20px;
  font-size: 3rem;
  border-radius: 10px;
  background: white;
  border: none;
  color: black;
  cursor: pointer;
  transition: all 0.3s;
}

.answer-btn:hover {
  transform: scale(1.05);
  box-shadow: 0 0 20px rgba(52, 152, 219, 0.6);
}

.color-buttons {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 50px;
  width: 90%;
}

.color-btn {
  height: 350px;
  border-radius: 15px;
  border: none;
  cursor: pointer;
  transition: all 0.3s;
  font-size: 1.4rem;
  font-weight: bold;
  text-shadow: 1px 1px 3px rgba(0,0,0,0.7);
}

.color-btn:hover {
  transform: scale(1.05);
  box-shadow: 0 0 25px rgba(255,255,255,0.6);
}

.spalony-btn {
  background: linear-gradient(135deg, #e74c3c, #c0392b);
  font-size: 4rem;
  padding: 90px 120px;
  display: none; /* Domyślnie ukryty */
}

.exchange-section {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 15px;
  padding: 20px;
  margin-top: 20px;
}

.exchange-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 15px;
}

.exchange-card {
  background: rgba(0, 0, 0, 0.4);
  border-radius: 10px;
  padding: 15px;
  border: 1px solid #ff8a00;
}

.exchange-cost {
  color: #ffcc00;
  font-weight: bold;
  margin: 10px 0;
}

.exchange-btn {
  background: linear-gradient(to right, #27ae60, #2ecc71);
  width: 100%;
  padding: 10px;
  border: none;
  border-radius: 5px;
  color: white;
  cursor: pointer;
}

.timer-display {
  font-size: 6rem;
  font-weight: bold;
  margin: 20px 0;
  color: #ffcc00;
  text-shadow: 0 0 15px rgba(255, 204, 0, 0.7);
}

.server-color {
  width: 200px;
  height: 200px;
  border-radius: 50%;
  margin: 30px auto;
  box-shadow: 0 0 40px rgba(255,255,255,0.7);
  transition: background-color 0.25s;
}

#notification {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  padding: 15px 30px;
  border-radius: 50px;
  background: linear-gradient(to right, #27ae60, #2ecc71);
  color: white;
  font-weight: bold;
  box-shadow: 0 4px 15px rgba(0,0,0,0.3);
  z-index: 1000;
  display: none;
}

.host-info {
  background: rgba(255, 215, 0, 0.2);
  border-radius: 10px;
  padding: 15px;
  margin: 15px 0;
  text-align: center;
  border: 2px solid gold;
}

.host-label {
  font-size: 2rem;
  font-weight: bold;
  color: gold;
}

.host-name {
  font-size: 2rem;
  font-weight: bold;
  margin-top: 5px;
}

@media (min-width: 768px) {
  .container {
    flex-direction: row;
  }

  .sidebar {
    order: 0; /* Dla desktop - na boku */
  }

  .sidebar-horizontal {
    display: none; /* Ukryj poziomy pasek na desktop */
  }
}

@media (max-width: 768px) {
  .btn {
    padding: 12px 20px;
    font-size: 1rem;
  }

  .countdown {
    font-size: 3rem;
  }

  .answer-buttons, .color-buttons {
    grid-template-columns: 1fr;
  }

  .exchange-btn {
    padding: 15px;
    font-size: 1.1rem;
  }

  .sidebar-horizontal {
    display: flex; /* Pokaż poziomy pasek na mobile */
  }

  .sidebar {
    display: none; /* Ukryj pionowy pasek na mobile */
  }
}
</style>
'''

# Szablony HTML
INDEX_HTML = APP_CSS + '''
<!DOCTYPE html>
<html>
<head>
  <title>MTB:Chaos - Logowanie</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
  <header>
    <div class="logo">MTB:Chaos</div>
  </header>

  <div class="game-area" style="justify-content: center; align-items: center;">
    <div style="text-align: center; max-width: 500px;">
      <h1 style="font-size: 2.5rem; margin-bottom: 30px;">Witaj w MTB:Chaos!</h1>
      <p style="font-size: 1.2rem; margin-bottom: 40px;">
        Dołącz do ekscytującej gry pełnej pytań, wyzwań i szybkich decyzji. Podaj swój nick aby rozpocząć!
      </p>

      <form method="POST" style="display: flex; flex-direction: column; gap: 20px;">
        <input type="text" name="nick" required 
               placeholder="Twój nick" 
               style="padding: 15px; font-size: 1.2rem; border-radius: 50px; border: none; text-align: center;">
        <button type="submit" class="btn">Dołącz do gry</button>
      </form>
    </div>
  </div>

  <div id="notification"></div>
</body>
</html>
'''

LOBBY_HTML = APP_CSS + '''
<!DOCTYPE html>
<html>
<head>
  <title>Lobby - MTB:Chaos</title>
  <script src="//cdnjs.cloudflare.com/ajax/libs/socket.io/4.5.4/socket.io.min.js"></script>
</head>
<body>
  <header>
    <div class="logo">MTB:Chaos</div>
    <div class="player-info">
      <div>Witaj, <span style="font-weight: bold; color: #ffcc00;">{{ nick }}</span>!</div>
      <div class="player-stats">
        <div class="stat">Wiedza: <span class="stat-value">{{ player_data.knowledge }}</span></div>
        <div class="stat">Chyżość: <span class="stat-value">{{ player_data.speed }}</span></div>
      </div>
    </div>
  </header>

  <div class="container">
    <div class="game-area">
      <h1 class="minigame-title">LOBBY GRACZY</h1>

      <div style="text-align: center; margin: 40px 0;">
        <h2 style="font-size: 1.8rem; margin-bottom: 20px;">Oczekiwanie na rozpoczęcie gry</h2>
        <p style="font-size: 1.2rem; margin-bottom: 30px;">
          Obecnie w lobby: <span id="player-count">{{ players|length }}</span> graczy
        </p>
        <button class="btn" onclick="startGame()">Rozpocznij grę</button>
      </div>
    </div>

    <div class="sidebar">
      <div class="host-info">
        <div class="host-label">Prowadzący:</div>
        <div class="host-name" id="current-host">{{ current_host or 'Brak' }}</div>
      </div>

      <h2 class="section-title">Gracze online</h2>
      <ul class="players-list" id="players-list">
        {% for player in players %}
        <li class="player-item">
          <div class="player-name">{{ player }}</div>
          <div class="player-stats-mini">
            <div class="mini-stat">W: {{ player_data[player].knowledge }}</div>
            <div class="mini-stat">C: {{ player_data[player].speed }}</div>
          </div>
        </li>
        {% endfor %}
      </ul>

      <div class="exchange-section">
        <h2 class="section-title">Wymiana punktów</h2>
        <div class="exchange-grid">
          <div class="exchange-card">
            <h3>Losowanie kolorów</h3>
            <p>Zmień kolory u innych graczy</p>
            <div class="exchange-cost">Koszt: 1 punkt chyżości</div>
            <button class="exchange-btn" onclick="buyExchange(1)">Wykup</button>
          </div>

          <div class="exchange-card">
            <h3>Natychmiastowy ziemniak</h3>
            <p>Przejdź od razu do gry "Gorący ziemniak"</p>
            <div class="exchange-cost">Koszt: 2 punkty chyżości</div>
            <button class="exchange-btn" onclick="buyExchange(2)">Wykup</button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div id="notification"></div>

  <script>
    const nick = "{{ nick }}";
    const socket = io();

    socket.on('connect', () => {
      socket.emit('join', nick);
    });

    socket.on('player_list', function(data) {
      const playersList = document.getElementById('players-list');
      playersList.innerHTML = '';

      data.players.forEach(player => {
        const playerItem = document.createElement('li');
        playerItem.className = 'player-item';
        playerItem.innerHTML = `
          <div class="player-name">${player}</div>
          <div class="player-stats-mini">
            <div class="mini-stat">W: ${data.player_data[player].knowledge}</div>
            <div class="mini-stat">C: ${data.player_data[player].speed}</div>
          </div>
        `;
        playersList.appendChild(playerItem);
      });

      document.getElementById('player-count').textContent = data.players.length;
      document.getElementById('current-host').textContent = data.current_host || 'Brak';
    });

    socket.on('game_started', function() {
      window.location.href = "/game";
    });

    socket.on('notification', function(data) {
      const notification = document.getElementById('notification');
      notification.textContent = data.message;
      notification.style.display = 'block';
      setTimeout(() => { notification.style.display = 'none'; }, 3000);
    });

    function startGame() {
      socket.emit('start_game');
    }

    function buyExchange(exchangeId) {
      socket.emit('buy_exchange', {exchange_id: exchangeId, nick: nick});
    }
  </script>
</body>
</html>
'''

GAME_HTML = APP_CSS + '''
<!DOCTYPE html>
<html>
<head>
  <title>Gra - MTB:Chaos</title>
  <script src="//cdnjs.cloudflare.com/ajax/libs/socket.io/4.5.4/socket.io.min.js"></script>
</head>
<body>
  <header>
    <div class="logo">MTB:Chaos</div>
    <div class="player-info">
      <div>Gracz: <span style="font-weight: bold; color: #ffcc00;">{{ nick }}</span></div>
      <div class="player-stats">
        <div class="stat">Wiedza: <span class="stat-value" id="knowledge">{{ player_data.knowledge }}</span></div>
        <div class="stat">Chyżość: <span class="stat-value" id="speed">{{ player_data.speed }}</span></div>
      </div>
    </div>
  </header>

  <div class="sidebar-horizontal">
    <div class="exchange-section-mobile">
      <div class="host-info">
        <div class="host-label">Prowadzący:</div>
        <div class="host-name" id="current-host">{{ current_host or 'Brak' }}</div>
      </div>
    </div>

    <div class="exchange-section-mobile">
      <h2 class="section-title">Wymiana punktów</h2>
      <div class="exchange-grid" id="exchange-grid-mobile">
        <!-- Oferty wymiany dla mobile -->
      </div>
    </div>
  </div>

  <div class="container">
    <div class="sidebar">
      <div class="host-info">
        <div class="host-label">Prowadzący:</div>
        <div class="host-name" id="current-host-desktop">{{ current_host or 'Brak' }}</div>
      </div>

      <div class="exchange-section">
        <h2 class="section-title">Wymiana punktów</h2>
        <div class="exchange-grid" id="exchange-grid">
          <!-- Oferty wymiany -->
        </div>
      </div>
    </div>

    <div class="game-area">
      <h1 class="minigame-title" id="minigame-title"></h1>

      <div class="minigame-content" id="minigame-content">
        <!-- Zawartość dynamiczna -->
      </div>
    </div>
  </div>

  <div id="notification"></div>

  <script>
    const nick = "{{ nick }}";
    const socket = io();
    let isHost = false;

    socket.on('connect', () => {
      socket.emit('join_game', nick);
    });

    socket.on('update_players', function(data) {
      document.getElementById('current-host').textContent = data.current_host || 'Brak';
      document.getElementById('current-host-desktop').textContent = data.current_host || 'Brak';
      document.getElementById('knowledge').textContent = data.player_data[nick].knowledge;
      document.getElementById('speed').textContent = data.player_data[nick].speed;

      isHost = (data.current_host === nick);
    });

    socket.on('start_minigame', function(data) {
      document.getElementById('minigame-title').textContent = data.title;
      const contentDiv = document.getElementById('minigame-content');
      contentDiv.innerHTML = '';

      if (data.type === 'countdown') {
        showUI();
        contentDiv.innerHTML = `
          <div class="countdown">${data.time}</div>
          <div class="question-box">${data.message}</div>
        `;
      }
      if (data.type === 'await_host') {
        showUI();
        if (isHost) {
            contentDiv.innerHTML = `
              <div class="question-box">Losuj następną minigrę</div>
              <button class="btn" onclick="nextMinigame()">LOSUJ</button>
            `;               
        } else { 
            contentDiv.innerHTML = `
              <div class="question-box">Oczekiwanie na prowadzącego...</div>
            `;        
        }
      }
      else if (data.type === 'goracy_ziemniak') {
        hideUI();
        contentDiv.innerHTML = `
          <div class="question-box">${data.question}</div>
          <button class="btn spalony-btn" id="spalony-btn" style="display:none" onclick="markSpalony()">SPALONY!</button>
        `;
      }
      else if (data.type === 'kolory') {
        hideUI();
        const colorsHtml = data.colors.map((color, index) => 
          `<button class="color-btn" style="background: ${getColorHex(color)};" 
                  onclick="selectColor('${color}')"></button>`
        ).join('');

        contentDiv.innerHTML = `
          <div class="color-buttons">${colorsHtml}</div>
        `;
      }
      else if (data.type === 'timekeeper') {
        hideUI();
        contentDiv.innerHTML = `
          <button class="btn" id="time-btn" onclick="stopTimer()">STOP</button>
        `;
      }
      else if (data.type === 'pytania') {
        hideUI();
        debugg('pytania');
        if (isHost) {
          contentDiv.innerHTML = `
            <div class="question-box">Przeczytaj pytanie oraz odpowiedzi i kliknij START</div>
            <button class="btn" onclick="startQuestion()">START</button>
          `;
        } else {
          contentDiv.innerHTML = `
            <div class="question-box">Poczekaj na przeczytanie pytania oraz odpowiedzi</div>
          `;
        }
      }
      resetAnswerButtons();  // Reset przycisków przy nowej grze
    });

    socket.on('minigame_update', function(data) {
      if (data.type === 'pytania') {
        const contentDiv = document.getElementById('minigame-content');
        contentDiv.innerHTML = '';

        if (data.phase === 'host_waiting' && isHost) {
          contentDiv.innerHTML = `
            <div class="question-box">${data.message}</div>
            <button class="btn" onclick="startQuestion()">START</button>
          `;
        }
        else if (data.phase === 'host_selecting' && isHost) {
                resetSelections();
                
                const answerButtons = data.options.map(opt => 
                    `<button class="answer-btn" onclick="selectCorrect(this, '${opt}')">${opt}</button>`
                ).join('');

                const difficultyButtons = data.difficulties.map(diff => 
                    `<button class="answer-btn2" onclick="selectDifficulty(this, ${diff})">Poziom ${diff}</button>`
                ).join('');

                contentDiv.innerHTML = `
                    <div class="question-box">
                        <h3>Wybierz poprawną odpowiedź:</h3>
                        <div class="answer-buttons">${answerButtons}</div>

                        <h3 style="margin-top: 20px;">Wybierz poziom trudności:</h3>
                        <div class="answer-buttons">${difficultyButtons}</div>

                        <button class="btn" id="confirm-btn" style="margin-top: 20px; display: none;" 
                                onclick="confirmSelection()">Potwierdź</button>
                    </div>
                `;
        }
        else if (data.phase === 'player_waiting') {
          contentDiv.innerHTML = `
            <div class="question-box">${data.message}</div>
          `;
        }
        else if (data.phase === 'answering') {
          if (isHost) {
              contentDiv.innerHTML = `
                <div class="question-box">Poczekaj na odpowiedzi uczestników...</div>
              `;
          }
          else {
            let buttonsHtml = '';
              if (data.options) {
                buttonsHtml = data.options.map(opt => 
                  `<button class="answer-btn" onclick="submitAnswer('${opt}')">${opt}</button>`
                ).join('');
              }
    
              contentDiv.innerHTML = `
                <div class="answer-buttons">${buttonsHtml}</div>
              `;
          }
        }
        else if (data.phase === 'host_selecting' && isHost) {
          const answerButtons = data.options.map(opt => 
            `<button class="answer-btn" onclick="selectCorrect('${opt}')">${opt}</button>`
          ).join('');

          const difficultyButtons = data.difficulties.map(diff => 
            `<button class="answer-btn2" onclick="selectDifficulty(${diff})">Poziom ${diff}</button>`
          ).join('');

          contentDiv.innerHTML = `
            <div class="question-box">
              <h3>Wybierz poprawną odpowiedź:</h3>
              <div class="answer-buttons">${answerButtons}</div>

              <h3 style="margin-top: 20px;">Wybierz poziom trudności:</h3>
              <div class="answer-buttons">${difficultyButtons}</div>

              <button class="btn" id="confirm-btn" style="margin-top: 20px; display: none;" 
                      onclick="confirmSelection()">Potwierdź</button>
            </div>
          `;
        }
        else if (data.phase === 'host_selecting' && !isHost) {
          contentDiv.innerHTML = `
            <div class="question-box">Czekaj na wynik...</div>
          `;
        }
      }
    });

    socket.on('minigame_results', function(data) {
      const contentDiv = document.getElementById('minigame-content');
      showUI();
      
      if (data.type === 'pytania') {
          if (data.phase === 'answering'){
              contentDiv.innerHTML = `
                <div class="timer-display">${data.time_left}</div>
              `;
          }
          else {
            let resultsHtml = `<div class="question-box"><h2>Wyniki pytania</h2><ul>`;
    
            for (const [player, points] of Object.entries(data.results)) {
              let pointsInfo = '';
              if (points.knowledge > 0) pointsInfo += `Wiedza: +${points.knowledge} `;
              if (points.speed > 0) pointsInfo += `Chyżość: +${points.speed}`;
    
              resultsHtml += `<li><strong>${player}:</strong> ${pointsInfo || '0'}</li>`;
            }
    
            resultsHtml += `</ul></div>`;
            if (isHost) {
              resultsHtml += `<button class="btn" onclick="nextRound()">Dalej</button>`;
            }
            contentDiv.innerHTML = resultsHtml;
          }
      }
      else if (data.type === 'kolory') {
        let resultsHtml = `<div class="question-box"><h2>Wyniki rundy</h2><ul>`;

        data.results.forEach(result => {
          resultsHtml += `<li>${result.player}: +${result.points} pkt chyżości (${result.reason})</li>`;
        });

        resultsHtml += `</ul></div>`;
        if (isHost) {
          resultsHtml += `<button class="btn" onclick="nextRound()">Dalej</button>`;
        }
        contentDiv.innerHTML = resultsHtml;
      }
      else if (data.type === 'timekeeper') {
        let resultsHtml = `<div class="question-box"><h2>Wyniki Chronometrażysty</h2><table style="width:100%;">`;
        resultsHtml += `<tr><th>Gracz</th><th>Czas</th><th>Różnica</th><th>Punkty</th></tr>`;

        data.results.forEach(result => {
          resultsHtml += `<tr>
            <td>${result.player}</td>
            <td>${result.time.toFixed(3)}s</td>
            <td>${result.diff.toFixed(3)}s</td>
            <td>${result.points}</td>
          </tr>`;
        });

        resultsHtml += `</table></div>`;
        if (isHost) {
          resultsHtml += `<button class="btn" onclick="nextRound()">Dalej</button>`;
        }
        contentDiv.innerHTML = resultsHtml;
      }
      else if (data.type === 'ziemniak') {
        // pod komunikatem o spaleniu dokładamy informację o -2 pkt
        const lostInfo = data.lost_speed
          ? `<p style="margin-top:10px; color:#ff6666; font-weight:bold;">
               -${data.lost_speed} pkt chyżości
             </p>`
          : ``;
    
        contentDiv.innerHTML = `
          <div class="question-box">
            <h2>${data.message}</h2>
            ${lostInfo}
            ${isHost ? '<button class="btn" onclick="nextRound()">Dalej</button>' : ''}
          </div>
        `;
      }
    });

    socket.on('activate_spalony', function() {
      document.getElementById('spalony-btn').style.display = 'block';
      document.getElementById('minigame-title').textContent = "Ziemniak wybuchł!";
    });

    socket.on('notification', function(data) {
      const notification = document.getElementById('notification');
      notification.textContent = data.message;
      notification.style.display = 'block';
      setTimeout(() => { notification.style.display = 'none'; }, 3000);
    });

      socket.on('update_exchanges', function(data) {
        const desktop = document.getElementById('exchange-grid');
        const mobile  = document.getElementById('exchange-grid-mobile');
        desktop.innerHTML = '';
        mobile.innerHTML  = '';
    
        data.exchanges.forEach(ex => {
          const card = document.createElement('div');
          card.className = 'exchange-card';
          card.innerHTML = `
            <h3>${ex.name}</h3>
            <p>${ex.description}</p>
            <div class="exchange-cost">Koszt: ${ex.cost} pkt chyżości</div>
            <button class="exchange-btn" onclick="buyExchange(${ex.id})">
              Wykup
            </button>
          `;
          desktop.appendChild(card);
          mobile.appendChild(card.cloneNode(true));
        });
      });

    function getColorHex(colorName) {
      const colors = {
        'biały': '#ffffff', 'żółty': '#ffff00', 'pomarańczowy': '#ffa500',
        'czerwony': '#ff0000', 'różowy': '#ff69b4', 'fioletowy': '#800080',
        'limonkowy': '#00ff00', 'ciemnozielony': '#006400', 'błękitny': '#00bfff',
        'niebieski': '#0000ff', 'brązowy': '#8b4513', 'szary': '#808080',
        'czarny': '#000000'
      };
      return colors[colorName] || '#333';
    }

    function hideUI() {
       document.querySelector('header').style.display = 'none';
       document.querySelector('.sidebar').style.display = 'none';
       document.querySelector('.sidebar-horizontal').style.display = 'none';
    }
    
    function showUI() {
      document.querySelector('header').style.display = '';
      document.querySelector('.sidebar').style.display = '';
      document.querySelector('.sidebar-horizontal').style.display = '';
    }

    function markSpalony() {
      socket.emit('spalony', nick);
    }

    function selectColor(color) {
      socket.emit('select_color', {color: color, nick: nick});
    }

    function submitAnswer(answer) {
        // Zaznacz wybraną odpowiedź i dezaktywuj przyciski
        const buttons = document.querySelectorAll('.answer-btn');
        buttons.forEach(btn => {
            btn.disabled = true;
            if (btn.textContent === answer) {
                btn.classList.add('selected-answer');
            } else {
                btn.classList.add('disabled-answer');
            }
        });
      socket.emit('submit_answer', {answer: answer, nick: nick});
    }
    
    function resetAnswerButtons() {
        const buttons = document.querySelectorAll('.answer-btn');
        buttons.forEach(btn => {
            btn.disabled = false;
            btn.classList.remove('selected-answer', 'disabled-answer');
        });
    }

    function startQuestion() {
      socket.emit('start_question');
    }

    function stopTimer() {
      const endTime = Date.now();
      socket.emit('stop_timer', {nick: nick, time: endTime});
      document.getElementById('time-btn').disabled = true;
    }
    
    function nextMinigame() {
        socket.emit('next_minigame');
    }
    
    function debugg(txt) {
        socket.emit('debugg', {text: txt});
    }

    function nextRound() {
      socket.emit('next_round');
    }

    function buyExchange(exchangeId) {
      socket.emit('buy_exchange', {exchange_id: exchangeId, nick: nick});
    }

    let selectedAnswer = null;
    let selectedDifficulty = null;

    function selectCorrect(button, answer) {
        // Usuń selekcję ze wszystkich przycisków odpowiedzi
        const answerButtons = document.querySelectorAll('.answer-btn');
        answerButtons.forEach(btn => {
            btn.classList.remove('selected-answer');
            btn.classList.add('unselected-answer');
        });
        
        // Zaznacz wybrany przycisk
        button.classList.remove('unselected-answer');
        button.classList.add('selected-answer');
        
        selectedAnswer = answer;
        checkSelection();
    }

    function selectDifficulty(button, difficulty) {
        // Usuń selekcję ze wszystkich przycisków trudności
        const difficultyButtons = document.querySelectorAll('.answer-btn2');
        difficultyButtons.forEach(btn => {
            btn.classList.remove('selected-difficulty');
            btn.classList.add('unselected-difficulty');
        });
        
        // Zaznacz wybrany przycisk
        button.classList.remove('unselected-difficulty');
        button.classList.add('selected-difficulty');
        
        selectedDifficulty = difficulty;
        checkSelection();
    }
    
    function resetSelections() {
        const answerButtons = document.querySelectorAll('.answer-btn');
        const difficultyButtons = document.querySelectorAll('.answer-btn2');
        
        answerButtons.forEach(btn => {
            btn.classList.remove('selected-answer', 'unselected-answer');
        });
        
        difficultyButtons.forEach(btn => {
            btn.classList.remove('selected-difficulty', 'unselected-difficulty');
        });
        
        selectedAnswer = null;
        selectedDifficulty = null;
    }

    function checkSelection() {
      if (selectedAnswer && selectedDifficulty) {
        document.getElementById('confirm-btn').style.display = 'block';
      }
    }

    function confirmSelection() {
      socket.emit('set_correct_answer', {
        answer: selectedAnswer, 
        difficulty: selectedDifficulty,
        nick: nick
      });
    }
  </script>
</body>
</html>
'''

SERVER_HTML = APP_CSS + '''
<!DOCTYPE html>
<html>
<head>
  <title>Serwer - MTB:Chaos</title>
  <script src="//cdnjs.cloudflare.com/ajax/libs/socket.io/4.5.4/socket.io.min.js"></script>
</head>
<body>
  <header>
    <div class="logo">MTB:Chaos - Serwer</div>
  </header>

  <div class="container">
    <div class="game-area">
      <h1 class="minigame-title" id="minigame-title">Oczekiwanie na grę</h1>

      <div class="minigame-content" id="minigame-content">
        <!-- Zawartość dynamiczna -->
      </div>
    </div>

    <div class="sidebar">
      <div class="host-info">
        <div class="host-label">Prowadzący:</div>
        <div class="host-name" id="current-host">Brak</div>
      </div>

      <h2 class="section-title">Gracze</h2>
      <ul class="players-list" id="players-list">
        <!-- Lista graczy -->
      </ul>
    </div>
  </div>

  <div id="notification"></div>

  <script>
    const socket = io();

    socket.on('connect', () => {
      socket.emit('join_server');
    });

    socket.on('update_players', function(data) {
      const playersList = document.getElementById('players-list');
      playersList.innerHTML = '';

      data.players.forEach(player => {
        const playerItem = document.createElement('li');
        playerItem.className = 'player-item';
        playerItem.innerHTML = `
          <div class="player-name">${player}</div>
          <div class="player-stats-mini">
            <div class="mini-stat">W: ${data.player_data[player].knowledge}</div>
            <div class="mini-stat">C: ${data.player_data[player].speed}</div>
          </div>
        `;
        playersList.appendChild(playerItem);
      });

      document.getElementById('current-host').textContent = data.current_host || 'Brak';
    });

    socket.on('start_minigame', function(data) {
      document.getElementById('minigame-title').textContent = data.title;
      const contentDiv = document.getElementById('minigame-content');
      contentDiv.innerHTML = '';

      if (data.type === 'countdown') {
        contentDiv.innerHTML = `
          <div class="countdown">${data.time}</div>
          <div class="question-box">${data.message}</div>
        `;
        if (data.time <= 3) {
          // Dodaj dźwięk odliczania w ostatnich sekundach
          const audio = new Audio('https://www.soundjay.com/buttons/button-19.mp3');
          audio.play();
        }
      }
      else if (data.type === 'await_host') {
            contentDiv.innerHTML = `
              <div class="question-box">Oczekiwanie na prowadzącego...</div>
            `;        
      }
      else if (data.type === 'goracy_ziemniak') {
        contentDiv.innerHTML = `
          <div class="question-box">${data.question}</div>
        `;
      }
      else if (data.type === 'kolory') {
        contentDiv.innerHTML = `
          <div class="server-color" id="server-color" 
               style="background: ${getColorHex(data.server_color)};"></div>
        `;
      }
      else if (data.type === 'timekeeper') {
        contentDiv.innerHTML = `
          <div class="question-box">Czas docelowy: ${data.target_time.toFixed(3)}s</div>
        `;
      }
      else if (data.type === 'pytania') {
        contentDiv.innerHTML = `
          <div class="question-box">Poczekaj na przeczytanie pytania oraz odpowiedzi</div>
        `;
      }
    });

    socket.on('minigame_update', function(data) {
        if (data.type === 'pytania') {
            if (data.phase === 'answering') {
                const contentDiv = document.getElementById('minigame-content');
                contentDiv.innerHTML = `
                    <div class="timer-display">${data.time_left}</div>
                    <div class="question-box">Trwa odpowiadanie na pytanie...</div>
                `;
            } else if (data.phase === 'host_selecting') {
                const contentDiv = document.getElementById('minigame-content');
                contentDiv.innerHTML = `
                    <div class="question-box">Prowadzący wskazuje poprawną odpowiedź...</div>
                `;
            }
        }
    });

    socket.on('minigame_results', function(data) {
      const contentDiv = document.getElementById('minigame-content');
      let resultsHtml = '';

      if (data.type === 'pytania') {
        resultsHtml = `<div class="question-box"><h2>Wyniki pytania</h2><ul>`;

        for (const [player, points] of Object.entries(data.results)) {
          let pointsInfo = '';
          if (points.knowledge > 0) pointsInfo += `Wiedza: +${points.knowledge} `;
          if (points.speed > 0) pointsInfo += `Chyżość: +${points.speed}`;

          resultsHtml += `<li><strong>${player}:</strong> ${pointsInfo || '0'}</li>`;
        }

        resultsHtml += `</ul></div>`;
      }
      else if (data.type === 'kolory') {
        resultsHtml = `<div class="question-box"><h2>Wyniki rundy</h2><ul>`;

        data.results.forEach(result => {
          resultsHtml += `<li>${result.player}: +${result.points} pkt chyżości (${result.reason})</li>`;
        });

        resultsHtml += `</ul></div>`;
      }
      else if (data.type === 'timekeeper') {
        resultsHtml = `<div class="question-box"><h2>Wyniki Chronometrażysty</h2><table style="width:100%;">`;
        resultsHtml += `<tr><th>Gracz</th><th>Czas</th><th>Różnica</th><th>Punkty</th></tr>`;

        data.results.forEach(result => {
          resultsHtml += `<tr>
            <td>${result.player}</td>
            <td>${result.time.toFixed(3)}s</td>
            <td>${result.diff.toFixed(3)}s</td>
            <td>${result.points}</td>
          </tr>`;
        });

        resultsHtml += `</table></div>`;
      }
      else if (data.type === 'ziemniak') {
        resultsHtml = `<div class="question-box"><h2>${data.message}</h2></div>`;
      }

      contentDiv.innerHTML = resultsHtml;
    });

    socket.on('notification', function(data) {
      const notification = document.getElementById('notification');
      notification.textContent = data.message;
      notification.style.display = 'block';
      setTimeout(() => { notification.style.display = 'none'; }, 3000);
    });
    
    socket.on('activate_spalony', function(data) {
        const audio = new Audio('https://www.soundjay.com/buttons/button-4.mp3');
        audio.play();
    });

    function getColorHex(colorName) {
      const colors = {
        'biały': '#ffffff', 'żółty': '#ffff00', 'pomarańczowy': '#ffa500',
        'czerwony': '#ff0000', 'różowy': '#ff69b4', 'fioletowy': '#800080',
        'limonkowy': '#00ff00', 'ciemnozielony': '#006400', 'błękitny': '#00bfff',
        'niebieski': '#0000ff', 'brązowy': '#8b4513', 'szary': '#808080',
        'czarny': '#000000'
      };
      return colors[colorName] || '#333';
    }
  </script>
</body>
</html>
'''


# Endpointy Flask
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        nick = request.form['nick']
        session['nick'] = nick

        # Inicjalizacja danych gracza
        if nick not in player_data:
            player_data[nick] = {
                'knowledge': 0,
                'speed': 0,
                'spalony': False,
                'exchange_used': []
            }

        return redirect(url_for('lobby'))
    return render_template_string(INDEX_HTML)


@app.route('/lobby')
def lobby():
    nick = session.get('nick')
    if not nick or nick not in player_data:
        return redirect('/')
    return render_template_string(LOBBY_HTML, nick=nick, players=players,
                                  player_data=player_data, current_host=current_host)


@app.route('/game')
def game():
    nick = session.get('nick')
    if not nick or nick not in player_data:
        return redirect('/')
    return render_template_string(GAME_HTML, nick=nick, players=players,
                                  player_data=player_data, current_host=current_host)


@app.route('/serwer')
def serwer():
    return render_template_string(SERVER_HTML)


# SocketIO events
@socketio.on('join')
def on_join(nick):
    if nick not in players:
        players.append(nick)
    user_sids[nick] = request.sid
    emit_player_list()

@socketio.on('join_game')
def on_join_game(nick):
    user_sids[nick] = request.sid
    emit_player_list()
    if current_minigame:
        start_minigame()
    # przy dołączeniu od razu podeślij dostępne wymiany
    emit_available_exchanges()

def emit_available_exchanges():
    """
    Przejrzyj EXCHANGES i dla każdego nicka wyślij tylko
    te, które:
     - nie były już użyte
     - gracz ma wystarczająco pkt
     - matchują okno czasowe dla danej wymiany
    """
    for nick, pdata in player_data.items():
        sid = user_sids.get(nick)
        if not sid:
            continue

        avail = []
        for eid, exch in EXCHANGES.items():
            # koszt i powtórki
            if eid in pdata['exchange_used'] or pdata['speed'] < exch['cost']:
                continue

            # 2,4,6: tylko przed wylosowaniem nowej minigry
            if eid in (2,4,6):
                # aktualnie czekamy na hosta, czyli type=='await_host'
                if current_minigame is not None:
                    continue

            # 3 i 5: tylko w rundzie "pytania", w fazie waiting (przed Start)
            if eid in (3,5):
                if current_minigame != 'pytania' or minigame_state.get('phase') != 'waiting':
                    continue
                # 5 tylko dla hosta
                if eid == 5 and nick != current_host:
                    continue

            avail.append({
                'id':          eid,
                'name':        exch['name'],
                'description': exch['description'],
                'cost':        exch['cost']
            })

        socketio.emit('update_exchanges', {'exchanges': avail}, room=sid)


@socketio.on('join_server')
def on_join_server():
    join_room(server_room)
    emit_player_list()


def emit_player_list():
    socketio.emit('player_list', {
        'players': players,
        'player_data': player_data,
        'current_host': current_host
    })
    socketio.emit('update_players', {
        'players': players,
        'player_data': player_data,
        'current_host': current_host
    }, namespace='/')


# Rozpoczynanie gry
@socketio.on('start_game')
def start_game():
    global current_round, current_minigame, current_host
    current_round = 1
    #current_minigame = None
    current_host = None  # Pierwszy gracz jako prowadzący

    # Reset stanu graczy
    for player in players:
        player_data[player]['spalony'] = False

    socketio.emit('game_started')
    time.sleep(1)
    next_host()


def next_host():
    global current_host
    # jeśli mamy backup po natychmiastowym ziemniaku
    if 'backup_host' in minigame_state:
        current_host = minigame_state.pop('backup_host')
        emit_player_list()
        # od razu ruszamy następną grę (await_host)
        socketio.emit('start_minigame',{'type':'await_host'})
        emit_available_exchanges()
        return

    # klasyczna rotacja CCW
    idx = players.index(current_host) if current_host else -1
    next_idx = (idx + 1) % len(players)
    cand = players[next_idx]
    # jeżeli ten kandydat ma flagę skip
    if player_data.get(cand,{}).get('skip_next_host'):
        # skasuj flagę i pobierz kolejnego
        player_data[cand].pop('skip_next_host')
        next_idx = (next_idx + 1) % len(players)
        cand = players[next_idx]
    current_host = cand

    emit_player_list()
    time.sleep(0.5)
    socketio.emit('start_minigame',{'type':'await_host'})


# Logika minigier
@socketio.on('next_minigame')
def on_next_minigame():
    # Losuj minigrę
    time.sleep(0.5)
    minigame_roll = random.randint(1, 6)

    '''if minigame_roll <= 3:
        start_pytania_minigame()
    elif minigame_roll == 4:'''
    start_kolory_minigame()
    '''elif minigame_roll == 5:
        start_timekeeper_minigame()
    else:  # 6'''
    #start_ziemniak_minigame()

def next_minigame():
    # Losuj minigrę
    time.sleep(0.5)
    minigame_roll = random.randint(1, 6)

    emit_player_list()

    if minigame_roll <= 3:
        start_pytania_minigame()
    elif minigame_roll == 4:
        start_kolory_minigame()
    elif minigame_roll == 5:
        start_timekeeper_minigame()
    else:  # 6
        start_ziemniak_minigame()


def start_ziemniak_minigame():
    global current_minigame, minigame_state
    current_minigame = 'goracy_ziemniak'

    random_question = random.choice(questions_ziemniak)
    while random_question in used_questions:
        random_question = random.choice(questions_ziemniak)
    used_questions.append(random_question)

    minigame_state = {
        'question': random_question,
        'start_time': time.time(),
        'explosion_time': random.randint(10, 30),
        'spalony': None
    }

    # Odliczanie 7 sekund
    countdown(7, "Gorący ziemniak", "Przygotuj się do podawania ziemniaka!")


def start_kolory_minigame():
    global current_minigame, minigame_state
    current_minigame = 'kolory'

    # Wybierz 4 losowe kolory
    selected_colors = random.sample(COLORS, 4)
    server_color = random.choice(selected_colors)

    minigame_state = {
        'colors': selected_colors,
        'server_color': server_color,
        'answers': {},
        'start_time': time.time()
    }

    countdown(7, "Kto pierwszy ten lepszy", "Kliknij we właściwy kolor jak najszybciej!")


def start_pytania_minigame():
    global current_minigame, minigame_state
    current_minigame = 'pytania'

    minigame_state = {
        'host': current_host,
        'answers': {},
        'phase': 'waiting',  # waiting -> answering -> selecting
        'timer': None,
        'correct_answer': None,
        'difficulty': None
    }
    socketio.emit('start_minigame', {
        'type': 'pytania',
        'title': 'Pytania z wiedzy',
    })
    emit_available_exchanges()


def start_timekeeper_minigame():
    global current_minigame, minigame_state
    current_minigame = 'timekeeper'

    minigame_state = {
        'target_time': random.uniform(3, 10),  # Czas docelowy (3-10s)
        'start_time': None,
        'results': {},
        'players_answered': set(),
        'timer_start': None
    }

    countdown(7, "Chronometrażysta", "Przygotuj się do liczenia czasu!")


def countdown(seconds, title, message):
    def countdown_task():
        for i in range(seconds, 0, -1):
            socketio.emit('start_minigame', {
                'type': 'countdown',
                'title': title,
                'time': i,
                'message': message
            })
            time.sleep(1)

        # Po odliczeniu rozpocznij właściwą minigrę
        start_minigame()

    socketio.start_background_task(countdown_task)


def start_minigame():
    if current_minigame == 'goracy_ziemniak':
        # Rozpocznij odliczanie wybuchu ziemniaka
        def ziemniak_task():
            start_time = time.time()
            explosion_time = minigame_state['explosion_time']

            # Aktualizuj czas dla serwera
            for i in range(explosion_time, 0, -1):
                socketio.emit('start_minigame', {
                    'type': 'goracy_ziemniak',
                    'title': 'Gorący ziemniak',
                    'time': i,
                    'question': minigame_state['question']
                })
                time.sleep(1)

            # Ziemniak wybuchł! Aktywuj przycisk "Spalony"
            socketio.emit('activate_spalony')
            socketio.emit('notification', {
                'message': 'Ziemniak wybuchł! Kto został spalony?'
            })

        socketio.start_background_task(ziemniak_task)

    elif current_minigame == 'kolory':
        # Rozpocznij pokazywanie koloru na serwerze
        socketio.emit('start_minigame', {
            'type': 'kolory',
            'title': 'Kto pierwszy ten lepszy',
            'colors': minigame_state['colors'],
            'server_color': minigame_state['server_color']
        })

    elif current_minigame == 'timekeeper':
        # Pokazuj minigrę dla graczy
        socketio.emit('start_minigame', {
            'type': 'timekeeper',
            'title': 'Chronometrażysta',
            'target_time': minigame_state['target_time']
        })

        # Rozpocznij pomiar czasu
        minigame_state['timer_start'] = time.time()
        minigame_state['start_time'] = time.time()

        # Uruchom timer 20s na zakończenie minigry
        def timekeeper_timer():
            time.sleep(20)
            if minigame_state['start_time']:  # Jeśli minigra jeszcze trwa
                end_timekeeper_minigame()

        socketio.start_background_task(timekeeper_timer)


# Obsługa odpowiedzi
@socketio.on('spalony')
def on_spalony(nick):
    minigame_state['spalony'] = nick
    player_data[nick]['spalony'] = True

    lost = min(2, player_data[nick]['speed'])
    player_data[nick]['speed'] -= lost

    # Wyślij informację o spalonym graczu
    socketio.emit('minigame_results', {
        'type': 'ziemniak',
        'message': f'{nick} został spalony!',
        'lost_speed': lost
    })

    socketio.emit('notification', {'message': f'{nick} został spalony!'})


@socketio.on('select_color')
def on_select_color(data):
    nick = data['nick']
    color = data['color']

    if nick in minigame_state['answers']:
        return  # Gracz już odpowiedział

    minigame_state['answers'][nick] = {
        'color': color,
        'time': time.time() - minigame_state['start_time']
    }

    # Sprawdź czy wszyscy odpowiedzieli
    if len(minigame_state['answers']) == len(players):
        end_kolory_minigame()


def end_kolory_minigame():
    correct_color = minigame_state['server_color']
    results = []

    # Zbierz poprawne odpowiedzi z czasem
    correct_answers = []
    for nick, answer_data in minigame_state['answers'].items():
        if answer_data['color'] == correct_color:
            correct_answers.append((nick, answer_data['time']))

    # Posortuj poprawnych graczy według czasu odpowiedzi
    correct_answers.sort(key=lambda x: x[1])

    # Przyznaj punkty
    if len(correct_answers) > 0:
        first = correct_answers[0][0]
        player_data[first]['speed'] += 2
        results.append({
            'player': first,
            'points': 2,
            'reason': '1. miejsce'
        })

    if len(correct_answers) > 1:
        second = correct_answers[1][0]
        player_data[second]['speed'] += 1
        results.append({
            'player': second,
            'points': 1,
            'reason': '2. miejsce'
        })

    # Wyślij wyniki
    socketio.emit('minigame_results', {
        'type': 'kolory',
        'results': results
    })
    emit_player_list()


@socketio.on('start_question')
def on_start_question():
    if minigame_state['phase'] != 'waiting': return
    # sprawdź opóźnienie
    delay = minigame_state.get('delay_questions', 0)
    minigame_state['phase'] = 'answering'
    minigame_state['start_time'] = time.time() + delay

    # odsyłamy fazę answering (z timerem 30s + delay na serwerze)
    socketio.emit('minigame_update', {
        'type':'pytania','phase':'answering','options':['A','B','C','D'],'time_left':30+delay
    })
    # rusz timer
    def question_timer():
        total = 30 + delay
        while total>0 and minigame_state['phase']=='answering':
            time.sleep(1)
            total -= 1
            socketio.emit('minigame_update',{
                'type':'pytania','phase':'answering','time_left': total
            }, room=server_room)
        # przejście do host_selecting
        minigame_state['phase'] = 'host_selecting'
        socketio.emit('minigame_update',{
            'type':'pytania','phase':'host_selecting',
            'options':['A','B','C','D'],'difficulties':[1,2,3]
        })
    socketio.start_background_task(question_timer)



@socketio.on('submit_answer')
def on_submit_answer(data):
    player = data['nick']
    answer = data['answer']

    # Zapisz odpowiedź tylko jeśli gracz jest uczestnikiem i trwa faza odpowiedzi
    if (player != minigame_state['host'] and
            minigame_state['phase'] == 'answering' and
            player not in minigame_state['answers']):

        minigame_state['answers'][player] = {
            'answer': answer,
            'time': time.time() - minigame_state['start_time']
        }
        participants = [p for p in players]
        print("odpowiedziało: ", len(minigame_state['answers']))
        # Sprawdź czy wszyscy odpowiedzieli
        if len(minigame_state['answers']) == len(participants) - 1: # bez hosta
            print("teraz host")
            minigame_state['phase'] = 'host_selecting'

            # Przejdź do wyboru odpowiedzi
            socketio.emit('minigame_update', {
                'type': 'pytania',
                'phase': 'host_selecting',
                'options': ['A', 'B', 'C', 'D'],
                'difficulties': [1, 2, 3]
            })


@socketio.on('set_correct_answer')
def on_set_correct_answer(data):
    global minigame_state

    if (minigame_state['phase'] == 'host_selecting' and
            data['nick'] == minigame_state['host']):

        minigame_state['correct_answer'] = data['answer']
        minigame_state['difficulty'] = data['difficulty']

        # Oblicz wyniki
        results = calculate_question_results()

        # Wyślij wyniki
        socketio.emit('minigame_results', {
            'type': 'pytania',
            'results': results
        })

        # Zaktualizuj punkty
        for player, points in results.items():
            player_data[player]['knowledge'] += points['knowledge']
            player_data[player]['speed'] += points['speed']

        emit_player_list()


def calculate_question_results():
    results = {}
    correct_players = []

    # Znajdź poprawnych graczy
    for player, answer_data in minigame_state['answers'].items():
        if answer_data['answer'] == minigame_state['correct_answer']:
            correct_players.append((player, answer_data['time']))

    # Posortuj poprawnych graczy według czasu odpowiedzi
    correct_players.sort(key=lambda x: x[1])

    # Przydziel punkty
    for i, (player, _) in enumerate(correct_players):
        results[player] = {
            'knowledge': minigame_state['difficulty'],
            'speed': 2 if i == 0 else (1 if i == 1 else 0)
        }

    # Dodaj graczy z błędnymi odpowiedziami
    for player in minigame_state['answers']:
        if player not in results:
            results[player] = {'knowledge': 0, 'speed': 0}

    return results


@socketio.on('debugg')
def on_debugg(data):
    print(data['text'])


@socketio.on('stop_timer')
def on_stop_timer(data):
    nick = data['nick']
    end_time = data['time'] / 1000.0  # Konwersja na sekundy

    if nick in minigame_state['players_answered']:
        return

    start_time = minigame_state['start_time']
    player_time = end_time - start_time
    minigame_state['results'][nick] = player_time
    minigame_state['players_answered'].add(nick)

    # Sprawdź czy wszyscy odpowiedzieli
    if len(minigame_state['players_answered']) == len(players):
        end_timekeeper_minigame()


def end_timekeeper_minigame():
    target_time = minigame_state['target_time']
    results = []

    # Oblicz różnice czasu dla każdego gracza
    for nick, player_time in minigame_state['results'].items():
        diff = abs(player_time - target_time)
        results.append({
            'player': nick,
            'time': player_time,
            'diff': diff
        })

    # Posortuj od najmniejszej różnicy
    results.sort(key=lambda x: x['diff'])

    # Przyznaj punkty
    if len(results) > 0:
        results[0]['points'] = 2
        player_data[results[0]['player']]['speed'] += 2

        if len(results) > 1:
            results[1]['points'] = 1
            player_data[results[1]['player']]['speed'] += 1

    # Wyślij wyniki
    socketio.emit('minigame_results', {
        'type': 'timekeeper',
        'results': results
    })
    emit_player_list()

    # Zresetuj stan minigry
    minigame_state['start_time'] = None


def get_sid(nick):
    # Funkcja pomocnicza do znajdowania SID dla nicku
    for sid, data in socketio.server.environ.items():
        #if 'nick' in data and data['nick'] == nick:
            print(sid)
            return sid
    return None


# ========== 1) Rozszerzamy EXCHANGES (jeżeli jeszcze nie ma) ==========
EXCHANGES = {
    1: {'name': 'Losowanie kolorów',      'cost': 1, 'description': 'Zmień kolory u innych graczy'},
    2: {'name': 'Natychmiastowy ziemniak','cost': 2, 'description': 'Przejdź od razu do gry "Gorący ziemniak"'},
    3: {'name': 'Opóźnienie pytań',       'cost': 3, 'description': 'Opóźnij start pytań o 5s'},
    4: {'name': '+1 pkt wiedzy',          'cost': 4, 'description': 'Dodatkowy punkt wiedzy'},
    5: {'name': 'Pomiń prowadzenie',     'cost': 5, 'description': 'Ominięcie tury prowadzącego'},
    6: {'name': '-1 pkt wiedzy innym',    'cost': 6, 'description': 'Odjęcie 1 pkt wiedzy pozostałym'},
}

# ========== 2) Modyfikujemy on_buy_exchange ==========

@socketio.on('buy_exchange')
def on_buy_exchange(data):
    global current_host
    nick       = data['nick']
    exchange_id= data['exchange_id']
    if exchange_id not in EXCHANGES: return
    cost = EXCHANGES[exchange_id]['cost']

    # sprawdź punkty i powtórki
    if player_data[nick]['speed'] < cost:
        return socketio.emit('notification',{'message':'Brak pkt chyżości'})
    if exchange_id in player_data[nick]['exchange_used']:
        return socketio.emit('notification',{'message':'Już użyłeś tej wymiany'})

    # pobieramy koszt
    player_data[nick]['speed'] -= cost
    player_data[nick]['exchange_used'].append(exchange_id)

    # ========== 2: Natychmiastowy ziemniak ==========
    if exchange_id == 2:
        # zachowaj oryginalnego hosta, by po ziemniaku przywrócić
        minigame_state['backup_host'] = current_host
        # od razu uruchom gorący ziemniak
        start_ziemniak_minigame()

    # ========== 3: Opóźnienie pytań o 5s ==========
    elif exchange_id == 3:
        # tylko kiedy już wylosowano "pytania" i przed START
        if current_minigame=='pytania' and minigame_state['phase']=='waiting':
            minigame_state['delay_questions'] = 5
        else:
            return socketio.emit('notification',{'message':'Nie możesz teraz tego kupić'})

    # ========== 4: Dodatkowy 1 pkt wiedzy ==========
    elif exchange_id == 4:
        # przed losowaniem rundy – po prostu dodaj
        player_data[nick]['knowledge'] += 1

    # ========== 5: Ominięcie prowadzenia ==========
    elif exchange_id == 5:
        # tylko w trakcie swojej tury jako host po wylosowaniu pytania
        if nick==current_host and current_minigame=='pytania' and minigame_state['phase']=='waiting':
            player_data[nick]['skip_next_host'] = True
        else:
            return socketio.emit('notification',{'message':'Nie możesz teraz tego kupić'})

    # ========== 6: Odjęcie 1 pkt wiedzy pozostałym ==========
    elif exchange_id == 6:
        # przed losowaniem – zdejmij od innych
        for p in players:
            if p!=nick:
                player_data[p]['knowledge'] = max(0, player_data[p]['knowledge']-1)

    emit_player_list()
    emit_available_exchanges()
    # potwierdź zakup i odśwież stan
    socketio.emit('notification',{'message':f'Wykupiono: {EXCHANGES[exchange_id]["name"]}'})
    emit_player_list()
    socketio.emit('update_exchanges',{'exchanges':[{'id':k,**v} for k,v in EXCHANGES.items()]})



@socketio.on('next_round')
def on_next_round():
    next_host()


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)