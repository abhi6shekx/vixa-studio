const videoInput = document.querySelector("#videoInput");
const video = document.querySelector("#video");
const projectName = document.querySelector("#projectName");
const statusText = document.querySelector("#status");
const newProjectBtn = document.querySelector("#newProjectBtn");
const generateBtn = document.querySelector("#generateBtn");
const topGenerateBtn = document.querySelector("#topGenerateBtn");
const exportBtn = document.querySelector("#exportBtn");
const applyBtn = document.querySelector("#applyBtn");
const backendStatus = document.querySelector("#backendStatus");
const promptInput = document.querySelector("#prompt");
const stage = document.querySelector("#stage");
const downloadLink = document.querySelector("#downloadLink");
const captionOverlay = document.querySelector("#captionOverlay");
const timeline = document.querySelector("#timeline");
const captionsList = document.querySelector("#captionsList");
const durationMetric = document.querySelector("#durationMetric");
const cutsMetric = document.querySelector("#cutsMetric");
const styleMetric = document.querySelector("#styleMetric");
const planSummary = document.querySelector("#planSummary");
const captionsToggle = document.querySelector("#captionsToggle");
const zoomToggle = document.querySelector("#zoomToggle");
const silenceToggle = document.querySelector("#silenceToggle");
const musicToggle = document.querySelector("#musicToggle");
const buttonLabel = generateBtn?.querySelector(".button-label");
const photoInput = document.querySelector("#photoInput");
const photoPrompt = document.querySelector("#photoPrompt");
const photoGenerateBtn = document.querySelector("#photoGenerateBtn");
const photoButtonLabel = photoGenerateBtn?.querySelector(".photo-button-label");
const photoStage = document.querySelector("#photoStage");
const photoPlaceholder = document.querySelector("#photoPlaceholder");
const photoPreviewStack = document.querySelector("#photoPreviewStack");
const photoPreviewImage = document.querySelector("#photoPreviewImage");
const photoPreviewCaption = document.querySelector("#photoPreviewCaption");
const photoPreviewMeta = document.querySelector("#photoPreviewMeta");
const photoRenderedVideo = document.querySelector("#photoRenderedVideo");
const styleImageInput = document.querySelector("#styleImageInput");
const styleReferenceInput = document.querySelector("#styleReferenceInput");
const styleImageName = document.querySelector("#styleImageName");
const styleReferenceName = document.querySelector("#styleReferenceName");
const stylePrompt = document.querySelector("#stylePrompt");
const styleGenerateBtn = document.querySelector("#styleGenerateBtn");
const styleButtonLabel = styleGenerateBtn?.querySelector(".style-button-label");
const styleStatus = document.querySelector("#styleStatus");
const stylePlaceholder = document.querySelector("#stylePlaceholder");
const styleOutputImage = document.querySelector("#styleOutputImage");
const styleDownloadLink = document.querySelector("#styleDownloadLink");
const voiceText = document.querySelector("#voiceText");
const voiceLanguage = document.querySelector("#voiceLanguage");
const voiceType = document.querySelector("#voiceType");
const voiceEmotion = document.querySelector("#voiceEmotion");
const voiceGenerateBtn = document.querySelector("#voiceGenerateBtn");
const voiceButtonLabel = voiceGenerateBtn?.querySelector(".voice-button-label");
const voiceStatus = document.querySelector("#voiceStatus");
const voiceAudio = document.querySelector("#voiceAudio");
const voiceDownloadLink = document.querySelector("#voiceDownloadLink");
const mainVideoInput = document.querySelector("#mainVideo");
const referenceVideoInput = document.querySelector("#referenceVideo");
const referencePrompt = document.querySelector("#referencePrompt");
const referenceGenerateBtn = document.querySelector("#referenceGenerateBtn");
const referenceButtonLabel = referenceGenerateBtn?.querySelector(".reference-button-label");
const mainVideoName = document.querySelector("#mainVideoName");
const referenceVideoName = document.querySelector("#referenceVideoName");
const referenceStatus = document.querySelector("#referenceStatus");
const analysisTone = document.querySelector("#analysisTone");
const analysisSpeed = document.querySelector("#analysisSpeed");
const analysisCuts = document.querySelector("#analysisCuts");
const analysisTransitions = document.querySelector("#analysisTransitions");
const analysisCaptions = document.querySelector("#analysisCaptions");
const analysisRatio = document.querySelector("#analysisRatio");
const analysisBeat = document.querySelector("#analysisBeat");
const analysisZoom = document.querySelector("#analysisZoom");
const aiSummary = document.querySelector("#aiSummary");
const aiPromptSource = document.querySelector("#aiPromptSource");
const aiSceneCount = document.querySelector("#aiSceneCount");
const aiCaptionCount = document.querySelector("#aiCaptionCount");
const aiSilenceCount = document.querySelector("#aiSilenceCount");
const settingsAiProvider = document.querySelector("#settingsAiProvider");
const settingsAiModel = document.querySelector("#settingsAiModel");
const settingsOpenAi = document.querySelector("#settingsOpenAi");
const settingsWhisper = document.querySelector("#settingsWhisper");
const settingsSceneAi = document.querySelector("#settingsSceneAi");
const aiTestPrompt = document.querySelector("#aiTestPrompt");
const aiTestBtn = document.querySelector("#aiTestBtn");
const aiTestOutput = document.querySelector("#aiTestOutput");
const analyzePromptBtn = document.querySelector("#analyzePromptBtn");
const promptAiOutput = document.querySelector("#promptAiOutput");
const copilotPrompt = document.querySelector("#copilotPrompt");
const copilotMediaContext = document.querySelector("#copilotMediaContext");
const copilotGenerateBtn = document.querySelector("#copilotGenerateBtn");
const copilotButtonLabel = copilotGenerateBtn?.querySelector(".copilot-button-label");
const copilotResultTitle = document.querySelector("#copilotResultTitle");
const copilotStatus = document.querySelector("#copilotStatus");
const copilotScore = document.querySelector("#copilotScore");
const copilotRecommendations = document.querySelector("#copilotRecommendations");
const copilotJson = document.querySelector("#copilotJson");
const engineReadyCount = document.querySelector("#engineReadyCount");
const engineRuntime = document.querySelector("#engineRuntime");
const engineGrid = document.querySelector("#engineGrid");

