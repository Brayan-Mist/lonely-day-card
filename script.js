const body = document.body;
const postcard = document.querySelector(".postcard");
const rain = document.querySelector(".rain");
const song = document.querySelector("#song");
const playButton = document.querySelector(".play-once");
const playIcon = playButton.querySelector("path");
const songLine = document.querySelector("[data-song-line]");
const songProgress = document.querySelector("[data-song-progress]");
const songCurrent = document.querySelector("[data-song-current]");
const songDuration = document.querySelector("[data-song-duration]");
const relationshipStart = new Date("2026-06-17T22:53:58+03:00");
const songTitle = "Spat";
const lrcPath = "assets/spat.lrc";
let activeSongMomentIndex = -1;
let songLineTransitionTimer;
let playbackErrorTimer;
let isUsingTimedLyrics = false;
let lyricsReady = false;

let songMoments = [];

const setPlaybackState = (isPlaying) => {
  postcard.classList.toggle("is-playing", isPlaying);
  playButton.setAttribute("aria-label", `${isPlaying ? "Pause" : "Play"} ${songTitle}`);
  playButton.setAttribute("aria-pressed", String(isPlaying));
  playIcon.setAttribute("d", isPlaying ? "M7 5h4v14H7zM13 5h4v14h-4z" : "M8 5v14l11-7Z");
};

const pad = (value) => String(value).padStart(2, "0");

const formatSongTime = (seconds) => {
  if (!Number.isFinite(seconds) || seconds < 0) {
    return "0:00";
  }

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.floor(seconds % 60);
  return `${minutes}:${pad(remainingSeconds)}`;
};

const parseLrcTime = (minutes, seconds) => Number(minutes) * 60 + Number(seconds);

const parseLrc = (lrcText) => {
  const moments = [];
  const timeTagPattern = /\[(\d{1,2}):(\d{2}(?:\.\d{1,3})?)\]/g;

  for (const rawLine of lrcText.split(/\r?\n/)) {
    const timeTags = [...rawLine.matchAll(timeTagPattern)];
    if (!timeTags.length) {
      continue;
    }

    const text = rawLine.replace(timeTagPattern, "").trim();
    if (!text) {
      continue;
    }

    for (const tag of timeTags) {
      moments.push({
        time: parseLrcTime(tag[1], tag[2]),
        text,
      });
    }
  }

  return moments.sort((left, right) => left.time - right.time);
};

const useFallbackLyrics = () => {
  songMoments = [];
  isUsingTimedLyrics = false;
  lyricsReady = true;
  clearSongLine();
};

const loadLrc = () => {
  const request = new XMLHttpRequest();

  request.open("GET", `${lrcPath}?v=${Date.now()}`, true);
  request.overrideMimeType("text/plain; charset=utf-8");

  request.onload = () => {
    if (request.status < 200 || request.status >= 300) {
      useFallbackLyrics();
      return;
    }

    const loadedMoments = parseLrc(request.responseText);
    if (!loadedMoments.length) {
      useFallbackLyrics();
      return;
    }

    songMoments = loadedMoments;
    isUsingTimedLyrics = true;
    lyricsReady = true;
    clearSongLine();
    updateSongMoment();
  };

  request.onerror = useFallbackLyrics;
  request.send();
};

const clearSongLine = () => {
  activeSongMomentIndex = -1;
  clearTimeout(songLineTransitionTimer);
  songLine.classList.remove("is-changing");
  songLine.textContent = "";
};

const showSongLine = (index, instant = false) => {
  if (index === activeSongMomentIndex || !songMoments[index]) {
    return;
  }

  activeSongMomentIndex = index;
  clearTimeout(songLineTransitionTimer);

  if (instant) {
    songLine.textContent = songMoments[index].text;
    songLine.classList.remove("is-changing");
    return;
  }

  songLine.classList.add("is-changing");
  songLineTransitionTimer = window.setTimeout(() => {
    songLine.textContent = songMoments[index].text;
    songLine.classList.remove("is-changing");
  }, 220);
};

const updateRelationshipTimer = () => {
  const diff = Math.max(0, Date.now() - relationshipStart.getTime());
  const totalSeconds = Math.floor(diff / 1000);
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  document.querySelector('[data-time-part="days"]').textContent = String(days).padStart(3, "0");
  document.querySelector('[data-time-part="hours"]').textContent = pad(hours);
  document.querySelector('[data-time-part="minutes"]').textContent = pad(minutes);
  document.querySelector('[data-time-part="seconds"]').textContent = pad(seconds);
};

const updateSongMoment = () => {
  const currentTime = song.currentTime || 0;
  const duration = Number.isFinite(song.duration) ? song.duration : 0;
  const momentIndex = songMoments.findLastIndex((item) => currentTime >= item.time);

  if (!lyricsReady) {
    clearSongLine();
  } else if (momentIndex >= 0) {
    showSongLine(momentIndex, activeSongMomentIndex === -1);
  } else if (isUsingTimedLyrics) {
    clearSongLine();
  }

  songCurrent.textContent = formatSongTime(currentTime);
  songDuration.textContent = formatSongTime(duration);
  songProgress.style.width = duration > 0 ? `${Math.min(100, (currentTime / duration) * 100)}%` : "0%";
};

for (let index = 0; index < 34; index += 1) {
  const drop = document.createElement("span");
  drop.className = "drop";
  drop.style.setProperty("--drop-left", `${Math.round(Math.random() * 110)}%`);
  drop.style.setProperty("--drop-height", `${44 + Math.round(Math.random() * 42)}px`);
  drop.style.setProperty("--drop-speed", `${2.7 + Math.random() * 2.8}s`);
  drop.style.setProperty("--drop-delay", `${Math.random() * -5}s`);
  rain.append(drop);
}

body.classList.add("warm");
song.volume = 0.42;
setPlaybackState(false);

playButton.addEventListener("click", async () => {
  clearTimeout(playbackErrorTimer);
  playButton.classList.remove("is-error");

  if (!song.paused) {
    song.pause();
    return;
  }

  try {
    await song.play();
    setPlaybackState(true);
  } catch {
    setPlaybackState(false);
    playButton.classList.add("is-error");
    playbackErrorTimer = window.setTimeout(() => {
      playButton.classList.remove("is-error");
      setPlaybackState(false);
    }, 900);
  }
});

song.addEventListener("loadedmetadata", updateSongMoment);
song.addEventListener("timeupdate", updateSongMoment);
song.addEventListener("playing", () => setPlaybackState(true));
song.addEventListener("pause", () => setPlaybackState(false));
song.addEventListener("ended", () => setPlaybackState(false));
song.addEventListener("error", () => {
  setPlaybackState(false);
});

updateRelationshipTimer();
updateSongMoment();
loadLrc();
setInterval(updateRelationshipTimer, 1000);
