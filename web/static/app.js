const state = {
  file: null,
  result: null,
  activeView: "overlay",
  mode: "single",
  files: [],
  batchResults: null,
  expandedCard: null,
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
  tamperType: document.getElementById("tamperType"),
  briefText: document.getElementById("briefText"),
  latencyText: document.getElementById("latencyText"),
  evidenceImage: document.getElementById("evidenceImage"),
  emptyEvidence: document.getElementById("emptyEvidence"),
  detailText: document.getElementById("detailText"),
  modeBar: document.getElementById("modeBar"),
  singleWorkspace: document.getElementById("singleWorkspace"),
  multiWorkspace: document.getElementById("multiWorkspace"),
  multiDropzone: document.getElementById("multiDropzone"),
  multiFileInput: document.getElementById("multiFileInput"),
  fileGrid: document.getElementById("fileGrid"),
  multiFileCount: document.getElementById("multiFileCount"),
  batchAnalyzeButton: document.getElementById("batchAnalyzeButton"),
  multiLocalizationToggle: document.getElementById("multiLocalizationToggle"),
  multiAlphaRange: document.getElementById("multiAlphaRange"),
  resultGrid: document.getElementById("resultGrid"),
  batchStats: document.getElementById("batchStats"),
  batchEmptyState: document.getElementById("batchEmptyState"),
  batchSuccessCount: document.getElementById("batchSuccessCount"),
  batchErrorCount: document.getElementById("batchErrorCount"),
  batchTotalTime: document.getElementById("batchTotalTime"),
  batchLatencyText: document.getElementById("batchLatencyText"),
};

