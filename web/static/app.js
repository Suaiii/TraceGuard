const state = {
  file: null,
  result: null,
  activeView: "overlay",
  mode: "single",
  files: [],
  batchResults: null,
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
  superOversightBanner: document.getElementById("superOversightBanner"),
  reviewSuggestion: document.getElementById("reviewSuggestion"),
  reviewText: document.getElementById("reviewText"),
  dimensionViz: document.getElementById("dimensionViz"),
  dimBars: document.getElementById("dimBars"),
  soFakeProbVal: document.getElementById("soFakeProbVal"),
  soRiskScoreVal: document.getElementById("soRiskScoreVal"),
  soTotalScore: document.getElementById("soTotalScore"),
  clearFilesButton: document.getElementById("clearFilesButton"),
  exportSingleButton: document.getElementById("exportSingleButton"),
  exportBatchButton: document.getElementById("exportBatchButton"),
  previewModal: document.getElementById("previewModal"),
  previewOverlay: document.getElementById("previewOverlay"),
  previewFrame: document.getElementById("previewFrame"),
  previewClose: document.getElementById("previewClose"),
  previewCancel: document.getElementById("previewCancel"),
  previewDownload: document.getElementById("previewDownload"),
  previewLoading: document.getElementById("previewLoading"),
  previewStatus: document.getElementById("previewStatus"),
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
  collapsed: "\u68c0\u6d4b\u540e\u663e\u793a\u8bc1\u636e\u56fe",
  noLocalization: "\u52fe\u9009\u300c\u53ef\u7591\u533a\u57df\u5b9a\u4f4d\u300d\u540e\u663e\u793a",
  batchConvert: "\u6b63\u5728\u8f6c\u6362\u56fe\u7247...",
  batchAnalyzing: "\u6b63\u5728\u6279\u91cf\u68c0\u6d4b...",
  batchAnalyze: "\u5f00\u59cb\u6279\u91cf\u68c0\u6d4b",
  batchEmpty: "\u4e0a\u4f20\u56fe\u7247\u5e76\u5f00\u59cb\u68c0\u6d4b\u540e\u663e\u793a\u7ed3\u679c",
  batchFailed: "\u6279\u91cf\u5206\u6790\u5931\u8d25",
  expandLabel: "\u5c55\u5f00 \u25bc",
  collapseLabel: "\u6536\u8d77 \u25b2",
  soVerdictLabel: "\u9ad8\u7f6e\u4fe1\u4f2a\u9020",
  soReviewText: "\u8be5\u56fe\u50cf\u5728\u4f2a\u9020\u6982\u7387\u548c\u7efc\u5408\u98ce\u9669\u4e24\u4e2a\u7ef4\u5ea6\u5747\u8fbe\u5230\u6700\u9ad8\u8b66\u6212\u7ea7\u522b\u3002\u5efa\u8bae\uff1a(1) \u5bf9\u7167\u539f\u59cb\u6765\u6e90\u6838\u5b9e\u56fe\u50cf\u771f\u5b9e\u6027\uff1b(2) \u68c0\u67e5\u5143\u6570\u636e\u4e2d\u7684\u7f16\u8f91\u75d5\u8ff9\uff1b(3) \u4ea4\u53c9\u9a8c\u8bc1\u4f20\u64ad\u94fe\u8def\u4e2d\u5176\u4ed6\u526f\u672c\u7684\u68c0\u6d4b\u7ed3\u679c\u3002\u5982\u786e\u8ba4\u4e3a AIGC \u4f2a\u9020\uff0c\u5e94\u7acb\u5373\u6807\u8bb0\u5e76\u9650\u5236\u4f20\u64ad\u3002",
  soCardReview: "\u9ad8\u7f6e\u4fe1\u4f2a\u9020\uff1a\u4f2a\u9020\u6982\u7387\u226590%\u4e14\u7efc\u5408\u98ce\u9669\u4e3a\u9ad8\uff0c\u5efa\u8bae\u52a0\u6025\u4eba\u5de5\u590d\u6838\u3002",
  dimLabels: {
    artifact_intensity: "\u4f2a\u9020\u75d5\u8ff9\u5f3a\u5ea6",
    tamper_area: "\u7be1\u6539\u533a\u57df\u5360\u6bd4",
    region_count: "\u53ef\u7591\u533a\u57df\u6570\u91cf",
    consistency: "\u7279\u5f81\u4e00\u81f4\u6027",
  },
  clearFiles: "\u6e05\u7a7a\u6240\u6709\u56fe\u7247",
  exportGenerating: "\u6b63\u5728\u751f\u6210\u62a5\u544a...",
  exportSingle: "\u5bfc\u51fa\u62a5\u544a",
  exportBatch: "\u6279\u91cf\u5bfc\u51fa\u62a5\u544a",
};