const pageRoutes = {
  "/": "dashboard",
  "/create": "create",
  "/tools": "tools",
  "/assets": "assets",
  "/assistant": "assistant",
  "/admin/engines": "engines",
  "/copilot": "copilot",
  "/editor": "editor",
  "/reference-match": "reference",
  "/photo-to-video": "photo",
  "/style-transform": "style",
  "/templates": "templates",
  "/projects": "projects",
  "/voice": "voice",
  "/subtitles": "subtitles",
  "/music": "music",
  "/analytics": "analytics",
  "/settings": "settings",
};

const pagePaths = Object.fromEntries(Object.entries(pageRoutes).map(([path, page]) => [page, path]));

let editPlan = [];
let captions = [];
let activeCaptionIndex = 0;
let selectedFile = null;
let selectedStyle = "cinematic";
let selectedPhotoMotion = "slow-zoom";
let selectedPhotoDuration = 5;
let selectedPhotoRatio = "16:9";
let selectedImageStyle = "voxel";
let selectedCopilotMode = "copilot";
let photoUrls = [];
let photoTimer = null;
let photoIndex = 0;

const photoMotionLabels = {
  "slow-zoom": "Slow Zoom",
  "pan-left": "Pan Left",
  "pan-right": "Pan Right",
  parallax: "3D Parallax",
  cinematic: "Cinematic Motion",
  anime: "Anime Motion",
  product: "Product Showcase",
};

function pageMatches(element, page) {
  return (element.dataset.page || "").split(/\s+/).includes(page);
}

function showPage(page, options = {}) {
  const nextPage = pagePaths[page] ? page : "dashboard";
  document.querySelectorAll("[data-page-section]").forEach((section) => {
    section.classList.toggle("page-hidden", !pageMatches(section, nextPage));
  });
  document.querySelectorAll("[data-page-aside]").forEach((aside) => {
    aside.classList.toggle("page-hidden", !pageMatches(aside, nextPage));
  });
  document.querySelectorAll(".nav-item").forEach((item) => {
    item.classList.toggle("active", item.dataset.page === nextPage);
  });
  document.body.dataset.page = nextPage;
  if (options.push !== false) {
    history.pushState({ page: nextPage }, "", pagePaths[nextPage]);
  }
  if (options.scroll !== false) {
    window.scrollTo({ top: 0, behavior: options.instant ? "auto" : "smooth" });
  }
}

function formatTime(seconds) {
  if (!Number.isFinite(seconds)) return "--";
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60).toString().padStart(2, "0");
  return `${mins}:${secs}`;
}

function makePlan(duration) {
  const safeDuration = Math.max(duration || 36, 18);
  const parts = [
    { label: "Hook", start: 0, end: Math.min(4, safeDuration * 0.12), type: "keep" },
    { label: "Pause", start: safeDuration * 0.12, end: safeDuration * 0.2, type: "cut" },
    { label: "Point 1", start: safeDuration * 0.2, end: safeDuration * 0.42, type: "keep" },
    { label: "Dead air", start: safeDuration * 0.42, end: safeDuration * 0.5, type: "cut" },
    { label: "Point 2", start: safeDuration * 0.5, end: safeDuration * 0.74, type: "keep" },
    { label: "CTA", start: safeDuration * 0.74, end: safeDuration, type: "keep" },
  ];

  return parts.map((part) => ({
    ...part,
    start: Math.max(0, part.start),
    end: Math.min(safeDuration, part.end),
  }));
}

function makeCaptions(plan, prompt) {
  const wantsShort = /short|reel|tiktok|viral|clip/i.test(prompt);
  const wantsDrama = /dramatic|anime|cinematic/i.test(prompt);
  const lines = wantsShort
    ? ["Here is the hook", "This is the key moment", "Watch what changes next", "Save this idea"]
    : wantsDrama
      ? ["A cinematic opening", "The tension builds", "A polished transition", "The final reveal"]
    : ["AI caption generated", "Important section", "Main takeaway", "Final note"];

  return plan
    .filter((clip) => clip.type === "keep")
    .slice(0, 4)
    .map((clip, index) => ({
      start: clip.start,
      end: clip.end,
      text: lines[index],
    }));
}

