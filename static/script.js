const moodInput = document.getElementById("mood");
const artistsInput = document.getElementById("artists");
const genresInput = document.getElementById("genres");
const amountInput = document.getElementById("amount");

const generateBtn = document.getElementById("generateBtn");
const playAllBtn = document.getElementById("playAllBtn");
const stopBtn = document.getElementById("stopBtn");
const prevBtn = document.getElementById("prevBtn");
const nextBtn = document.getElementById("nextBtn");
const playCurrentBtn = document.getElementById("playCurrentBtn");
const autoNextCheck = document.getElementById("autoNext");

const statusBox = document.getElementById("status");
const youtubeFrame = document.getElementById("youtubeFrame");
const tracksList = document.getElementById("tracksList");

const nowTitle = document.getElementById("nowTitle");
const nowReason = document.getElementById("nowReason");
const nowVibe = document.getElementById("nowVibe");
const playlistName = document.getElementById("playlistName");
const playlistDescription = document.getElementById("playlistDescription");
const equalizer = document.getElementById("equalizer");

let tracks = [];
let currentIndex = 0;
let isPlaying = false;
let playlistMode = true;
let autoTimer = null;

function setStatus(text, type = "") {
  statusBox.textContent = text;
  statusBox.className = "status " + type;
}

function escapeHtml(text) {
  return String(text || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function encodeQuery(query) {
  return encodeURIComponent(query || "");
}

function youtubeSearchUrl(query) {
  return `https://www.youtube.com/results?search_query=${encodeQuery(query)}`;
}

function youtubeEmbedFromQuery(query, autoplay = true) {
  const q = encodeQuery(query);
  return `https://www.youtube.com/embed?listType=search&list=${q}&autoplay=${autoplay ? "1" : "0"}&controls=1&rel=0`;
}

function clearAutoTimer() {
  if (autoTimer) {
    clearTimeout(autoTimer);
    autoTimer = null;
  }
}

function startAutoTimer(track) {
  clearAutoTimer();

  if (!autoNextCheck.checked) return;
  if (!playlistMode) return;
  if (!track) return;

  const seconds = Number(track.estimated_seconds || 240);
  const safeSeconds = Math.max(120, Math.min(seconds, 480));

  autoTimer = setTimeout(() => {
    nextTrack(true);
  }, safeSeconds * 1000);
}

function renderTracks() {
  tracksList.innerHTML = "";

  if (!tracks.length) {
    tracksList.innerHTML = `<div class="empty">Ainda não existem músicas recomendadas.</div>`;
    return;
  }

  tracks.forEach((track, index) => {
    const item = document.createElement("div");
    item.className = "track-card";

    if (index === currentIndex) {
      item.classList.add("active");
    }

    item.innerHTML = `
      <div class="track-number">${String(index + 1).padStart(2, "0")}</div>

      <div class="track-main">
        <h3>${escapeHtml(track.artist)} - ${escapeHtml(track.title)}</h3>
        <p>${escapeHtml(track.reason)}</p>

        <div class="track-meta">
          <span>${escapeHtml(track.vibe || "boa vibe")}</span>
          <span>${Math.round((track.estimated_seconds || 240) / 60)} min aprox.</span>
        </div>
      </div>

      <div class="track-actions">
        <button class="play-one">Play</button>
        <a href="${youtubeSearchUrl(track.youtube_query)}" target="_blank">Abrir</a>
      </div>
    `;

    item.querySelector(".play-one").addEventListener("click", () => {
      playTrack(index, false);
    });

    tracksList.appendChild(item);
  });
}

function playTrack(index, continuePlaylist = true) {
  if (!tracks.length) {
    setStatus("Ainda não há músicas. Gera uma playlist primeiro.", "error");
    return;
  }

  if (index < 0) index = tracks.length - 1;
  if (index >= tracks.length) index = 0;

  currentIndex = index;
  playlistMode = continuePlaylist;
  isPlaying = true;

  const track = tracks[currentIndex];

  nowTitle.textContent = `${track.artist} - ${track.title}`;
  nowReason.textContent = track.reason || "Recomendação criada pelo ChatGPT.";
  nowVibe.textContent = track.vibe || "boa vibe";

  youtubeFrame.src = youtubeEmbedFromQuery(track.youtube_query, true);

  equalizer.classList.add("playing");

  renderTracks();

  setStatus(
    continuePlaylist
      ? `A tocar playlist seguida: ${track.artist} - ${track.title}`
      : `A tocar música escolhida: ${track.artist} - ${track.title}`,
    "ok"
  );

  startAutoTimer(track);
}

function nextTrack(forcePlaylist = false) {
  if (!tracks.length) return;

  if (forcePlaylist) {
    playlistMode = true;
  }

  playTrack(currentIndex + 1, playlistMode);
}

function prevTrack() {
  if (!tracks.length) return;
  playTrack(currentIndex - 1, playlistMode);
}

function stopPlayer() {
  clearAutoTimer();

  youtubeFrame.src = "";
  isPlaying = false;
  playlistMode = false;

  equalizer.classList.remove("playing");

  setStatus("Player parado.", "");
}

async function generateRecommendations(autoStart = true) {
  clearAutoTimer();

  generateBtn.disabled = true;
  playAllBtn.disabled = true;

  setStatus("A pedir recomendações ao ChatGPT...", "loading");

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

    tracks = Array.isArray(data.tracks) ? data.tracks : [];
    currentIndex = 0;
    playlistMode = true;

    playlistName.textContent = data.playlist_name || "Playlist Super Deus";
    playlistDescription.textContent = data.description || "Músicas recomendadas pelo ChatGPT.";

    renderTracks();

    if (!tracks.length) {
      setStatus("O ChatGPT não devolveu músicas. Tenta gerar novamente.", "error");
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
    playAllBtn.disabled = false;
  }
}

generateBtn.addEventListener("click", () => {
  generateRecommendations(true);
});

playAllBtn.addEventListener("click", () => {
  if (!tracks.length) {
    generateRecommendations(true);
    return;
  }

  playTrack(currentIndex, true);
});

stopBtn.addEventListener("click", () => {
  stopPlayer();
});

nextBtn.addEventListener("click", () => {
  nextTrack(true);
});

prevBtn.addEventListener("click", () => {
  prevTrack();
});

playCurrentBtn.addEventListener("click", () => {
  if (!tracks.length) {
    generateRecommendations(true);
    return;
  }

  playTrack(currentIndex, true);
});

autoNextCheck.addEventListener("change", () => {
  clearAutoTimer();

  if (autoNextCheck.checked && isPlaying && tracks[currentIndex]) {
    startAutoTimer(tracks[currentIndex]);
    setStatus("Avanço automático ativado.", "ok");
  } else {
    setStatus("Avanço automático desativado.", "");
  }
});

window.addEventListener("load", () => {
  renderTracks();

  setTimeout(() => {
    generateRecommendations(true);
  }, 700);
});