function setStatus(kind, message) {
  el.serviceStatus.className = `status ${kind}`;
  el.serviceStatus.querySelector("span:last-child").textContent = message;
}

function asPercent(value) {
  return `${Math.round(Number(value || 0) * 100)}%`;
}

var prefersReducedMotion =
  window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// Restart a one-shot CSS animation bound to className (remove -> reflow -> add)
function replayAnimation(elem, className) {
  elem.classList.remove(className);
  void elem.offsetWidth;
  elem.classList.add(className);
}

// Count a 0..1 ratio up to its target over ~400ms, rendered via asPercent
function animateCount(elem, target) {
  if (prefersReducedMotion) {
    elem.textContent = asPercent(target);
    return;
  }
  var startTime = null;
  function step(now) {
    if (startTime === null) startTime = now;
    var p = Math.min((now - startTime) / 400, 1);
    var eased = 1 - Math.pow(1 - p, 3);
    elem.textContent = asPercent(target * eased);
    if (p < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
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

// 判据：高置信伪造 + 高综合风险 → 加急人工复核。
//
// 注意（措辞红线，勿改回）：本系统只判断"是否 AIGC 生成"，管线输出中没有任何
// 内容类别字段，因此**不能**据此声称检测到"超监管内容"（战争/恐怖主义/枪械等
// 语义类别）——那需要内容分类器，本作品没有，报告 1.4 合规声明也明确只做检测器
// 评测。CSS 类名与 id 仍沿用 super-oversight/so- 前缀是为了不动样式表，仅为历史
// 命名，不代表系统具备超监管内容识别能力。
function isHighConfidenceFake(data) {
  return data.label === "fake" && Number(data.fake_prob || 0) >= 0.9 && data.risk_level === "high";
}

function dimBarColor(value) {
  if (value >= 0.8) return "var(--red)";
  if (value >= 0.5) return "var(--amber)";
  return "var(--green)";
}

function renderDimensionBars(scores, container, compact) {
  container.innerHTML = "";
  var dims = [
    { key: "artifact_intensity", label: text.dimLabels.artifact_intensity },
    { key: "tamper_area",       label: text.dimLabels.tamper_area },
    { key: "region_count",      label: text.dimLabels.region_count },
    { key: "consistency",       label: text.dimLabels.consistency },
  ];

  var fills = [];
  dims.forEach(function (dim) {
    var value = Math.min(Math.max(Number(scores[dim.key] || 0), 0), 1);
    var pct = asPercent(value);

    var row = document.createElement("div");
    row.className = compact ? "card-dim-bar" : "dim-bar";

    var label = document.createElement("span");
    label.className = compact ? "dim-label" : "dim-bar-label";
    label.textContent = dim.label;

    var track = document.createElement("span");
    track.className = "dim-bar-track";

    var fill = document.createElement("span");
    fill.className = "dim-bar-fill";
    // start at 0 so the width transition plays once mounted
    fill.style.width = prefersReducedMotion ? pct : "0";
    fill.style.background = dimBarColor(value);
    fills.push([fill, pct]);

    track.appendChild(fill);

    var val = document.createElement("span");
    val.className = compact ? "dim-val" : "dim-bar-value";
    val.textContent = pct;

    row.appendChild(label);
    row.appendChild(track);
    row.appendChild(val);
    container.appendChild(row);
  });

  if (!prefersReducedMotion) {
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        fills.forEach(function (pair) { pair[0].style.width = pair[1]; });
      });
    });
  }
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
  el.analyzeButton.classList.add("loading");
  el.analyzeButton.textContent = text.analyzing;
  el.exportSingleButton.style.display = "none";

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
    el.analyzeButton.classList.remove("loading");
    el.analyzeButton.textContent = text.analyze;
  }
}