function renderTimeline() {
  timeline.innerHTML = "";
  editPlan.forEach((clip) => {
    const item = document.createElement("button");
    item.className = `clip ${clip.type}`;
    item.innerHTML = `<strong>${clip.label}</strong><small>${formatTime(clip.start)} - ${formatTime(clip.end)}</small>`;
    item.addEventListener("click", () => {
      if (video.src) {
        video.currentTime = clip.start;
        video.play();
      }
    });
    timeline.appendChild(item);
  });
}

function renderCaptions() {
  captionsList.innerHTML = "";
  captions.forEach((caption) => {
    const item = document.createElement("div");
    item.className = "caption-item";
    item.innerHTML = `<span>${formatTime(caption.start)} - ${formatTime(caption.end)}</span>${caption.text}`;
    captionsList.appendChild(item);
  });
}

function updateCaptionOverlay() {
  if (!captionsToggle.checked) {
    captionOverlay.style.display = "none";
    return;
  }
  captionOverlay.style.display = "block";

  const match = captions.findIndex((caption) => video.currentTime >= caption.start && video.currentTime <= caption.end);
  if (match >= 0) activeCaptionIndex = match;
  captionOverlay.textContent = captions[activeCaptionIndex]?.text || "AI captions will appear here";
}

function setGenerateLoading(isLoading) {
  generateBtn.disabled = isLoading || !selectedFile;
  topGenerateBtn.disabled = isLoading;
  generateBtn.classList.toggle("is-loading", isLoading);
  if (buttonLabel) buttonLabel.textContent = isLoading ? "Generating" : "Generate with Free AI";
  topGenerateBtn.textContent = isLoading ? "Generating..." : "Start New Project";
}

function updateGenerateAvailability() {
  generateBtn.disabled = !selectedFile;
  generateBtn.title = selectedFile ? "Render this video with the AI engine" : "Upload a video first";
}

async function checkBackendHealth() {
  if (!backendStatus) return;
  try {
    const response = await fetch("/health");
    const health = await response.json();
    if (!response.ok || health.status !== "ok") throw new Error("AI engine offline");
    backendStatus.className = "backend-status";
    const aiLabel = health.openai ? "OpenAI" : health.whisper ? "Whisper" : "Local AI";
    backendStatus.querySelector("strong").textContent = health.ffmpeg ? `${aiLabel} Engine Online` : "Plan Mode Only";
    statusText.textContent = health.ffmpeg ? `${aiLabel} engine connected. Upload a video to start.` : "Backend connected, but FFmpeg is missing.";
  } catch (error) {
    backendStatus.className = "backend-status offline";
    backendStatus.querySelector("strong").textContent = "Backend Offline";
    statusText.textContent = "Backend is not connected. Run python3 app.py and open http://127.0.0.1:5050";
  }
}

function yesNo(value) {
  return value ? "Connected" : "Not connected";
}

async function refreshAiSettings() {
  if (!settingsAiProvider) return;
  try {
    const response = await fetch("/api/ai/status");
    const status = await response.json();
    settingsAiProvider.textContent = status.provider === "openai" ? "OpenAI" : "Local AI";
    settingsAiModel.textContent = status.model || "--";
    settingsOpenAi.textContent = yesNo(status.openai);
    settingsWhisper.textContent = yesNo(status.whisper);
    settingsSceneAi.textContent = yesNo(status.scene_ai);
  } catch (error) {
    settingsAiProvider.textContent = "Offline";
    settingsAiModel.textContent = "--";
    settingsOpenAi.textContent = "--";
    settingsWhisper.textContent = "--";
    settingsSceneAi.textContent = "--";
  }
}

function renderEngines(data) {
  if (!engineGrid) return;
  engineReadyCount.textContent = `${data.ready}/${data.total}`;
  engineRuntime.textContent = data.runtime === "vercel" ? "Vercel lightweight" : "Local Mac";
  engineGrid.innerHTML = (data.engines || [])
    .map((engine) => `
      <article class="engine-card ${engine.ready ? "ready" : "missing"}">
        <div>
          <strong>${engine.name}</strong>
          <span>${engine.engine}</span>
        </div>
        <b>${engine.ready ? "Ready" : "Setup needed"}</b>
        <p>${(engine.tasks || []).join(" • ")}</p>
        <small>${engine.setup}</small>
      </article>
    `)
    .join("");
}

async function refreshFreeEngines() {
  if (!engineGrid) return;
  try {
    const response = await fetch("/api/ai/engines");
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || "Engine scan failed");
    renderEngines(data);
  } catch (error) {
    engineGrid.innerHTML = `<article class="engine-card missing"><strong>Engine scan failed</strong><span>${error.message || "Backend unavailable"}</span></article>`;
  }
}

async function testAiBrain() {
  if (!aiTestPrompt || !aiTestOutput) return;
  aiTestBtn.disabled = true;
  aiTestOutput.textContent = "Thinking...";
  try {
    const response = await fetch("/api/ai/prompt", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: aiTestPrompt.value }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.message || "AI prompt test failed");
    aiTestOutput.textContent = JSON.stringify(result.actions, null, 2);
  } catch (error) {
    aiTestOutput.textContent = error.message || "AI prompt test failed";
  } finally {
    aiTestBtn.disabled = false;
  }
}

