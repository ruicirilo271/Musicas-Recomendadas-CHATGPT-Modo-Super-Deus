const moodInput = document.getElementById("mood");
const genresInput = document.getElementById("genres");
const amountInput = document.getElementById("amount");

const loadLikesBtn = document.getElementById("loadLikesBtn");
const generateBtn = document.getElementById("generateBtn");
const playAllBtn = document.getElementById("playAllBtn");
const stopBtn = document.getElementById("stopBtn");
const prevBtn = document.getElementById("prevBtn");
const nextBtn = document.getElementById("nextBtn");
const playCurrentBtn = document.getElementById("playCurrentBtn");
const useEstimatedDuration = document.getElementById("useEstimatedDuration");

const statusBox = document.getElementById("status");
const likesStatus = document.getElementById("likesStatus");
const tracksList = document.getElementById("tracksList");
const likedVideosList = document.getElementById("likedVideosList");

const nowTitle = document.getElementById("nowTitle");
const nowReason = document.getElementById("nowReason");
const nowVibe = document.getElementById("nowVibe");
const playlistName = document.getElementById("playlistName");
const playlistDescription = document.getElementById("playlistDescription");
const tasteSummary = document.getElementById("tasteSummary");
const equalizer = document.getElementById("equalizer");

const coverImg = document.getElementById("coverImg");
const discFallback = document.getElementById("discFallback");
const openYoutube = document.getElementById("openYoutube");

let likedVideos = [];
let tracks = [];
let currentIndex = 0;
let isPlaying = false;
let playlistMode = true;
let autoTimer = null;

let ytPlayer = null;
let ytReady = false;
let pendingVideoId = null;

function onYouTubeIframeAPIReady() {
  ytPlayer = new YT.Player("youtubePlayer", {
    width: "100%",
    height: "100%",
    videoId: "",
    playerVars: {
      autoplay: 0,
      controls: 1,
      rel: 0,
      playsinline: 1
    },
    events: {
      onReady: () => {
        ytReady = true;

        if (pendingVideoId) {
          loadVideoInPlayer(pendingVideoId);
          pendingVideoId = null;
        }
      },
      onStateChange: onPlayerStateChange
    }
  });
}

function onPlayerStateChange(event) {
  if (event.data === YT.PlayerState.ENDED) {
    clearAutoTimer();

    if (playlistMode && tracks.length) {
      setStatus("Música terminou. A avançar para a próxima...", "ok");

      setTimeout(() => {
        nextTrack(true);
      }, 700);
    }
  }

  if (event.data === YT.PlayerState.PLAYING) {
    equalizer.classList.add("playing");
    isPlaying = true;
  }

  if (event.data === YT.PlayerState.PAUSED) {
    equalizer.classList.remove("playing");
  }
}

function loadVideoInPlayer(videoId) {
  if (!ytReady || !ytPlayer) {
    pendingVideoId = videoId;
    return;
  }

  ytPlayer.loadVideoById(videoId);
}

function setStatus(text, type = "") {
  statusBox.textContent = text;
  statusBox.className = "status " + type;
}

function setLikesStatus(text, type = "") {
  likesStatus.textContent = text;
  likesStatus.className = "mini-status " + type;
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

async function getYouTubeVideo(query) {
  const res = await fetch("/api/youtube/search", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ query })
  });

  const data = await res.json();

  if (!data.ok) {
    throw new Error(data.error || "Não foi possível encontrar vídeo no YouTube.");
  }

  return data;
}

function clearAutoTimer() {
  if (autoTimer) {
    clearTimeout(autoTimer);
    autoTimer = null;
  }
}

function startEstimatedTimer(track) {
  clearAutoTimer();

  if (!useEstimatedDuration.checked) return;
  if (!playlistMode) return;
  if (!track) return;

  const seconds = Number(track.estimated_seconds || 240);
  const safeSeconds = Math.max(120, Math.min(seconds, 480));

  autoTimer = setTimeout(() => {
    nextTrack(true);
  }, safeSeconds * 1000);
}

function setCover(src) {
  if (src) {
    coverImg.src = src;
    coverImg.style.display = "block";
    discFallback.style.display = "none";
  } else {
    coverImg.src = "";
    coverImg.style.display = "none";
    discFallback.style.display = "flex";
  }
}

function renderLikedVideos() {
  likedVideosList.innerHTML = "";

  if (!likedVideos.length) {
    likedVideosList.innerHTML = `<div class="empty">Ainda não carregaste os vídeos gostados.</div>`;
    return;
  }

  likedVideos.slice(0, 12).forEach((video) => {
    const item = document.createElement("div");
    item.className = "liked-card";

    item.innerHTML = `
      <img src="${escapeHtml(video.thumbnail || "")}" alt="">
      <div>
        <h4>${escapeHtml(video.title)}</h4>
        <p>${escapeHtml(video.channelTitle)}</p>
      </div>
      <a href="${escapeHtml(video.watchUrl)}" target="_blank">Abrir</a>
    `;

    likedVideosList.appendChild(item);
  });
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

    const videoBadge = track.videoId
      ? `<span>vídeo encontrado</span>`
      : `<span>ainda sem vídeo</span>`;

    item.innerHTML = `
      <div class="track-number">${String(index + 1).padStart(2, "0")}</div>

      <div class="track-main">
        <h3>${escapeHtml(track.artist)} - ${escapeHtml(track.title)}</h3>
        <p>${escapeHtml(track.reason)}</p>

        <div class="track-meta">
          <span>${escapeHtml(track.vibe || "boa vibe")}</span>
          <span>${Math.round((track.estimated_seconds || 240) / 60)} min aprox.</span>
          ${videoBadge}
        </div>
      </div>

      <div class="track-actions">
        <button class="play-one">Play</button>
        <a href="${youtubeSearchUrl(track.youtube_query)}" target="_blank">Pesquisar</a>
      </div>
    `;

    item.querySelector(".play-one").addEventListener("click", () => {
      playTrack(index, false);
    });

    tracksList.appendChild(item);
  });
}

