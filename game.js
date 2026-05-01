const ROUND_DURATION_SECONDS = 120;

const targetWordEl = document.getElementById("targetWord");
const targetLabelEl = document.getElementById("targetLabel");
const forbiddenLabelEl = document.getElementById("forbiddenLabel");
const idleHintEl = document.getElementById("idleHint");
const forbiddenListEl = document.getElementById("forbiddenList");
const timerEl = document.getElementById("timer");
const scoreEl = document.getElementById("score");
const difficultyEl = document.getElementById("difficulty");

const guessedBtn = document.getElementById("guessedBtn");
const skipBtn = document.getElementById("skipBtn");
const startResetBtn = document.getElementById("startResetBtn");

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

function lockRoundUI(locked) {
  guessedBtn.disabled = locked;
  skipBtn.disabled = locked;
  if (locked) {
    startResetBtn.textContent = "Démarrer";
    startResetBtn.dataset.mode = "start";
    startResetBtn.classList.remove("btn-reset");
    startResetBtn.classList.add("btn-start");
  } else {
    startResetBtn.textContent = "Reset";
    startResetBtn.dataset.mode = "reset";
    startResetBtn.classList.remove("btn-start");
    startResetBtn.classList.add("btn-reset");
  }
}

function refillDeck() {
  const level = difficultyEl.value;
  const filtered = level === "all" ? cards : cards.filter((c) => c.niveau === level);
  deck = shuffle(filtered);
  return deck.length;
}

function showIdleState(message = "Appuie sur Démarrer") {
  targetWordEl.textContent = message;
  targetLabelEl.hidden = true;
  forbiddenLabelEl.hidden = true;
  forbiddenListEl.hidden = true;
  forbiddenListEl.innerHTML = "";
  idleHintEl.hidden = false;
}

function showCard(card) {
  targetLabelEl.hidden = false;
  forbiddenLabelEl.hidden = false;
  forbiddenListEl.hidden = false;
  idleHintEl.hidden = true;
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
      showIdleState("Aucune carte");
      guessedBtn.disabled = true;
      skipBtn.disabled = true;
      return;
    }
  }
  currentCard = deck.pop();
  showCard(currentCard);
  updateHud();
}

// ── Feux d'artifice ──────────────────────────────────────────────────────────

function launchFireworks(finalScore) {
  const overlay = document.getElementById("fireworksOverlay");
  const canvas = document.getElementById("fireworksCanvas");
  const scoreDisplay = document.getElementById("fireworksScore");

  scoreDisplay.textContent = `${finalScore} point${finalScore !== 1 ? "s" : ""}`;
  overlay.hidden = false;
  overlay.classList.remove("fireworks-fade-out");

  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
  const ctx = canvas.getContext("2d");

  const COLORS = ["#eb5e28", "#f3a712", "#2f9e44", "#4dabf7", "#f06595", "#ffffff", "#c77dff"];
  const particles = [];

  function createBurst(x, y) {
    const count = 70;
    for (let i = 0; i < count; i++) {
      const angle = (Math.PI * 2 * i) / count + (Math.random() - 0.5) * 0.3;
      const speed = 2 + Math.random() * 6;
      particles.push({
        x,
        y,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        alpha: 1,
        color: COLORS[Math.floor(Math.random() * COLORS.length)],
        radius: 3 + Math.random() * 3,
      });
    }
  }

  let burstCount = 0;
  const burstInterval = setInterval(() => {
    createBurst(
      60 + Math.random() * (canvas.width - 120),
      40 + Math.random() * (canvas.height * 0.65),
    );
    burstCount++;
    if (burstCount >= 10) clearInterval(burstInterval);
  }, 380);

  let animating = true;

  function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (let i = particles.length - 1; i >= 0; i--) {
      const p = particles[i];
      p.x += p.vx;
      p.y += p.vy;
      p.vy += 0.12;
      p.vx *= 0.98;
      p.alpha -= 0.013;
      if (p.alpha <= 0) {
        particles.splice(i, 1);
        continue;
      }
      ctx.save();
      ctx.globalAlpha = p.alpha;
      ctx.fillStyle = p.color;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    }
    if (animating) requestAnimationFrame(animate);
  }

  animate();

  setTimeout(() => {
    animating = false;
    clearInterval(burstInterval);
    overlay.classList.add("fireworks-fade-out");
    setTimeout(() => {
      overlay.hidden = true;
      // Remise à zéro de l'état et de l'affichage après la fermeture de l'overlay
      score = 0;
      timeLeft = ROUND_DURATION_SECONDS;
      currentCard = null;
      deck = [];
      showIdleState("Appuie sur Démarrer");
      updateHud();
    }, 800);
  }, 4500);
}

// ── Contrôle de partie ───────────────────────────────────────────────────────

function finishRound() {
  isRunning = false;
  clearInterval(timerId);
  timerId = null;
  const finalScore = score;
  lockRoundUI(true);
  launchFireworks(finalScore);
}

function tick() {
  if (!isRunning) return;
  timeLeft -= 1;
  updateHud();
  if (timeLeft <= 0) {
    timeLeft = 0;
    updateHud();
    finishRound();
  }
}

function startRound() {
  if (isRunning) return;

  if (!currentCard) {
    const count = refillDeck();
    if (count === 0) return;
    nextCard();
  }

  isRunning = true;
  lockRoundUI(false);
  timerId = setInterval(tick, 1000);
}

function resetRound() {
  isRunning = false;
  clearInterval(timerId);
  timerId = null;

  score = 0;
  timeLeft = ROUND_DURATION_SECONDS;
  currentCard = null;

  showIdleState("Appuie sur Démarrer");

  lockRoundUI(true);
  updateHud();
}

// ── Événements ───────────────────────────────────────────────────────────────

guessedBtn.addEventListener("click", () => {
  if (!isRunning) return;
  score += 1;
  nextCard();
});

skipBtn.addEventListener("click", () => {
  if (!isRunning) return;
  nextCard();
});

startResetBtn.addEventListener("click", () => {
  if (startResetBtn.dataset.mode === "reset") {
    resetRound();
  } else {
    startRound();
  }
});

difficultyEl.addEventListener("change", () => {
  if (isRunning) {
    resetRound();
  }
  currentCard = null;
  deck = [];
  showIdleState("Appuie sur Démarrer");
});

// ── Chargement des cartes ────────────────────────────────────────────────────

async function bootstrap() {
  try {
    const response = await fetch("cards.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    cards = await response.json();
    updateHud();
  } catch (error) {
    showIdleState("Erreur de chargement");
  }
}

lockRoundUI(true);
updateHud();
showIdleState("Appuie sur Démarrer");
bootstrap();