async function analyzePromptInEditor() {
  if (!promptAiOutput) return;
  analyzePromptBtn.disabled = true;
  promptAiOutput.textContent = "Free AI is reading your prompt...";
  try {
    const response = await fetch("/api/ai/prompt", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: `${promptInput.value} ${selectedStyle}` }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.message || "Prompt AI failed");
    promptAiOutput.textContent = JSON.stringify(result.actions, null, 2);
    aiPromptSource.textContent = result.provider || result.actions?.source || "local-ai-parser";
    statusText.textContent = "Prompt AI analyzed your edit instructions";
  } catch (error) {
    promptAiOutput.textContent = error.message || "Prompt AI failed";
  } finally {
    analyzePromptBtn.disabled = false;
  }
}

function setPhotoLoading(isLoading) {
  photoGenerateBtn.disabled = isLoading;
  photoGenerateBtn.classList.toggle("is-loading", isLoading);
  if (photoButtonLabel) {
    photoButtonLabel.textContent = isLoading ? "Generating" : "Generate Video from Photos";
  }
}

function setStyleLoading(isLoading) {
  if (!styleGenerateBtn) return;
  styleGenerateBtn.disabled = isLoading;
  styleGenerateBtn.classList.toggle("is-loading", isLoading);
  if (styleButtonLabel) {
    styleButtonLabel.textContent = isLoading ? "Generating AI Edit" : "Generate AI Image Edit";
  }
}

function setVoiceLoading(isLoading) {
  if (!voiceGenerateBtn) return;
  voiceGenerateBtn.disabled = isLoading;
  voiceGenerateBtn.classList.toggle("is-loading", isLoading);
  if (voiceButtonLabel) {
    voiceButtonLabel.textContent = isLoading ? "Generating Voice" : "Generate Voiceover";
  }
}

function setCopilotLoading(isLoading) {
  if (!copilotGenerateBtn) return;
  copilotGenerateBtn.disabled = isLoading;
  copilotGenerateBtn.classList.toggle("is-loading", isLoading);
  if (copilotButtonLabel) {
    copilotButtonLabel.textContent = isLoading ? "Thinking" : "Generate Creator Plan";
  }
}

function setReferenceLoading(isLoading) {
  referenceGenerateBtn.disabled = isLoading;
  referenceGenerateBtn.classList.toggle("is-loading", isLoading);
  if (referenceButtonLabel) {
    referenceButtonLabel.textContent = isLoading ? "Matching Reference" : "Match Reference Style ✨";
  }
}

function clearPhotoTimer() {
  if (photoTimer) {
    clearInterval(photoTimer);
    photoTimer = null;
  }
}

function updatePhotoMotionClass() {
  photoStage.classList.remove(
    "motion-slow-zoom",
    "motion-pan-left",
    "motion-pan-right",
    "motion-parallax",
    "motion-cinematic",
    "motion-anime",
    "motion-product",
  );
  photoStage.classList.add(`motion-${selectedPhotoMotion}`);
}

function updatePhotoRatioClass() {
  photoStage.classList.remove("ratio-wide", "ratio-vertical", "ratio-square");
  const ratioClass = selectedPhotoRatio === "9:16" ? "ratio-vertical" : selectedPhotoRatio === "1:1" ? "ratio-square" : "ratio-wide";
  photoStage.classList.add(ratioClass);
}

function resetPhotoObjectUrls() {
  photoUrls.forEach((url) => URL.revokeObjectURL(url));
  photoUrls = [];
}

function showPhotoFrame(index) {
  if (!photoUrls.length) return;
  photoPreviewStack.classList.add("is-switching");
  setTimeout(() => {
    photoPreviewImage.src = photoUrls[index];
    photoPreviewStack.classList.remove("is-switching");
  }, 160);
}

function buildPhotoCaption(prompt) {
  const label = photoMotionLabels[selectedPhotoMotion] || "Cinematic Motion";
  const effect = /rain|storm|drizzle/i.test(prompt) ? "Rain effect" : "AI motion";
  return `${label} • ${effect}`;
}

function showRenderedOutput(result, fallbackName = "Vixa AI render") {
  if (!result?.output_url) return false;
  video.src = result.output_url;
  video.load();
  projectName.textContent = fallbackName;
  captionOverlay.textContent = "Rendered output ready";
  captionOverlay.style.display = "block";
  if (downloadLink) {
    downloadLink.href = result.download_url || result.output_url;
    downloadLink.hidden = false;
  }
  return true;
}