function renderResult(data) {
  const label = data.label || "error";
  const fakeProb = Number(data.fake_prob || 0);
  const riskScore = Number(data.risk_score || 0);
  const bboxCount = Array.isArray(data.bbox_list) ? data.bbox_list.length : 0;

  el.verdictBlock.className = `verdict ${label}`;
  replayAnimation(el.verdictBlock, "updated");
  el.labelText.textContent = text.label[label] || label;
  animateCount(el.probText, fakeProb);
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

  if (isHighConfidenceFake(data)) {
    el.superOversightBanner.style.display = "";
    el.reviewSuggestion.style.display = "";
    el.reviewText.textContent = text.soReviewText;
    el.dimensionViz.style.display = "";
    renderDimensionBars(data.dimension_scores || {}, el.dimBars, false);
    el.verdictBlock.classList.add("super-oversight-active");
    el.labelText.textContent = text.soVerdictLabel;
    el.soFakeProbVal.textContent = asPercent(fakeProb);
    el.soRiskScoreVal.textContent = asPercent(riskScore);
    el.soTotalScore.textContent = asPercent(riskScore);
  } else {
    el.superOversightBanner.style.display = "none";
    el.reviewSuggestion.style.display = "none";
    el.dimensionViz.style.display = "none";
    el.verdictBlock.classList.remove("super-oversight-active");
    el.labelText.textContent = text.label[label] || label;
  }

  el.exportSingleButton.style.display = "block";

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
    replayAnimation(el.evidenceImage, "swap");
    el.emptyEvidence.classList.add("hidden");
  } else {
    el.evidenceImage.removeAttribute("src");
    el.emptyEvidence.classList.remove("hidden");
    var locViews = ["bbox", "tamper"];
    var locEnabled = state.result && state.result.metadata && state.result.metadata.localization_enabled;
    if (locViews.indexOf(state.activeView) !== -1 && locEnabled === false) {
      el.emptyEvidence.textContent = text.noLocalization;
    } else {
      el.emptyEvidence.textContent = text.collapsed;
    }
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
  renderFileList();
}

function removeFile(index) {
  state.files.splice(index, 1);
  state.batchResults = null;
  renderFileList();
}

function clearFiles() {
  state.files = [];
  state.batchResults = null;
  el.exportBatchButton.style.display = "none";
  renderFileList();
}