async function loadLikedVideos() {
  setLikesStatus("A carregar vídeos que deste like no YouTube...", "loading");

  try {
    const res = await fetch("/api/youtube/liked?max=50");
    const data = await res.json();

    if (!data.ok) {
      if (data.login_required) {
        setLikesStatus("Tens de entrar com o YouTube primeiro.", "error");
        return;
      }

      throw new Error(data.error || "Erro ao carregar likes.");
    }

    likedVideos = data.videos || [];

    renderLikedVideos();

    setLikesStatus(`Carreguei ${likedVideos.length} vídeos gostados do YouTube.`, "ok");

  } catch (err) {
    console.error(err);
    setLikesStatus("Erro: " + err.message, "error");
  }
}

async function generateRecommendations(autoStart = true) {
  clearAutoTimer();

  generateBtn.disabled = true;
  playAllBtn.disabled = true;

  setStatus("A pedir recomendações ao ChatGPT com base nos teus likes...", "loading");

  try {
    if (!likedVideos.length) {
      await loadLikedVideos();
    }

    const payload = {
      mood: moodInput.value,
      genres: genresInput.value,
      amount: amountInput.value,
      liked_videos: likedVideos
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
    playlistDescription.textContent = data.description || "Músicas recomendadas pelo ChatGPT com base nos teus likes.";
    tasteSummary.textContent = data.taste_summary || "";

    renderTracks();

    if (!tracks.length) {
      setStatus("O ChatGPT não devolveu músicas. Tenta novamente.", "error");
      return;
    }

    setStatus(`Playlist criada com ${tracks.length} músicas baseadas nos teus likes.`, "ok");

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

async function playTrack(index, continuePlaylist = true) {
  if (!tracks.length) {
    setStatus("Ainda não há músicas. Gera uma playlist primeiro.", "error");
    return;
  }

  if (index < 0) index = tracks.length - 1;
  if (index >= tracks.length) index = 0;

  clearAutoTimer();

  currentIndex = index;
  playlistMode = continuePlaylist;
  isPlaying = true;

  const track = tracks[currentIndex];

  nowTitle.textContent = `${track.artist} - ${track.title}`;
  nowReason.textContent = track.reason || "Recomendação criada pelo ChatGPT.";
  nowVibe.textContent = track.vibe || "boa vibe";

  equalizer.classList.add("playing");
  renderTracks();

  setStatus(`A procurar vídeo no YouTube: ${track.artist} - ${track.title}`, "loading");

  try {
    let yt = null;

    if (track.videoId) {
      yt = {
        videoId: track.videoId,
        title: track.youtubeTitle || "",
        channelTitle: track.channelTitle || "",
        thumbnail: track.thumbnail || "",
        watchUrl: track.watchUrl || `https://www.youtube.com/watch?v=${track.videoId}`
      };
    } else {
      yt = await getYouTubeVideo(track.youtube_query);

      track.videoId = yt.videoId;
      track.youtubeTitle = yt.title;
      track.channelTitle = yt.channelTitle;
      track.thumbnail = yt.thumbnail;
      track.watchUrl = yt.watchUrl;
    }

    loadVideoInPlayer(yt.videoId);
    setCover(yt.thumbnail);

    if (yt.watchUrl) {
      openYoutube.href = yt.watchUrl;
      openYoutube.style.display = "inline-flex";
    } else {
      openYoutube.style.display = "none";
    }

    setStatus(
      continuePlaylist
        ? `A tocar playlist seguida: ${track.artist} - ${track.title}`
        : `A tocar música escolhida: ${track.artist} - ${track.title}`,
      "ok"
    );

    renderTracks();

    if (useEstimatedDuration.checked) {
      startEstimatedTimer(track);
    }

  } catch (err) {
    console.error(err);
    setStatus("Erro YouTube: " + err.message, "error");

    if (continuePlaylist) {
      setTimeout(() => {
        nextTrack(true);
      }, 2200);
    }
  }
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

  if (ytPlayer && ytReady) {
    ytPlayer.stopVideo();
  }

  isPlaying = false;
  playlistMode = false;

  equalizer.classList.remove("playing");

  setStatus("Player parado.", "");
}

loadLikesBtn.addEventListener("click", () => {
  loadLikedVideos();
});

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

useEstimatedDuration.addEventListener("change", () => {
  clearAutoTimer();

  if (useEstimatedDuration.checked && isPlaying && tracks[currentIndex]) {
    startEstimatedTimer(tracks[currentIndex]);
    setStatus("Modo duração estimada ativado.", "ok");
  } else {
    setStatus("Modo fim real do vídeo ativado. A música vai até ao fim e depois avança.", "ok");
  }
});

window.addEventListener("load", () => {
  renderTracks();
  renderLikedVideos();
  setCover("");
  openYoutube.style.display = "none";

  setStatus("Entra com o YouTube e carrega os teus likes para gerar recomendações.", "");
});