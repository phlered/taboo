const ROUND_DURATION_SECONDS = 120;

const targetWordEl = document.getElementById("targetWord");
const forbiddenListEl = document.getElementById("forbiddenList");
const timerEl = document.getElementById("timer");
const scoreEl = document.getElementById("score");
const statusEl = document.getElementById("status");
const difficultyEl = document.getElementById("difficulty");

const guessedBtn = document.getElementById("guessedBtn");
const skipBtn = document.getElementById("skipBtn");
const startBtn = document.getElementById("startBtn");
const pauseBtn = document.getElementById("pauseBtn");
const resetBtn = document.getElementById("resetBtn");

let cards = [];
let deck = [];
let currentCard = null;
let score = 0;
let timeLeft = ROUND_DURATION_SECONDS;
let timerId = null;
let isRunning = false;

function shuffle(array) {
  const copy = [...array];
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

function formatTime(totalSeconds) {
  const min = Math.floor(totalSeconds / 60).toString().padStart(2, "0");
  const sec = (totalSeconds % 60).toString().padStart(2, "0");
  return `${min}:${sec}`;
}

function updateHud() {
  timerEl.textContent = formatTime(timeLeft);
  scoreEl.textContent = String(score);
}

function setStatus(message) {
  statusEl.textContent = message;
}

function refillDeck() {
  const level = difficultyEl.value;
  const filtered = level === "all" ? cards : cards.filter((c) => c.niveau === level);
  deck = shuffle(filtered);
  return deck.length;
}

function showCard(card) {
  targetWordEl.textContent = card.mot_a_deviner;
  forbiddenListEl.innerHTML = "";
  card.mots_interdits.forEach((word) => {
    const li = document.createElement("li");
    li.textContent = word;
    forbiddenListEl.appendChild(li);
  });
}

function nextCard() {
  if (deck.length === 0) {
    refillDeck();
    if (deck.length === 0) {
      targetWordEl.textContent = "Aucune carte";
      forbiddenListEl.innerHTML = "";
      setStatus("Aucune carte disponible pour ce niveau.");
      guessedBtn.disabled = true;
      skipBtn.disabled = true;
      return;
    }
  }

  currentCard = deck.pop();
  showCard(currentCard);
  updateHud();
}

function lockRoundUI(locked) {
  guessedBtn.disabled = locked;
  skipBtn.disabled = locked;
  startBtn.disabled = !locked;
  pauseBtn.disabled = locked;
  resetBtn.disabled = false;
}

function finishRound() {
  isRunning = false;
  clearInterval(timerId);
  timerId = null;
  lockRoundUI(true);
  setStatus(`Partie terminée. Score final : ${score}.`);
}

function tick() {
  if (!isRunning) {
    return;
  }

  timeLeft -= 1;
  updateHud();

  if (timeLeft <= 0) {
    timeLeft = 0;
    updateHud();
    finishRound();
  }
}

function startRound() {
  if (isRunning) {
    return;
  }

  if (!currentCard) {
    const count = refillDeck();
    if (count === 0) {
      setStatus("Aucune carte chargée.");
      return;
    }
    nextCard();
  }

  isRunning = true;
  lockRoundUI(false);
  setStatus("Partie en cours.");
  timerId = setInterval(tick, 1000);
}

function pauseRound() {
  if (!isRunning) {
    return;
  }
  isRunning = false;
  clearInterval(timerId);
  timerId = null;
  guessedBtn.disabled = true;
  skipBtn.disabled = true;
  pauseBtn.disabled = true;
  startBtn.disabled = false;
  setStatus("Partie en pause.");
}

function resetRound() {
  isRunning = false;
  clearInterval(timerId);
  timerId = null;

  score = 0;
  timeLeft = ROUND_DURATION_SECONDS;
  currentCard = null;

  targetWordEl.textContent = "Appuie sur Démarrer";
  forbiddenListEl.innerHTML = "";

  lockRoundUI(true);
  setStatus("Partie réinitialisée.");
  updateHud();
}

guessedBtn.addEventListener("click", () => {
  if (!isRunning) {
    return;
  }
  score += 1;
  nextCard();
});

skipBtn.addEventListener("click", () => {
  if (!isRunning) {
    return;
  }
  nextCard();
});

startBtn.addEventListener("click", startRound);
pauseBtn.addEventListener("click", pauseRound);
resetBtn.addEventListener("click", resetRound);

difficultyEl.addEventListener("change", () => {
  if (isRunning) {
    pauseRound();
  }
  currentCard = null;
  deck = [];
  targetWordEl.textContent = "Appuie sur Démarrer";
  forbiddenListEl.innerHTML = "";
  setStatus("Niveau changé. Lance une nouvelle partie.");
});

async function bootstrap() {
  try {
    const response = await fetch("cards.json", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    cards = await response.json();
    setStatus(`${cards.length} cartes chargées.`);
    updateHud();
  } catch (error) {
    setStatus(`Erreur de chargement des cartes : ${error.message}`);
    targetWordEl.textContent = "Erreur";
  }
}

lockRoundUI(true);
updateHud();
bootstrap();