function renderFileList() {
  el.fileGrid.innerHTML = "";
  el.multiFileCount.textContent = state.files.length + " / 20";
  el.batchAnalyzeButton.disabled = state.files.length === 0;
  el.clearFilesButton.style.display = state.files.length > 0 ? "" : "none";
  el.batchEmptyState.style.display = "";
  el.batchStats.style.display = "none";
  var cards = el.resultGrid.querySelectorAll(".result-card");
  for (var c = 0; c < cards.length; c++) { cards[c].remove(); }

  state.files.forEach(function (file, index) {
    var card = document.createElement("div");
    card.className = "file-card";
    card.style.setProperty("--i", String(index));

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
  el.batchAnalyzeButton.classList.add("loading");
  el.batchAnalyzeButton.textContent = text.batchConvert;
  el.exportBatchButton.style.display = "none";
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
    el.batchAnalyzeButton.classList.remove("loading");
    el.batchAnalyzeButton.textContent = text.batchAnalyze;
  }
}

function renderBatchResults(data) {
  el.batchEmptyState.style.display = "none";
  el.batchStats.style.display = "flex";
  var oldCards = el.resultGrid.querySelectorAll(".result-card");
  for (var c = 0; c < oldCards.length; c++) { oldCards[c].remove(); }
  el.batchSuccessCount.textContent = String(data.success_count);
  el.batchErrorCount.textContent = String(data.error_count);
  el.batchTotalTime.textContent = String(Math.round(data.total_elapsed_ms));
  el.batchLatencyText.textContent = Math.round(data.total_elapsed_ms) + " ms";

  var grid = el.resultGrid;
  data.results.forEach(function (result, index) {
    var card = createResultCard(result, index);
    grid.appendChild(card);
  });

  el.exportBatchButton.style.display = "block";
}

function createResultCard(result, index) {
  var card = document.createElement("article");
  var label = result.label || "error";
  card.className = "result-card " + label;
  var isSO = isHighConfidenceFake(result);
  if (isSO) card.classList.add("super-oversight");
  card.dataset.index = String(index);
  card.style.setProperty("--i", String(index));

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
  if (isSO) {
    var soBadge = document.createElement("span");
    soBadge.className = "so-badge";
    soBadge.textContent = "高置信伪造";
    meta.appendChild(soBadge);
  }
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
  toggle.textContent = text.expandLabel;
  toggle.addEventListener("click", (function (idx) {
    return function () { expandCard(idx); };
  })(index));

  // Detail
  var detail = document.createElement("div");
  detail.className = "card-detail";
  detail.style.display = "none";

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
  if (isSO) {
    var cardDimBars = document.createElement("div");
    cardDimBars.className = "card-dim-bars";
    renderDimensionBars(result.dimension_scores || {}, cardDimBars, true);
    detail.appendChild(cardDimBars);

    var cardReview = document.createElement("p");
    cardReview.className = "card-review";
    cardReview.textContent = text.soCardReview;
    detail.appendChild(cardReview);
  }
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
    replayAnimation(img, "swap");
  }
}