const text = {
  label: {
    fake: "AIGC \u4f2a\u9020",
    real: "\u771f\u5b9e\u56fe\u50cf",
    local_tamper: "\u5c40\u90e8\u7be1\u6539",
    error: "\u5206\u6790\u5931\u8d25",
  },
  tamperType: {
    confirmed_real: "未发现局部异常",
    local_tamper: "局部篡改证据",
    full_aigc: "全图 AIGC 证据",
    full_aigc_hotspots: "全图 AIGC 证据（含热点）",
    unavailable: "不可用",
  },
  apiOffline: "API \u672a\u5c31\u7eea",
  analyzing: "\u68c0\u6d4b\u4e2d...",
  analyze: "\u5f00\u59cb\u68c0\u6d4b",
  noBrief: "\u65e0\u6458\u8981",
  noDetail: "\u65e0\u8be6\u7ec6\u89e3\u91ca",
  failed: "\u5206\u6790\u5931\u8d25",
  localSample: "\u8bf7\u9009\u62e9 tests/fixtures \u4e2d\u7684\u6837\u4f8b\u56fe\u50cf\u8fdb\u884c\u68c0\u6d4b",
  batchConvert: "\u6b63\u5728\u8f6c\u6362\u56fe\u7247...",
  batchAnalyzing: "\u6b63\u5728\u6279\u91cf\u68c0\u6d4b...",
  batchAnalyze: "\u5f00\u59cb\u6279\u91cf\u68c0\u6d4b",
  batchEmpty: "\u4e0a\u4f20\u56fe\u7247\u5e76\u5f00\u59cb\u68c0\u6d4b\u540e\u663e\u793a\u7ed3\u679c",
  batchFailed: "\u6279\u91cf\u5206\u6790\u5931\u8d25",
  expandLabel: "\u5c55\u5f00 \u25bc",
  collapseLabel: "\u6536\u8d77 \u25b2",
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
  el.tamperType.textContent = text.tamperType[data.tamper_type] || data.tamper_type || "--";
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

function switchMode(mode) {
  if (state.mode === mode) return;
  state.mode = mode;

  el.modeBar.querySelectorAll(".mode-tab").forEach(function (tab) {
    tab.classList.toggle("active", tab.dataset.mode === mode);
  });

  el.singleWorkspace.style.display = mode === "single" ? "" : "none";
  el.multiWorkspace.style.display = mode === "multi" ? "" : "none";
}

function addFiles(incomingFileList) {
  var incoming = Array.from(incomingFileList).filter(function (f) {
    return f.type.startsWith("image/");
  });

  for (var i = 0; i < incoming.length; i++) {
    var file = incoming[i];
    var isDuplicate = state.files.some(function (f) {
      return f.name === file.name && f.size === file.size;
    });
    if (!isDuplicate && state.files.length < 20) {
      state.files.push(file);
    }
  }

  state.batchResults = null;
  state.expandedCard = null;
  renderFileList();
}

function removeFile(index) {
  state.files.splice(index, 1);
  state.batchResults = null;
  state.expandedCard = null;
  renderFileList();
}

function renderFileList() {
  el.fileGrid.innerHTML = "";
  el.multiFileCount.textContent = state.files.length + " / 20";
  el.batchAnalyzeButton.disabled = state.files.length === 0;
  el.batchEmptyState.style.display = "";
  el.batchStats.style.display = "none";
  var cards = el.resultGrid.querySelectorAll(".result-card");
  for (var c = 0; c < cards.length; c++) { cards[c].remove(); }

  state.files.forEach(function (file, index) {
    var card = document.createElement("div");
    card.className = "file-card";

    var img = document.createElement("img");
    img.src = URL.createObjectURL(file);
    img.alt = file.name;

    var nameSpan = document.createElement("span");
    nameSpan.className = "file-name";
    nameSpan.textContent = file.name;

    var sizeSpan = document.createElement("span");
    sizeSpan.className = "file-size";
    sizeSpan.textContent = (file.size / 1024).toFixed(1) + " KB";

    var removeBtn = document.createElement("button");
    removeBtn.className = "file-remove";
    removeBtn.type = "button";
    removeBtn.textContent = "×";
    removeBtn.addEventListener("click", (function (idx) {
      return function (e) { e.stopPropagation(); removeFile(idx); };
    })(index));

    card.appendChild(img);
    card.appendChild(nameSpan);
    card.appendChild(sizeSpan);
    card.appendChild(removeBtn);
    el.fileGrid.appendChild(card);
  });
}

async function submitBatch() {
  if (state.files.length === 0) return;

  el.batchAnalyzeButton.disabled = true;
  el.batchAnalyzeButton.textContent = text.batchConvert;
  el.batchEmptyState.textContent = "正在分析中...";
  el.batchEmptyState.style.display = "";
  el.batchStats.style.display = "none";
  var oldCards = el.resultGrid.querySelectorAll(".result-card");
  for (var c = 0; c < oldCards.length; c++) { oldCards[c].remove(); }

  try {
    var imagesBase64 = await Promise.all(
      state.files.map(function (f) { return fileToBase64(f); })
    );

    el.batchAnalyzeButton.textContent = text.batchAnalyzing;

    var res = await fetch("/api/v1/analyze/batch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        images_base64: imagesBase64,
        options: {
          overlay_alpha: Number(el.multiAlphaRange.value),
          enable_localization: el.multiLocalizationToggle.checked,
          language: "zh",
          detail_level: "standard",
        },
      }),
    });

    var data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "HTTP " + res.status);
    }

    state.batchResults = data;
    renderBatchResults(data);
  } catch (error) {
    el.batchEmptyState.textContent = text.batchFailed + ": " + error.message;
    el.batchEmptyState.style.display = "";
    el.batchStats.style.display = "none";
  } finally {
    el.batchAnalyzeButton.disabled = false;
    el.batchAnalyzeButton.textContent = text.batchAnalyze;
  }
}

function renderBatchResults(data) {
  el.batchEmptyState.style.display = "none";
  el.batchStats.style.display = "flex";
  el.batchSuccessCount.textContent = String(data.success_count);
  el.batchErrorCount.textContent = String(data.error_count);
  el.batchTotalTime.textContent = String(Math.round(data.total_elapsed_ms));
  el.batchLatencyText.textContent = Math.round(data.total_elapsed_ms) + " ms";

  var grid = el.resultGrid;
  data.results.forEach(function (result, index) {
    var card = createResultCard(result, index);
    grid.appendChild(card);
  });
}