function resetNewProject(options = {}) {
  const { scrollToEditor = true, navigateToEditor = true } = options;
  selectedFile = null;
  editPlan = makePlan(36);
  captions = makeCaptions(editPlan, promptInput.value || "cinematic");
  activeCaptionIndex = 0;

  video.pause();
  video.removeAttribute("src");
  video.load();
  videoInput.value = "";
  mainVideoInput.value = "";
  referenceVideoInput.value = "";
  photoInput.value = "";

  projectName.textContent = "Untitled Vixa project";
  statusText.textContent = "New project ready. Upload a video to start.";
  captionOverlay.style.display = "block";
  captionOverlay.textContent = "Upload a video to preview edits";
  mainVideoName.textContent = "No video selected";
  referenceVideoName.textContent = "No reference selected";
  referenceStatus.textContent = "Waiting for both videos";
  photoPreviewMeta.textContent = "Upload photos and generate motion";
  photoPlaceholder.hidden = false;
  photoPreviewStack.hidden = true;
  photoRenderedVideo.hidden = true;
  photoRenderedVideo.removeAttribute("src");
  photoRenderedVideo.load();
  photoStage.classList.remove("is-playing", "has-rain");
  if (styleImageInput) styleImageInput.value = "";
  if (styleReferenceInput) styleReferenceInput.value = "";
  if (styleImageName) styleImageName.textContent = "JPG, PNG, or WebP";
  if (styleReferenceName) styleReferenceName.textContent = "Use this for reference style copy";
  if (styleStatus) styleStatus.textContent = "Upload a photo to begin";
  if (stylePlaceholder) stylePlaceholder.hidden = false;
  if (styleOutputImage) {
    styleOutputImage.hidden = true;
    styleOutputImage.removeAttribute("src");
  }
  if (styleDownloadLink) {
    styleDownloadLink.hidden = true;
    styleDownloadLink.href = "#";
  }
  if (voiceStatus) voiceStatus.textContent = "Ready for script";
  if (voiceAudio) {
    voiceAudio.hidden = true;
    voiceAudio.removeAttribute("src");
    voiceAudio.load();
  }
  if (voiceDownloadLink) {
    voiceDownloadLink.hidden = true;
    voiceDownloadLink.href = "#";
  }
  clearPhotoTimer();
  resetPhotoObjectUrls();

  if (downloadLink) {
    downloadLink.hidden = true;
    downloadLink.href = "#";
  }

  updateReferenceAnalysis(null);
  renderTimeline();
  renderCaptions();
  cutsMetric.textContent = editPlan.filter((clip) => clip.type === "cut").length;
  durationMetric.textContent = "--";
  planSummary.textContent = "New project created";
  updateGenerateAvailability();
  updateAiIntelligence(null);

  if (navigateToEditor) {
    showPage("editor", { push: true, scroll: scrollToEditor });
  }
}

async function generatePhotoVideo() {
  const files = Array.from(photoInput.files || []);
  const prompt = photoPrompt.value.trim();

  if (!files.length) {
    photoPreviewMeta.textContent = "Choose at least one image first";
    statusText.textContent = "Photo to Video needs one or more images";
    photoInput.focus();
    return;
  }

  setPhotoLoading(true);
  statusText.textContent = "Uploading photos to AI renderer...";
  photoPreviewMeta.textContent = "Rendering real MP4 video...";

  try {
    const formData = new FormData();
    files.forEach((file) => formData.append("images", file));
    formData.append("prompt", prompt);
    formData.append("motion", selectedPhotoMotion);
    formData.append("duration", selectedPhotoDuration);
    formData.append("aspect_ratio", selectedPhotoRatio);

    const response = await fetch("/photo-to-video", { method: "POST", body: formData });
    const result = await response.json();
    if (!response.ok || result.status === "render-error" || result.status === "error") {
      throw new Error(result.message || "Photo to Video render failed");
    }

    updatePhotoMotionClass();
    updatePhotoRatioClass();
    photoStage.style.setProperty("--photo-duration", `${selectedPhotoDuration}s`);
    photoStage.classList.remove("has-rain", "is-playing");
    clearPhotoTimer();
    resetPhotoObjectUrls();
    photoPreviewStack.hidden = true;
    photoStage.classList.remove("is-playing");
    photoPlaceholder.hidden = true;
    photoRenderedVideo.hidden = false;
    photoRenderedVideo.src = result.output_url;
    photoRenderedVideo.load();
    photoRenderedVideo.play().catch(() => {});

    showRenderedOutput(result, "Photo to Video render");
    photoPreviewMeta.textContent = `${files.length} image${files.length === 1 ? "" : "s"} • real MP4 rendered • ${selectedPhotoDuration} sec • ${selectedPhotoRatio}`;
    statusText.textContent = result.message || "Photo to Video AI rendered successfully";
  } catch (error) {
    statusText.textContent = error.message || "Photo to Video render failed";
    photoPreviewMeta.textContent = "Render failed. Check FFmpeg and try again.";
  } finally {
    setPhotoLoading(false);
  }
}

async function generateStyleTransform() {
  const file = styleImageInput?.files?.[0];
  if (!file) {
    styleStatus.textContent = "Upload a photo first";
    styleImageInput?.focus();
    return;
  }

  const formData = new FormData();
  formData.append("image", file);
  formData.append("style", selectedImageStyle);
  formData.append("prompt", stylePrompt?.value || "");
  const reference = styleReferenceInput?.files?.[0];
  if (reference) formData.append("reference_image", reference);

  setStyleLoading(true);
  styleStatus.textContent = "Local AI is transforming your photo...";

  try {
    const response = await fetch("/style-transform", { method: "POST", body: formData });
    const result = await response.json();
    if (!response.ok || !result.output_url) {
      throw new Error(result.message || "AI style transform failed");
    }

    stylePlaceholder.hidden = true;
    styleOutputImage.hidden = false;
    styleOutputImage.src = `${result.output_url}?t=${Date.now()}`;
    styleDownloadLink.href = result.download_url || result.output_url;
    styleDownloadLink.hidden = false;
    styleStatus.textContent = `${result.message} Style: ${result.style}`;
    statusText.textContent = "AI Style Transform generated a real image output";
  } catch (error) {
    styleStatus.textContent = error.message || "AI style transform failed";
    statusText.textContent = "AI Style Transform failed. Check backend logs.";
  } finally {
    setStyleLoading(false);
  }
}

