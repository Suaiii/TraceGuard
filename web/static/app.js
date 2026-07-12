const state = {
  file: null,
  result: null,
  activeView: "overlay",
};

const el = {
  serviceStatus: document.getElementById("serviceStatus"),
  fileInput: document.getElementById("fileInput"),
  dropzone: document.getElementById("dropzone"),
  previewImage: document.getElementById("previewImage"),
  previewCaption: document.getElementById("previewCaption"),
  analyzeButton: document.getElementById("analyzeButton"),
  sampleButton: document.getElementById("sampleButton"),
  localizationToggle: document.getElementById("localizationToggle"),
  alphaRange: document.getElementById("alphaRange"),
  verdictBlock: document.getElementById("verdictBlock"),
  labelText: document.getElementById("labelText"),
  probText: document.getElementById("probText"),
  fakeProbText: document.getElementById("fakeProbText"),
  fakeProbBar: document.getElementById("fakeProbBar"),
  riskText: document.getElementById("riskText"),
  riskBar: document.getElementById("riskBar"),
  bboxCount: document.getElementById("bboxCount"),
  riskLevel: document.getElementById("riskLevel"),
  methodText: document.getElementById("methodText"),
  briefText: document.getElementById("briefText"),
  latencyText: document.getElementById("latencyText"),
  evidenceImage: document.getElementById("evidenceImage"),
  emptyEvidence: document.getElementById("emptyEvidence"),
  detailText: document.getElementById("detailText"),
};

const text = {
  label: {
    fake: "AIGC \u4f2a\u9020",
    real: "\u771f\u5b9e\u56fe\u50cf",
    local_tamper: "\u5c40\u90e8\u7be1\u6539",
    error: "\u5206\u6790\u5931\u8d25",
  },
  apiOffline: "API \u672a\u5c31\u7eea",
  analyzing: "\u5ba1\u8ba1\u4e2d...",
  analyze: "\u5f00\u59cb\u5ba1\u8ba1",
  noBrief: "\u65e0\u6458\u8981",
  noDetail: "\u65e0\u8be6\u7ec6\u89e3\u91ca",
  failed: "\u5206\u6790\u5931\u8d25",
  localSample: "\u8bf7\u9009\u62e9 tests/fixtures \u4e2d\u7684\u6837\u4f8b\u56fe\u50cf\u8fdb\u884c\u5ba1\u8ba1",
};

function setStatus(kind, message) {
  el.serviceStatus.className = `status ${kind}`;
  el.serviceStatus.querySelector("span:last-child").textContent = message;
}

function asPercent(value) {
  return `${Math.round(Number(value || 0) * 100)}%`;
}

function imageSrc(b64) {
  return b64 ? `data:image/png;base64,${b64}` : "";
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const raw = String(reader.result || "");
      resolve(raw.includes(",") ? raw.split(",")[1] : raw);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function setFile(file) {
  if (!file || !file.type.startsWith("image/")) return;
  state.file = file;
  state.result = null;
  el.previewImage.src = URL.createObjectURL(file);
  el.previewCaption.textContent = `${file.name} - ${(file.size / 1024).toFixed(1)} KB`;
  el.analyzeButton.disabled = false;
  el.emptyEvidence.classList.remove("hidden");
  el.evidenceImage.removeAttribute("src");
}

async function loadHealth() {
  try {
    const res = await fetch("/api/v1/health");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    setStatus("ready", `${data.device} - ${data.model_params}`);
  } catch (error) {
    setStatus("error", text.apiOffline);
  }
}

async function analyze() {
  if (!state.file) return;
  el.analyzeButton.disabled = true;
  el.analyzeButton.textContent = text.analyzing;

  try {
    const image_base64 = await fileToBase64(state.file);
    const res = await fetch("/api/v1/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        image_base64,
        options: {
          overlay_alpha: Number(el.alphaRange.value),
          enable_localization: el.localizationToggle.checked,
          language: "zh",
          detail_level: "standard",
        },
      }),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || `HTTP ${res.status}`);
    }
    state.result = data;
    renderResult(data);
  } catch (error) {
    state.result = null;
    el.detailText.textContent = `${text.failed}: ${error.message}`;
  } finally {
    el.analyzeButton.disabled = false;
    el.analyzeButton.textContent = text.analyze;
  }
}

function renderResult(data) {
  const label = data.label || "error";
  const fakeProb = Number(data.fake_prob || 0);
  const riskScore = Number(data.risk_score || 0);
  const bboxCount = Array.isArray(data.bbox_list) ? data.bbox_list.length : 0;

  el.verdictBlock.className = `verdict ${label}`;
  el.labelText.textContent = text.label[label] || label;
  el.probText.textContent = asPercent(fakeProb);
  el.fakeProbText.textContent = asPercent(fakeProb);
  el.fakeProbBar.style.width = asPercent(fakeProb);
  el.riskText.textContent = `${asPercent(riskScore)} - ${data.risk_level}`;
  el.riskBar.style.width = asPercent(riskScore);
  el.bboxCount.textContent = String(bboxCount);
  el.riskLevel.textContent = data.risk_level || "--";
  el.methodText.textContent = data.metadata?.heatmap_method || "gradcam";
  el.briefText.textContent = data.explanation_brief || text.noBrief;
  el.latencyText.textContent = `${Math.round(data.elapsed_ms || 0)} ms`;
  el.detailText.textContent = data.explanation || text.noDetail;

  renderEvidence();
}

function renderEvidence() {
  if (!state.result) return;
  const keyMap = {
    overlay: "overlay_b64",
    mask: "mask_b64",
    bbox: "bbox_image_b64",
    tamper: "tamper_overlay_b64",
  };
  const b64 = state.result[keyMap[state.activeView]];
  if (b64) {
    el.evidenceImage.src = imageSrc(b64);
    el.emptyEvidence.classList.add("hidden");
  } else {
    el.evidenceImage.removeAttribute("src");
    el.emptyEvidence.classList.remove("hidden");
  }
}

function bindEvents() {
  el.fileInput.addEventListener("change", (event) => {
    setFile(event.target.files?.[0]);
  });

  ["dragenter", "dragover"].forEach((type) => {
    el.dropzone.addEventListener(type, (event) => {
      event.preventDefault();
      el.dropzone.classList.add("dragging");
    });
  });

  ["dragleave", "drop"].forEach((type) => {
    el.dropzone.addEventListener(type, (event) => {
      event.preventDefault();
      el.dropzone.classList.remove("dragging");
    });
  });

  el.dropzone.addEventListener("drop", (event) => {
    setFile(event.dataTransfer?.files?.[0]);
  });

  el.analyzeButton.addEventListener("click", analyze);

  el.sampleButton.addEventListener("click", () => {
    el.previewCaption.textContent = text.localSample;
  });

  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((item) => item.classList.remove("active"));
      tab.classList.add("active");
      state.activeView = tab.dataset.view;
      renderEvidence();
    });
  });
}

bindEvents();
loadHealth();