function createResultCard(result, index) {
  var card = document.createElement("article");
  var label = result.label || "error";
  card.className = "result-card " + label;
  card.dataset.index = String(index);

  var file = state.files[index];
  var fileName = file ? file.name : ("图片 " + (index + 1));
  var thumbSrc = file ? URL.createObjectURL(file) : "";

  // Head
  var head = document.createElement("div");
  head.className = "card-head";

  var thumb = document.createElement("img");
  thumb.className = "card-thumb";
  thumb.src = thumbSrc;
  thumb.alt = "";

  var meta = document.createElement("div");
  meta.className = "card-meta";

  var nameEl = document.createElement("span");
  nameEl.className = "card-name";
  nameEl.textContent = fileName;

  var verdict = document.createElement("span");
  verdict.className = "card-verdict";
  verdict.textContent = text.label[label] || label;

  meta.appendChild(nameEl);
  meta.appendChild(verdict);
  head.appendChild(thumb);
  head.appendChild(meta);

  // Body stats
  var body = document.createElement("div");
  body.className = "card-body";
  body.appendChild(makeStat("伪造概率", asPercent(result.fake_prob || 0)));

  var riskLevel = result.risk_level || "error";
  var riskHtml = "<span class=\"risk-" + riskLevel + "\">" + (riskLevel || "--") + "</span>";
  body.appendChild(makeStat("风险等级", riskHtml));

  body.appendChild(makeStat("耗时", Math.round(result.elapsed_ms || 0) + " ms"));

  // Toggle
  var toggle = document.createElement("button");
  toggle.className = "card-toggle";
  toggle.type = "button";
  var expanded = state.expandedCard === index;
  toggle.textContent = expanded ? text.collapseLabel : text.expandLabel;
  toggle.addEventListener("click", (function (idx) {
    return function () { expandCard(idx); };
  })(index));

  // Detail
  var detail = document.createElement("div");
  detail.className = "card-detail";
  detail.style.display = expanded ? "" : "none";

  var brief = document.createElement("p");
  brief.textContent = result.explanation_brief || text.noBrief;

  // Mini evidence viewer
  var evidenceB64 = {
    overlay: result.overlay_b64 || "",
    mask: result.mask_b64 || "",
    bbox: result.bbox_image_b64 || "",
    tamper: result.tamper_overlay_b64 || "",
  };

  var hasEvidence = evidenceB64.overlay || evidenceB64.mask || evidenceB64.bbox || evidenceB64.tamper;

  var miniEvidence = null;
  if (hasEvidence) {
    miniEvidence = document.createElement("div");
    miniEvidence.className = "mini-evidence";

    var miniTabs = document.createElement("div");
    miniTabs.className = "mini-tabs";

    var evidenceLabels = {
      overlay: "热力叠加",
      mask: "热力掩膜",
      bbox: "区域标注",
      tamper: "篡改掩膜",
    };

    var firstView = null;
    Object.keys(evidenceLabels).forEach(function (view) {
      if (evidenceB64[view]) {
        if (!firstView) firstView = view;
        var tabBtn = document.createElement("button");
        tabBtn.className = "mini-tab";
        tabBtn.type = "button";
        tabBtn.dataset.view = view;
        tabBtn.dataset.cardIndex = String(index);
        tabBtn.textContent = evidenceLabels[view];
        tabBtn.addEventListener("click", function (evt) {
          evt.stopPropagation();
          switchMiniEvidence(index, view);
        });
        miniTabs.appendChild(tabBtn);
      }
    });

    // Set first available tab as active
    if (firstView) {
      var firstTab = miniTabs.querySelector('[data-view="' + firstView + '"]');
      if (firstTab) firstTab.classList.add("active");
    }

    var miniView = document.createElement("div");
    miniView.className = "mini-evidence-view";
    miniView.dataset.cardIndex = String(index);

    // Set initial image
    var miniImg = document.createElement("img");
    miniImg.alt = "";
    if (firstView && evidenceB64[firstView]) {
      miniImg.src = imageSrc(evidenceB64[firstView]);
    }
    miniView.appendChild(miniImg);

    miniEvidence.appendChild(miniTabs);
    miniEvidence.appendChild(miniView);
  }

  var pre = document.createElement("pre");
  pre.textContent = result.explanation || text.noDetail;

  detail.appendChild(brief);
  if (miniEvidence) detail.appendChild(miniEvidence);
  detail.appendChild(pre);

  card.appendChild(head);
  card.appendChild(body);
  card.appendChild(toggle);
  card.appendChild(detail);

  return card;
}