async function generateVoiceover() {
  const text = voiceText?.value?.trim() || "";
  if (!text) {
    voiceStatus.textContent = "Write a script first";
    voiceText?.focus();
    return;
  }

  setVoiceLoading(true);
  voiceStatus.textContent = "Generating local AI voiceover...";

  try {
    const response = await fetch("/api/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text,
        language: voiceLanguage?.value || "english",
        voice: voiceType?.value || "narrator",
        emotion: voiceEmotion?.value || "neutral",
      }),
    });
    const result = await response.json();
    if (!response.ok || !result.output_url) {
      throw new Error(result.message || "Voice generation failed");
    }

    voiceAudio.hidden = false;
    voiceAudio.src = `${result.output_url}?t=${Date.now()}`;
    voiceAudio.load();
    voiceAudio.play().catch(() => {});
    voiceDownloadLink.href = result.download_url || result.output_url;
    voiceDownloadLink.hidden = false;
    voiceStatus.textContent = `${result.message} Engine: ${result.meta?.engine || "local"}`;
    statusText.textContent = "Voice Studio generated a real audio file";
  } catch (error) {
    voiceStatus.textContent = error.message || "Voice generation failed";
    statusText.textContent = "Voice Studio failed. Check backend logs.";
  } finally {
    setVoiceLoading(false);
  }
}

async function generateCopilotPlan() {
  const prompt = copilotPrompt?.value?.trim() || "";
  if (!prompt) {
    copilotStatus.textContent = "Write a prompt first";
    copilotPrompt?.focus();
    return;
  }

  setCopilotLoading(true);
  copilotStatus.textContent = "Vixa AI is building your creator plan...";

  try {
    const response = await fetch("/api/copilot", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        mode: selectedCopilotMode,
        prompt,
        media_context: copilotMediaContext?.value || "",
      }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.message || "AI Copilot failed");

    copilotResultTitle.textContent = result.title || "AI Creator Plan";
    copilotStatus.textContent = "Creator plan generated";
    copilotScore.textContent = Number.isFinite(result.score) ? `${result.score}/10` : "--";
    copilotRecommendations.innerHTML = (result.recommendations || [])
      .map((item) => `<p>${item}</p>`)
      .join("");
    copilotJson.textContent = JSON.stringify({
      mode: result.mode,
      actions: result.actions,
      pipeline: result.pipeline,
      next_tools: result.next_tools,
    }, null, 2);
    statusText.textContent = "AI Copilot generated a creator plan";
  } catch (error) {
    copilotStatus.textContent = error.message || "AI Copilot failed";
    copilotJson.textContent = "Could not generate plan.";
  } finally {
    setCopilotLoading(false);
  }
}

function updateReferenceAnalysis(analysis) {
  analysisTone.textContent = analysis?.color_tone || "--";
  analysisSpeed.textContent = analysis?.speed || "--";
  analysisCuts.textContent = analysis?.cuts || "--";
  analysisTransitions.textContent = analysis?.transitions || "--";
  analysisCaptions.textContent = analysis?.captions_style || "--";
  analysisRatio.textContent = analysis?.aspect_ratio || "--";
  analysisBeat.textContent = analysis?.music_beat || "--";
  analysisZoom.textContent = analysis?.zoom_style || "--";
}

function updateAiIntelligence(result) {
  const ai = result?.ai;
  const analysis = result?.plan?.ai_analysis;
  aiPromptSource.textContent = ai?.actions?.source || "--";
  aiSceneCount.textContent = ai?.scene_count ? `${ai.scene_count} scenes` : "--";
  aiCaptionCount.textContent = Number.isFinite(ai?.captions_generated) ? `${ai.captions_generated} captions` : "--";
  aiSilenceCount.textContent = Number.isFinite(ai?.silence_segments) ? `${ai.silence_segments} cuts` : "--";
  if (analysis?.scene?.highlights?.length) {
    aiSummary.textContent = `${analysis.scene.highlights.length} highlight moments found with ${analysis.scene.source} scene AI`;
  } else if (ai) {
    aiSummary.textContent = "AI analysis completed";
  } else {
    aiSummary.textContent = "Upload and generate to see AI analysis";
  }
}

async function generateReferenceEdit() {
  const mainFile = mainVideoInput.files?.[0];
  const referenceFile = referenceVideoInput.files?.[0];
  const prompt = referencePrompt.value.trim();

  if (!mainFile || !referenceFile) {
    referenceStatus.textContent = "Upload both videos first";
    statusText.textContent = "Reference Match AI needs your video and a reference video";
    return;
  }

  const formData = new FormData();
  formData.append("main_video", mainFile);
  formData.append("reference_video", referenceFile);
  formData.append("prompt", prompt);

  setReferenceLoading(true);
  referenceStatus.textContent = "Analyzing reference style...";
  statusText.textContent = "Matching your video to the reference vibe...";

  try {
    const response = await fetch("/reference-edit", { method: "POST", body: formData });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.message || "Reference style match failed");
    }

    updateReferenceAnalysis(result.analysis);
    referenceStatus.textContent = result.message || "Reference style matched";
    statusText.textContent = "Reference Match AI generated a style plan";

    if (result.output_url) {
      showRenderedOutput(result, "Reference matched edit");
    } else {
      video.src = URL.createObjectURL(mainFile);
      projectName.textContent = mainFile.name;
      captionOverlay.textContent = "Reference style plan ready";
    }
  } catch (error) {
    referenceStatus.textContent = "Could not match reference";
    statusText.textContent = error.message || "Reference Match AI failed";
  } finally {
    setReferenceLoading(false);
  }
}