function expandCard(index) {
  var card = el.resultGrid.querySelector('[data-index="' + index + '"]');
  if (!card) return;

  var detail = card.querySelector(".card-detail");
  var toggle = card.querySelector(".card-toggle");
  if (!detail || !toggle) return;

  var isOpen = detail.style.display !== "none";
  if (isOpen) {
    detail.style.display = "none";
    toggle.textContent = text.expandLabel;
  } else {
    detail.style.display = "";
    toggle.textContent = text.collapseLabel;
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

  // --- Report export ---
  function buildReportRequest(type) {
    if (type === "single") {
      const data = state.result;
      if (!data) return null;
      // Convert state.result to a plain object matching AnalysisResponse schema
      return {
        type: "single",
        results: [data],
        options: { include_llm: true },
      };
    } else {
      const data = state.batchResults;
      if (!data || !data.results) return null;
      return {
        type: "batch",
        results: data.results,
        options: { include_llm: true },
      };
    }
  }

  function openPreview(html) {
    el.previewModal.style.display = "flex";
    el.previewLoading.style.display = "flex";
    el.previewFrame.style.display = "none";
    el.previewDownload.disabled = false;
    el.previewStatus.textContent = "";

    const blob = new Blob([html], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    el.previewFrame.dataset.blobUrl = url;

    el.previewFrame.onload = function () {
      el.previewLoading.style.display = "none";
      el.previewFrame.style.display = "block";
      // Auto-resize iframe to content height (消除内层滚动条)
      try {
        var body = el.previewFrame.contentDocument.body;
        var html = el.previewFrame.contentDocument.documentElement;
        var h = Math.max(
          body.scrollHeight, body.offsetHeight,
          html.clientHeight, html.scrollHeight, html.offsetHeight
        );
        el.previewFrame.style.height = (h + 40) + "px";
      } catch (e) {
        el.previewFrame.style.height = "2000px";
      }
    };
    el.previewFrame.src = url;
  }

  function closePreview() {
    el.previewModal.style.display = "none";
    const url = el.previewFrame.dataset.blobUrl;
    if (url) {
      URL.revokeObjectURL(url);
      el.previewFrame.dataset.blobUrl = "";
    }
    el.previewFrame.src = "";
    el.previewFrame.style.display = "none";
    el.previewLoading.style.display = "flex";
    el.previewStatus.textContent = "";
  }

  async function previewReport(type) {
    const req = buildReportRequest(type);
    if (!req) {
      alert("没有可导出的检测结果");
      return;
    }
    const btn = type === "single" ? el.exportSingleButton : el.exportBatchButton;
    const originalText = btn.textContent;
    btn.textContent = text.exportGenerating;
    btn.disabled = true;
    // 先显示弹窗 + loading
    el.previewModal.style.display = "flex";
    el.previewLoading.style.display = "flex";
    el.previewFrame.style.display = "none";
    el.previewDownload.disabled = true;
    el.previewStatus.textContent = "";
    try {
      const resp = await fetch("/api/v1/report/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(req),
      });
      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || err.message || resp.statusText);
      }
      const data = await resp.json();
      cachedReportHtml = data.html;
      cachedReportType = type;
      openPreview(data.html);
    } catch (err) {
      alert("报告生成失败：" + err.message);
    } finally {
      btn.textContent = originalText;
      btn.disabled = false;
    }
  }

  var cachedReportHtml = "";
  var cachedReportType = "";

  async function downloadReport() {
    if (!cachedReportHtml) {
      alert("请先预览报告再下载");
      return;
    }
    var btn = el.previewDownload;
    btn.disabled = true;
    btn.textContent = "正在生成 PDF...";
    el.previewStatus.textContent = "";
    // 生成唯一文件名: TraceGuard-{single|batch}-{YYYYMMDD-HHmmss}.pdf
    var now = new Date();
    var ts = now.getFullYear()
      + String(now.getMonth() + 1).padStart(2, "0")
      + String(now.getDate()).padStart(2, "0")
      + "-"
      + String(now.getHours()).padStart(2, "0")
      + String(now.getMinutes()).padStart(2, "0")
      + String(now.getSeconds()).padStart(2, "0");
    var filename = "TraceGuard-" + (cachedReportType || "report") + "-" + ts + ".pdf";
    try {
      const resp = await fetch("/api/v1/report/pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ html: cachedReportHtml, type: cachedReportType }),
      });
      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || err.message || resp.statusText);
      }
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      el.previewStatus.textContent = "PDF 已下载";
    } catch (err) {
      el.previewStatus.textContent = "下载失败";
      alert("PDF 下载失败：" + err.message);
    } finally {
      btn.disabled = false;
      btn.textContent = "下载 PDF";
    }
  }

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

  // --- Clear files button ---
  el.clearFilesButton.addEventListener("click", clearFiles);

  // --- Export buttons ---
  el.exportSingleButton.addEventListener("click", function () {
    previewReport("single");
  });
  el.exportBatchButton.addEventListener("click", function () {
    previewReport("batch");
  });

  // --- Preview modal ---
  el.previewClose.addEventListener("click", closePreview);
  el.previewCancel.addEventListener("click", closePreview);
  el.previewOverlay.addEventListener("click", closePreview);

  el.previewDownload.addEventListener("click", downloadReport);

  // ESC to close modal
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && el.previewModal.style.display === "flex") {
      closePreview();
    }
  });
}

bindEvents();
loadHealth();
