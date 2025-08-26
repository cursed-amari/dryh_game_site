(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', () => {
    if (typeof io === 'undefined') {
      console.error('[game] socket.io not found — ensure socket.io script is loaded');
      return;
    }

    const socket = io();

    const playersByName = new Map();

    (function populatePlayers() {
      try {
        const cfg = window.gameConfig || {};
        const players = Array.isArray(cfg.players) ? cfg.players : [];
        for (let i = 0; i < players.length; i++) {
          const p = players[i];
          if (p && p.name) playersByName.set(p.name, p);
        }
      } catch (e) {
        console.error('[game] populatePlayers error', e);
      }
    })();

    // кэш селекторов
    const diceContainer = document.querySelector('.dice-container');
    const playersList = document.querySelector('.players-list');
    const modalOverlay = document.querySelector('.modal-overlay');
    const modalClose = modalOverlay ? modalOverlay.querySelector('.modal-close') : null;
    const rollButton = document.querySelector('.roll-button');

    const hopeInput = document.getElementById('hope-counter');
    const despairInput = document.getElementById('despair-counter');

    // константы
    const MAX_ROLL_HISTORY = 2;
    const diceAngles = {
      1: { x: 0, y: 0 },
      2: { x: 0, y: 180 },
      3: { x: 0, y: -90 },
      4: { x: 0, y: 90 },
      5: { x: -90, y: 0 },
      6: { x: 90, y: 0 }
    };

    const toInt = (v, fallback = 0) => {
      const n = parseInt(v, 10);
      return Number.isFinite(n) ? n : fallback;
    };

    const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

    const updateStat = (stat, value) => {
      socket.emit('update_character', { [stat]: toInt(value) });
    };

    const createDiceElement = (value, color) => {
      const wrapper = document.createElement('div');
      wrapper.classList.add('dice-mechanics');

      const dice = document.createElement('div');
      dice.className = `dice dice-${color}`;

      for (let i = 1; i <= 6; i++) {
        const face = document.createElement('div');
        face.className = 'dice-face';
        face.textContent = i;
        dice.appendChild(face);
      }
      wrapper.appendChild(dice);

      dice.style.transform = 'none';
      requestAnimationFrame(() => {
        void dice.offsetWidth;
        requestAnimationFrame(() => {
          const randX = 360 * (Math.floor(Math.random() * 4) + 2);
          const randY = 360 * (Math.floor(Math.random() * 4) + 2);
          const angles = diceAngles[value] || diceAngles[1];
          dice.style.transform = `rotateX(${randX + angles.x}deg) rotateY(${randY + angles.y}deg)`;
        });
      });

      return wrapper;
    };

    const displayDiceResult = (data) => {
      if (!diceContainer) {
        console.warn('[game] diceContainer not found — cannot display dice');
        return;
      }

      const rollBlock = document.createElement('div');
      rollBlock.classList.add('roll-block');

      const title = document.createElement('h3');
      title.classList.add('roll-block-title');
      title.textContent = `Бросок ${data.player_name || ''}`;
      rollBlock.appendChild(title);

      const appendDice = (arr = [], color) => {
        if (!Array.isArray(arr)) return;
        for (let i = 0; i < arr.length; i++) {
          rollBlock.appendChild(createDiceElement(arr[i], color));
        }
      };

      if (data && data.type === 'yellow') {
        appendDice(data.results, 'yellow');
      } else if (data) {
        appendDice(data.white_results, 'white');
        appendDice(data.red_results, 'red');
        appendDice(data.black_results, 'black');
      }

      diceContainer.prepend(rollBlock);

      while (diceContainer.children.length > MAX_ROLL_HISTORY) {
        diceContainer.removeChild(diceContainer.lastChild);
      }
    };

    const openPlayerModal = (playerName) => {
      if (!modalOverlay) return;
      const player = playersByName.get(playerName);
      if (!player) return;

      modalOverlay.querySelectorAll('[data-stat]').forEach(el => {
        el.textContent = player[el.dataset.stat] || 0;
      });

      modalOverlay.querySelectorAll('[data-field]').forEach(el => {
        el.textContent = player[el.dataset.field] || '';
      });

      modalOverlay.classList.add('active');
    };

    const closePlayerModal = () => {
      if (!modalOverlay) return;
      modalOverlay.classList.remove('active');
    };

    const refreshPlayersList = (players) => {
      if (!playersList) return;
      playersByName.clear();
      playersList.textContent = '';

      if (!Array.isArray(players) || players.length === 0) {
        const li = document.createElement('li');
        li.textContent = 'Нет других игроков';
        playersList.appendChild(li);
        return;
      }

      const frag = document.createDocumentFragment();
      for (let i = 0; i < players.length; i++) {
        const p = players[i];
        playersByName.set(p.name, p);

        const li = document.createElement('li');
        li.className = 'player-item';
        li.textContent = p.name;
        li.dataset.playerName = p.name;
        frag.appendChild(li);
      }
      playersList.appendChild(frag);
    };

    // ------------------- Обработчики -------------------
    if (socket && socket.emit) socket.emit('request_coins');

    const cfg = window.gameConfig || {};
    const isMaster = cfg.master === true || cfg.master === 'true';

    if (isMaster) {
      if (despairInput) {
        despairInput.addEventListener('change', () => {
          const despairValue = toInt(despairInput.value, 0);
          const hopeValue = toInt(hopeInput && hopeInput.value, 0);

          const prevDespair = toInt(despairInput.getAttribute('data-prev'), 0);

          if (despairValue < prevDespair && hopeInput) {
            hopeInput.value = String(hopeValue + 1);
          }

          despairInput.setAttribute('data-prev', String(despairValue));

          socket.emit('update_coins', {
            hope: toInt(hopeInput && hopeInput.value, 0),
            despair: despairValue
          });
        });
      } else {
        console.warn('[game] despairInput not found for master');
      }

      if (hopeInput) {
        hopeInput.addEventListener('change', () => {
          socket.emit('update_coins', {
            hope: toInt(hopeInput.value, 0),
            despair: toInt(despairInput && despairInput.value, 0)
          });
        });
      }
    } else {
      if (hopeInput) hopeInput.readOnly = true;
      if (despairInput) despairInput.readOnly = true;
    }

    if (playersList) {
      playersList.addEventListener('click', e => {
        const li = e.target.closest && e.target.closest('.player-item');
        if (li) openPlayerModal(li.dataset.playerName);
      });
    }

    if (rollButton) {
      rollButton.addEventListener('click', () => {
        if (!socket) return;
        if (isMaster) {
          const yellowIn = document.getElementById('yellow-dice');
          const yellow = yellowIn ? clamp(toInt(yellowIn.value, 3), 1, 15) : 3;
          socket.emit('roll_dice', { yellow });
        } else {
          const red = clamp(toInt(document.getElementById('red-extra') && document.getElementById('red-extra').value, 0), 0, 6);
          const black = clamp(toInt(document.getElementById('black-extra') && document.getElementById('black-extra').value, 0), 0, 1);
          socket.emit('roll_dice', { red_extra: red, black_extra: black });
        }
      });
    }

    document.querySelectorAll('.stat-input').forEach(input => {
      input.addEventListener('change', () => updateStat(input.dataset.stat, input.value));
    });

    socket.on('dice_rolled', displayDiceResult);
    socket.on('update_players', refreshPlayersList);
    socket.on('update_coins', (data) => {
      if (hopeInput) hopeInput.value = toInt(data.hope, 0);
      if (despairInput) despairInput.value = toInt(data.despair, 0);
    });

    if (modalClose) modalClose.addEventListener('click', closePlayerModal);
    if (modalOverlay) modalOverlay.addEventListener('click', e => { if (e.target === modalOverlay) closePlayerModal(); });
    document.addEventListener('keydown', e => { if (e.key === 'Escape') closePlayerModal(); });

    refreshPlayersList(Array.from(playersByName.values()));
  });
})();