function applyServerPlan(serverPlan) {
  if (!serverPlan) return;
  editPlan = serverPlan.cuts || editPlan;
  captions = Array.isArray(serverPlan.caption_items) && serverPlan.caption_items.length
    ? serverPlan.caption_items
    : serverPlan.captions
      ? editPlan
          .filter((clip) => clip.type === "keep")
          .slice(0, 4)
          .map((clip, index) => ({
            start: clip.start,
            end: clip.end,
            text: ["Strong hook", "Key moment", "Main takeaway", "Final beat"][index] || "AI caption",
          }))
      : [];
}

async function generatePlan() {
  if (!selectedFile) {
    statusText.textContent = "Upload a video first. This is a real renderer, not a slideshow demo.";
    captionOverlay.textContent = "Choose a video file, then click Generate Video";
    videoInput.focus();
    updateGenerateAvailability();
    return;
  }

  const prompt = promptInput.value.trim();
  const styledPrompt = `${prompt} ${selectedStyle}`.trim();
  setGenerateLoading(true);
  statusText.textContent = "Uploading video to AI engine...";

  if (location.protocol !== "file:") {
    const formData = new FormData();
    formData.append("video", selectedFile);
    formData.append("prompt", styledPrompt);

    try {
      const response = await fetch("/edit", { method: "POST", body: formData });
      const result = await response.json();
      applyServerPlan(result.plan);
      if (result.output_url) {
        showRenderedOutput(result, selectedFile.name);
      }
      updateAiIntelligence(result);
      statusText.textContent = result.message || "AI edit generated";
    } catch (error) {
      editPlan = makePlan(video.duration);
      captions = makeCaptions(editPlan, styledPrompt);
      statusText.textContent = "Server render failed, showing browser preview plan";
    }
  } else {
    editPlan = makePlan(video.duration);
    captions = makeCaptions(editPlan, styledPrompt);
    statusText.textContent = "Open http://127.0.0.1:5050 to render with the backend.";
  }

  renderTimeline();
  renderCaptions();

  const cuts = editPlan.filter((clip) => clip.type === "cut").length;
  const keptSeconds = editPlan.filter((clip) => clip.type === "keep").reduce((sum, clip) => sum + clip.end - clip.start, 0);
  cutsMetric.textContent = cuts;
  durationMetric.textContent = formatTime(keptSeconds);
  styleMetric.textContent = selectedStyle.replace(/\b\w/g, (letter) => letter.toUpperCase());
  planSummary.textContent = `${cuts} cuts, ${captions.length} captions, ${formatTime(keptSeconds)} output`;
  updateCaptionOverlay();
  setGenerateLoading(false);
  updateGenerateAvailability();
}

videoInput.addEventListener("change", () => {
  const file = videoInput.files?.[0];
  if (!file) return;
  selectedFile = file;
  updateGenerateAvailability();
  video.src = URL.createObjectURL(file);
  projectName.textContent = file.name;
  statusText.textContent = "Video loaded";
  captionOverlay.textContent = "Click generate AI edit";
});

video.addEventListener("loadedmetadata", () => {
  durationMetric.textContent = formatTime(video.duration);
});

video.addEventListener("timeupdate", updateCaptionOverlay);

generateBtn.addEventListener("click", generatePlan);
topGenerateBtn.addEventListener("click", () => showPage("create"));
newProjectBtn.addEventListener("click", () => showPage("create"));

applyBtn.addEventListener("click", () => {
  if (!selectedFile && !editPlan.length) {
    statusText.textContent = "Upload and generate a real edit before applying controls.";
    videoInput.focus();
    return;
  }
  if (!editPlan.length) generatePlan();
  stage.classList.toggle("ai-focus", zoomToggle.checked);
  statusText.textContent = silenceToggle.checked ? "Plan applied: silence sections marked for removal" : "Plan applied";
  updateCaptionOverlay();
});

exportBtn.addEventListener("click", () => {
  if (!editPlan.length) {
    statusText.textContent = "Generate a real edit first, then export the edit plan.";
    videoInput.focus();
    return;
  }
  const exported = {
    prompt: promptInput.value,
    style: selectedStyle,
    format: document.querySelector(".segment.active").dataset.format,
    captions: captionsToggle.checked,
    autoZoom: zoomToggle.checked,
    removeSilence: silenceToggle.checked,
    backgroundMusic: musicToggle.checked,
    timeline: editPlan,
  };
  const blob = new Blob([JSON.stringify(exported, null, 2)], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "ai-video-edit-plan.json";
  link.click();
  URL.revokeObjectURL(link.href);
  statusText.textContent = "Preview edit plan exported";
});

document.querySelectorAll(".segment").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".segment").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    stage.classList.remove("vertical", "square", "wide");
    const format = button.dataset.format;
    stage.classList.add(format === "9:16" ? "vertical" : format === "1:1" ? "square" : "wide");
  });
});

