const generateBtn = document.getElementById("generateBtn");
const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");

const prevBtn = document.getElementById("prevBtn");
const nextBtn = document.getElementById("nextBtn");
const playCurrentBtn = document.getElementById("playCurrentBtn");

const moodInput = document.getElementById("mood");
const artistsInput = document.getElementById("artists");
const genresInput = document.getElementById("genres");
const amountInput = document.getElementById("amount");

const statusBox = document.getElementById("status");
const tracksList = document.getElementById("tracksList");
const youtubeFrame = document.getElementById("youtubeFrame");

const nowTitle = document.getElementById("nowTitle");
const nowReason = document.getElementById("nowReason");
const playlistName = document.getElementById("playlistName");
const playlistDescription = document.getElementById("playlistDescription");
const equalizer = document.getElementById("equalizer");

let tracks = [];
let currentIndex = 0;
let autoMode = false;

function setStatus(text, type = "") {
  statusBox.textContent = text;
  statusBox.className = "status " + type;
}

function encodeQuery(query) {
  return encodeURIComponent(query);
}

function youtubeEmbedFromQuery(query, autoplay = true) {
  const q = encodeQuery(query);

  return `https://www.youtube.com/embed?listType=search&list=${q}&autoplay=${autoplay ? "1" : "0"}&controls=1&rel=0`;
}

function youtubeSearchUrl(query) {
  return `https://www.youtube.com/results?search_query=${encodeQuery(query)}`;
}

function renderTracks() {
  tracksList.innerHTML = "";

  if (!tracks.length) {
    tracksList.innerHTML = `<div class="empty">Ainda não existem músicas recomendadas.</div>`;
    return;
  }

  tracks.forEach((track, index) => {
    const item = document.createElement("div");
    item.className = "track";
    if (index === currentIndex) item.classList.add("active");

    item.innerHTML = `
      <div class="track-number">${index + 1}</div>

      <div class="track-info">
        <h3>${escapeHtml(track.artist)} - ${escapeHtml(track.title)}</h3>
        <p>${escapeHtml(track.reason || "Combina com o teu gosto musical.")}</p>
        <span>${escapeHtml(track.vibe || "boa vibe")}</span>
      </div>

      <div class="track-actions">
        <button class="play-one">Play</button>
        <a href="${youtubeSearchUrl(track.youtube_query)}" target="_blank">YouTube</a>
      </div>
    `;

    item.querySelector(".play-one").addEventListener("click", () => {
      playTrack(index, false);
    });

    tracksList.appendChild(item);
  });
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function playTrack(index, continuePlaylist = true) {
  if (!tracks.length) return;

  if (index < 0) index = tracks.length - 1;
  if (index >= tracks.length) index = 0;

  currentIndex = index;
  autoMode = continuePlaylist;

  const track = tracks[currentIndex];

  nowTitle.textContent = `${track.artist} - ${track.title}`;
  nowReason.textContent = track.reason || "A tocar recomendação do ChatGPT.";

  youtubeFrame.src = youtubeEmbedFromQuery(track.youtube_query, true);

  equalizer.classList.add("playing");

  renderTracks();

  setStatus(
    autoMode
      ? `A tocar playlist seguida: ${track.artist} - ${track.title}`
      : `A tocar música escolhida: ${track.artist} - ${track.title}`,
    "ok"
  );
}

function nextTrack() {
  if (!tracks.length) return;
  playTrack(currentIndex + 1, autoMode);
}

function prevTrack() {
  if (!tracks.length) return;
  playTrack(currentIndex - 1, autoMode);
}

function stopPlayer() {
  youtubeFrame.src = "";
  autoMode = false;
  equalizer.classList.remove("playing");
  setStatus("Player parado.", "");
}

async function generateRecommendations(autoStart = true) {
  setStatus("A pedir recomendações ao ChatGPT...", "loading");
  generateBtn.disabled = true;

  try {
    const payload = {
      mood: moodInput.value,
      artists: artistsInput.value,
      genres: genresInput.value,
      amount: amountInput.value
    };

    const res = await fetch("/api/recommendations", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    const data = await res.json();

    if (!data.ok) {
      throw new Error(data.error || "Erro ao gerar recomendações.");
    }

    tracks = data.tracks || [];
    currentIndex = 0;

    playlistName.textContent = data.playlist_name || "Playlist Super Deus";
    playlistDescription.textContent = data.description || "Músicas recomendadas pelo ChatGPT.";

    renderTracks();

    if (!tracks.length) {
      setStatus("O ChatGPT não devolveu músicas. Tenta novamente.", "error");
      return;
    }

    setStatus(`Playlist criada com ${tracks.length} músicas.`, "ok");

    if (autoStart) {
      playTrack(0, true);
    }

  } catch (err) {
    console.error(err);
    setStatus("Erro: " + err.message, "error");
  } finally {
    generateBtn.disabled = false;
  }
}

generateBtn.addEventListener("click", () => {
  generateRecommendations(true);
});

startBtn.addEventListener("click", () => {
  if (!tracks.length) {
    generateRecommendations(true);
    return;
  }

  playTrack(currentIndex, true);
});

stopBtn.addEventListener("click", stopPlayer);

nextBtn.addEventListener("click", () => {
  autoMode = true;
  nextTrack();
});

prevBtn.addEventListener("click", () => {
  autoMode = true;
  prevTrack();
});

playCurrentBtn.addEventListener("click", () => {
  if (!tracks.length) {
    generateRecommendations(true);
    return;
  }

  playTrack(currentIndex, true);
});

/*
  Nota:
  Alguns browsers bloqueiam autoplay com som.
  Por isso a aplicação tenta começar automaticamente,
  mas se o browser bloquear, carrega em "Tocar seguidas".
*/
window.addEventListener("load", () => {
  renderTracks();

  setTimeout(() => {
    generateRecommendations(true);
  }, 500);
});