function makeStat(label, valueHtml) {
  var div = document.createElement("div");
  div.className = "card-stat";
  var span = document.createElement("span");
  span.textContent = label;
  var b = document.createElement("b");
  b.innerHTML = valueHtml;
  div.appendChild(span);
  div.appendChild(b);
  return div;
}

function switchMiniEvidence(cardIndex, view) {
  var card = el.resultGrid.querySelector('[data-index="' + cardIndex + '"]');
  if (!card) return;

  // Update tab states
  card.querySelectorAll(".mini-tab").forEach(function (tab) {
    tab.classList.toggle("active", tab.dataset.view === view);
  });

  // Update image
  var miniView = card.querySelector(".mini-evidence-view");
  if (!miniView) return;

  var img = miniView.querySelector("img");
  if (!img) return;

  // Find result from batchResults
  var result = state.batchResults && state.batchResults.results && state.batchResults.results[cardIndex];
  if (!result) return;

  var keyMap = {
    overlay: "overlay_b64",
    mask: "mask_b64",
    bbox: "bbox_image_b64",
    tamper: "tamper_overlay_b64",
  };

  var b64 = result[keyMap[view]];
  if (b64) {
    img.src = imageSrc(b64);
  }
}

function expandCard(index) {
  var prev = state.expandedCard;
  state.expandedCard = state.expandedCard === index ? null : index;

  // Collapse previous
  if (prev !== null) {
    var prevCard = el.resultGrid.querySelector('[data-index="' + prev + '"]');
    if (prevCard) {
      var prevDetail = prevCard.querySelector(".card-detail");
      var prevToggle = prevCard.querySelector(".card-toggle");
      if (prevDetail) prevDetail.style.display = "none";
      if (prevToggle) prevToggle.textContent = text.expandLabel;
    }
  }

  // Expand new
  if (state.expandedCard !== null) {
    var curCard = el.resultGrid.querySelector('[data-index="' + state.expandedCard + '"]');
    if (curCard) {
      var curDetail = curCard.querySelector(".card-detail");
      var curToggle = curCard.querySelector(".card-toggle");
      if (curDetail) curDetail.style.display = "";
      if (curToggle) curToggle.textContent = text.collapseLabel;
    }
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

  // --- Mode toggle ---
  el.modeBar.querySelectorAll(".mode-tab").forEach(function (tab) {
    tab.addEventListener("click", function () {
      switchMode(tab.dataset.mode);
    });
  });

  // --- Multi-file input ---
  el.multiFileInput.addEventListener("change", function (event) {
    addFiles(event.target.files);
    event.target.value = "";
  });

  // --- Multi dropzone drag-and-drop ---
  ["dragenter", "dragover"].forEach(function (type) {
    el.multiDropzone.addEventListener(type, function (event) {
      event.preventDefault();
      el.multiDropzone.classList.add("dragging");
    });
  });

  ["dragleave", "drop"].forEach(function (type) {
    el.multiDropzone.addEventListener(type, function (event) {
      event.preventDefault();
      el.multiDropzone.classList.remove("dragging");
    });
  });

  el.multiDropzone.addEventListener("drop", function (event) {
    addFiles(event.dataTransfer.files);
  });

  // --- Batch analyze button ---
  el.batchAnalyzeButton.addEventListener("click", submitBatch);
}

bindEvents();
loadHealth();