document.querySelectorAll(".style-chip").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".style-chip").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    selectedStyle = button.dataset.style;
    styleMetric.textContent = button.textContent;
    statusText.textContent = `${button.textContent} style selected`;
  });
});

document.querySelectorAll("[data-template]").forEach((button) => {
  button.addEventListener("click", () => {
    promptInput.value = button.dataset.template;
    statusText.textContent = "Template copied into prompt editor";
    showPage("editor");
    promptInput.focus();
  });
});

document.querySelectorAll("[data-tool]").forEach((button) => {
  button.addEventListener("click", () => {
    const tool = button.dataset.tool;
    if (tool === "captions") captionsToggle.checked = true;
    if (tool === "silence") silenceToggle.checked = true;
    if (tool === "zoom") zoomToggle.checked = true;
    if (tool === "music") musicToggle.checked = true;
    button.classList.add("active");
    statusText.textContent = `${button.querySelector("strong")?.textContent || button.textContent} enabled`;
  });
});

document.querySelectorAll("[data-jump-page]").forEach((button) => {
  button.addEventListener("click", () => {
    const preset = button.dataset.copilotPreset;
    if (preset) {
      selectedCopilotMode = preset;
      document.querySelectorAll(".copilot-mode-chip").forEach((item) => {
        item.classList.toggle("active", item.dataset.mode === preset);
      });
      if (copilotStatus) copilotStatus.textContent = `${button.querySelector("strong")?.textContent || "AI mode"} selected`;
    }
    showPage(button.dataset.jumpPage || "dashboard");
  });
});

document.querySelectorAll(".nav-item").forEach((button) => {
  button.addEventListener("click", () => {
    showPage(button.dataset.page || "dashboard");
  });
});

document.querySelectorAll(".motion-chip").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".motion-chip").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    selectedPhotoMotion = button.dataset.motion;
    updatePhotoMotionClass();
    photoPreviewMeta.textContent = `${button.textContent} selected`;
  });
});

document.querySelectorAll(".duration-chip").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".duration-chip").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    selectedPhotoDuration = Number(button.dataset.duration);
    photoStage.style.setProperty("--photo-duration", `${selectedPhotoDuration}s`);
    photoPreviewMeta.textContent = `${button.textContent} duration selected`;
  });
});

document.querySelectorAll(".photo-ratio-chip").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".photo-ratio-chip").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    selectedPhotoRatio = button.dataset.ratio;
    updatePhotoRatioClass();
    photoPreviewMeta.textContent = `${selectedPhotoRatio} aspect ratio selected`;
  });
});

photoInput.addEventListener("change", () => {
  const count = photoInput.files?.length || 0;
  photoPreviewMeta.textContent = count ? `${count} image${count === 1 ? "" : "s"} ready for motion` : "Upload photos and generate motion";
  statusText.textContent = count ? "Photos loaded for Photo to Video AI" : statusText.textContent;
});

photoGenerateBtn.addEventListener("click", generatePhotoVideo);

styleImageInput?.addEventListener("change", () => {
  const file = styleImageInput.files?.[0];
  styleImageName.textContent = file ? file.name : "JPG, PNG, or WebP";
  styleStatus.textContent = file ? "Photo ready for AI Style Transform" : "Upload a photo to begin";
});

styleReferenceInput?.addEventListener("change", () => {
  const file = styleReferenceInput.files?.[0];
  styleReferenceName.textContent = file ? file.name : "Use this for reference style copy";
  if (file) styleStatus.textContent = "Reference image loaded";
});

document.querySelectorAll(".image-style-chip").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".image-style-chip").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    selectedImageStyle = button.dataset.style;
    styleStatus.textContent = `${button.textContent} style selected`;
  });
});

styleGenerateBtn?.addEventListener("click", generateStyleTransform);
voiceGenerateBtn?.addEventListener("click", generateVoiceover);
copilotGenerateBtn?.addEventListener("click", generateCopilotPlan);

document.querySelectorAll(".copilot-mode-chip").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".copilot-mode-chip").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    selectedCopilotMode = button.dataset.mode;
    copilotStatus.textContent = `${button.textContent} selected`;
  });
});

mainVideoInput.addEventListener("change", () => {
  const file = mainVideoInput.files?.[0];
  mainVideoName.textContent = file ? file.name : "No video selected";
  if (file) {
    referenceStatus.textContent = "Your video loaded";
  }
});

referenceVideoInput.addEventListener("change", () => {
  const file = referenceVideoInput.files?.[0];
  referenceVideoName.textContent = file ? file.name : "No reference selected";
  if (file) {
    referenceStatus.textContent = "Reference video loaded";
  }
});

referenceGenerateBtn.addEventListener("click", generateReferenceEdit);
aiTestBtn?.addEventListener("click", testAiBrain);
analyzePromptBtn?.addEventListener("click", analyzePromptInEditor);

window.addEventListener("popstate", () => {
  showPage(pageRoutes[location.pathname] || "dashboard", { push: false, instant: true });
});

resetNewProject({ scrollToEditor: false, navigateToEditor: false });
showPage(pageRoutes[location.pathname] || "dashboard", { push: false, instant: true });
checkBackendHealth();
refreshAiSettings();
refreshFreeEngines();
