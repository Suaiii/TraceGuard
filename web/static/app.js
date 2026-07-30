// ---------- Screening constants ----------
var MAX_FILES = 1000;             // 前端总量护栏（后端单请求上限 50，见 CHUNK_SIZE）
var CHUNK_SIZE = 10;              // 每次 POST /analyze/batch 的图片数
var IMG_EXT_RE = /\.(png|jpe?g|webp)$/i;
var IMG_TYPE_RE = /^image\/(png|jpe?g|webp)$/i;

function newScreenState() {
  return {
    running: false,
    abortRequested: false,
    chunkSize: CHUNK_SIZE,
    total: 0,
    done: 0,
    passed: [],          // {idx, name, fake_prob}
    flagged: [],         // {idx, name, data}
    sortedFlagged: [],   // flagged 按严重度排序后的视图（卡片 dataset.index 指向它）
    errors: 0,
    startedAt: 0,
    elapsedMs: 0,
    finished: false,
    interrupted: false,
  };
}

const state = {
  file: null,
  result: null,
  activeView: "overlay",
  mode: "single",
  files: [],
  fileKeys: new Set(),
  screen: newScreenState(),
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
  folderButton: document.getElementById("folderButton"),
  folderInput: document.getElementById("folderInput"),
  fileGrid: document.getElementById("fileGrid"),
  multiFileCount: document.getElementById("multiFileCount"),
  batchAnalyzeButton: document.getElementById("batchAnalyzeButton"),
  multiLocalizationToggle: document.getElementById("multiLocalizationToggle"),
  multiAlphaRange: document.getElementById("multiAlphaRange"),
  resultGrid: document.getElementById("resultGrid"),
  batchStats: document.getElementById("batchStats"),
  batchEmptyState: document.getElementById("batchEmptyState"),
  batchTotalCount: document.getElementById("batchTotalCount"),
  batchPassedCount: document.getElementById("batchPassedCount"),
  batchFlaggedCount: document.getElementById("batchFlaggedCount"),
  batchHighConfCount: document.getElementById("batchHighConfCount"),
  batchErrorCount: document.getElementById("batchErrorCount"),
  batchBreakdown: document.getElementById("batchBreakdown"),
  batchInterrupted: document.getElementById("batchInterrupted"),
  batchLatencyText: document.getElementById("batchLatencyText"),
  screenProgress: document.getElementById("screenProgress"),
  progressText: document.getElementById("progressText"),
  progressMeta: document.getElementById("progressMeta"),
  progressFill: document.getElementById("progressFill"),
  abortButton: document.getElementById("abortButton"),
  superOversightBanner: document.getElementById("superOversightBanner"),
  highConfidenceBanner: document.getElementById("highConfidenceBanner"),
  reviewSuggestion: document.getElementById("reviewSuggestion"),
  reviewText: document.getElementById("reviewText"),
  dimensionViz: document.getElementById("dimensionViz"),
  dimBars: document.getElementById("dimBars"),
  batchSoCount: document.getElementById("batchSoCount"),
  soBannerTitle: document.getElementById("soBannerTitle"),
  soBannerText: document.getElementById("soBannerText"),
  soCategoryVal: document.getElementById("soCategoryVal"),
  soScoreVal: document.getElementById("soScoreVal"),
  hcBannerTitle: document.getElementById("hcBannerTitle"),
  hcBannerText: document.getElementById("hcBannerText"),
  hcFakeProbVal: document.getElementById("hcFakeProbVal"),
  hcRiskScoreVal: document.getElementById("hcRiskScoreVal"),
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
  capButton: document.getElementById("capButton"),
  capModal: document.getElementById("capModal"),
  capOverlay: document.getElementById("capOverlay"),
  capClose: document.getElementById("capClose"),
};

const text = {
  label: {
    fake: "AIGC 伪造",
    real: "真实图像",
    local_tamper: "局部篡改",
    error: "分析失败",
  },
  tamperType: {
    confirmed_real: "未发现局部异常",
    local_tamper: "局部篡改证据",
    full_aigc: "全图 AIGC 证据",
    full_aigc_hotspots: "全图 AIGC 证据（含热点）",
    unavailable: "不可用",
  },
  apiOffline: "API 未就绪",
  analyzing: "检测中...",
  analyze: "开始检测",
  noBrief: "无摘要",
  noDetail: "无详细解释",
  failed: "分析失败",
  localSample: "请选择 tests/fixtures 中的样例图像进行检测",
  collapsed: "检测后显示证据图",
  noLocalization: "勾选「可疑区域定位」后显示",
  batchConvert: "正在转换图片...",
  batchAnalyzing: "正在筛查...",
  batchAnalyze: "开始批量检测",
  batchEmpty: "上传图片或选择文件夹，开始取证筛查",
  batchAllPassed: "本批次全部筛选通过，无待处置条目",
  batchFailed: "批量分析失败",
  expandLabel: "展开 ▼",
  collapseLabel: "收起 ▲",
  soVerdictLabel: "高置信伪造",
  soReviewText: "该图像在伪造概率和综合风险两个维度均达到最高警戒级别。建议：(1) 对照原始来源核实图像真实性；(2) 检查元数据中的编辑痕迹；(3) 交叉验证传播链路中其他副本的检测结果。如确认为 AIGC 伪造，应立即标记并限制传播。",
  soCardReview: "高置信伪造：伪造概率≥90%且综合风险为高，建议加急人工复核。",
  // 如内容确属超监管领域（经分类器确认），请按平台超监管流程上报。
  soProcessTip: "如内容涉严重危害，请按平台超监管流程上报。",
  rankLabel: {
    0: "超监管高危",
    1: "高置信伪造",
    2: "AIGC 伪造",
    3: "局部篡改",
    4: "需复核",
    5: "失败",
  },
  dimLabels: {
    artifact_intensity: "伪造痕迹强度",
    tamper_area: "篡改区域占比",
    region_count: "可疑区域数量",
    consistency: "特征一致性",
  },
  clearFiles: "清空所有图片",
  exportGenerating: "正在生成报告...",
  exportSingle: "导出报告",
  exportBatch: "导出待处置报告",
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

function sleep(ms) {
  return new Promise(function (resolve) { setTimeout(resolve, ms); });
}

// 5s → "5s"；≥60s → "2:07"
function formatDuration(ms) {
  var totalSec = Math.max(0, Math.round(Number(ms || 0) / 1000));
  if (totalSec < 60) return totalSec + "s";
  var m = Math.floor(totalSec / 60);
  var s = totalSec % 60;
  return m + ":" + String(s).padStart(2, "0");
}

// 两条独立并行判定链：
//   - 高置信伪造：label=='fake' ∧ fake_prob≥0.9 ∧ risk_level=='high'
//   - 超监管领域：label=='fake' ∧ is_super_oversight_domain==true
// 两者互不嵌套，可同时触发。CSS 类名与 id 前缀沿用 super-oversight/so-。
function isHighConfidenceFake(data) {
  return data.label === "fake" && Number(data.fake_prob || 0) >= 0.9 && data.risk_level === "high";
}

// 超监管领域识别（独立于高置信判定，仅依赖 AIGC 伪造 + 内容分类器确认）
function isSuperOversightDomain(data) {
  return data.label === "fake" && data.is_super_oversight_domain === true;
}

function dimBarColor(value) {
  if (value >= 0.8) return "var(--red)";
  if (value >= 0.5) return "var(--amber)";
  return "var(--green)";
}

// 超监管类别名映射
var _SO_CAT_LABELS = {
  warfare: "战争冲突", terrorism: "恐怖主义", weapons: "武器枪械",
  gore_violence: "血腥暴力", disasters: "火灾/洪水/地震等灾难"
};
function _soCatLabel(cat) {
  return _SO_CAT_LABELS[cat] || cat;
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

// ---------- objectURL registries ----------
// 文件列表与结果卡各自一份，重渲染 / 结果重置时按需 revoke，避免千张图泄漏。
var fileUrlRegistry = [];
var resultUrlRegistry = [];
var singlePreviewUrl = "";

function trackURL(file, registry) {
  var url = URL.createObjectURL(file);
  registry.push(url);
  return url;
}

function revokeAll(registry) {
  for (var i = 0; i < registry.length; i++) {
    try { URL.revokeObjectURL(registry[i]); } catch (e) { /* noop */ }
  }
  registry.length = 0;
}

function setFile(file) {
  if (!isImageFile(file)) return;
  state.file = file;
  state.result = null;
  if (singlePreviewUrl) {
    try { URL.revokeObjectURL(singlePreviewUrl); } catch (e) { /* noop */ }
  }
  singlePreviewUrl = URL.createObjectURL(file);
  el.previewImage.src = singlePreviewUrl;
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

  var isSO = isSuperOversightDomain(data);
  var isHC = isHighConfidenceFake(data);

  // 超监管领域高危 banner（独立判定）
  if (isSO) {
    el.superOversightBanner.style.display = "";
    el.soBannerTitle.textContent = "超监管领域高危 · 建议立即复核";
    el.soBannerText.textContent = "内容分类器确认该 AIGC 图像属于超监管领域（战争/暴恐/枪械/暴力/灾难等），建议立即标记并上报平台超监管流程处置。";
    el.soCategoryVal.textContent = _soCatLabel(data.content_category) || data.content_category || "--";
    el.soScoreVal.textContent = asPercent(data.super_oversight_score || 0);
  } else {
    el.superOversightBanner.style.display = "none";
  }

  // 高置信伪造 banner（独立判定）
  if (isHC) {
    el.highConfidenceBanner.style.display = "";
    el.hcBannerTitle.textContent = "高置信伪造 · 建议加急复核";
    el.hcBannerText.textContent = "高置信伪造：伪造概率≥90%且综合风险为高，建议加急人工复核。如内容涉严重危害，请按平台超监管流程上报。";
    el.hcFakeProbVal.textContent = asPercent(fakeProb);
    el.hcRiskScoreVal.textContent = asPercent(riskScore);
  } else {
    el.highConfidenceBanner.style.display = "none";
  }

  if (isSO || isHC) {
    el.reviewSuggestion.style.display = "";
    el.reviewText.textContent = text.soReviewText;
    el.dimensionViz.style.display = "";
    renderDimensionBars(data.dimension_scores || {}, el.dimBars, false);
    el.verdictBlock.classList.add("super-oversight-active");
    el.labelText.textContent = isSO ? "超监管领域高危" : text.soVerdictLabel;
    el.soTotalScore.textContent = asPercent(riskScore);
  } else {
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

// ---------- A. 文件收集 ----------

// 文件夹读出的 File 常见 type === ""，必须允许按扩展名判定
function isImageFile(file) {
  if (!file) return false;
  if (IMG_TYPE_RE.test(file.type || "")) return true;
  return IMG_EXT_RE.test(file.name || "");
}

function fileKey(file) {
  return file.webkitRelativePath || file.__tgPath || (file.name + "|" + file.size);
}

var limitNoticeTimer = null;

function showLimitNotice(skipped) {
  var notice = document.getElementById("limitNotice");
  if (!notice) {
    notice = document.createElement("div");
    notice.className = "limit-notice";
    notice.id = "limitNotice";
    el.fileGrid.parentNode.insertBefore(notice, el.fileGrid);
  }
  notice.textContent = "已达 " + MAX_FILES + " 张上限，" + skipped + " 张未加入";
  notice.style.display = "";
  if (limitNoticeTimer) clearTimeout(limitNoticeTimer);
  limitNoticeTimer = setTimeout(function () {
    notice.style.display = "none";
  }, 6000);
}

function addFiles(incomingFileList) {
  if (state.screen.running) return;
  var incoming = Array.prototype.slice.call(incomingFileList || []).filter(isImageFile);

  var skipped = 0;
  for (var i = 0; i < incoming.length; i++) {
    var file = incoming[i];
    var key = fileKey(file);
    if (state.fileKeys.has(key)) continue;
    if (state.files.length >= MAX_FILES) {
      skipped = incoming.length - i;
      break;
    }
    state.fileKeys.add(key);
    state.files.push(file);
  }

  if (skipped > 0) showLimitNotice(skipped);

  resetScreening();
  renderFileList();
}

function removeFile(index) {
  if (state.screen.running) return;
  var file = state.files[index];
  if (file) state.fileKeys.delete(fileKey(file));
  state.files.splice(index, 1);
  resetScreening();
  renderFileList();
}

function clearFiles() {
  if (state.screen.running) return;
  state.files = [];
  state.fileKeys.clear();
  revokeAll(fileUrlRegistry);
  resetScreening();
  renderFileList();
}

function renderFileList() {
  // 重渲染前先回收上一轮缩略图 URL
  revokeAll(fileUrlRegistry);
  el.fileGrid.innerHTML = "";
  el.multiFileCount.textContent = state.files.length + " / " + MAX_FILES;
  el.batchAnalyzeButton.disabled = state.files.length === 0;
  el.clearFilesButton.style.display = state.files.length > 0 ? "" : "none";

  var THUMB_LIMIT = 24;
  var shown = Math.min(state.files.length, THUMB_LIMIT);

  for (var index = 0; index < shown; index++) {
    (function (file, idx) {
      var card = document.createElement("div");
      card.className = "file-card";
      card.style.setProperty("--i", String(idx));

      var img = document.createElement("img");
      img.src = trackURL(file, fileUrlRegistry);
      img.alt = file.name;

      var nameSpan = document.createElement("span");
      nameSpan.className = "file-name";
      nameSpan.textContent = file.webkitRelativePath || file.name;

      var sizeSpan = document.createElement("span");
      sizeSpan.className = "file-size";
      sizeSpan.textContent = (file.size / 1024).toFixed(1) + " KB";

      card.appendChild(img);
      card.appendChild(nameSpan);
      card.appendChild(sizeSpan);

      // >24 张时不提供逐张删除（只保留"清空"），避免大列表下标维护成本
      if (state.files.length <= THUMB_LIMIT) {
        var removeBtn = document.createElement("button");
        removeBtn.className = "file-remove";
        removeBtn.type = "button";
        removeBtn.textContent = "×";
        removeBtn.addEventListener("click", function (e) {
          e.stopPropagation();
          removeFile(idx);
        });
        card.appendChild(removeBtn);
      }

      el.fileGrid.appendChild(card);
    })(state.files[index], index);
  }

  if (state.files.length > THUMB_LIMIT) {
    var more = document.createElement("div");
    more.className = "file-card file-card-more";
    more.textContent = "等 " + (state.files.length - THUMB_LIMIT) + " 张 …";
    el.fileGrid.appendChild(more);
  }
}

// ---------- 拖拽文件夹（webkitGetAsEntry 递归） ----------

async function collectFromDataTransfer(dataTransfer) {
  if (!dataTransfer) return [];

  // DataTransferItem 在首个 await 之后即失效 —— entry 必须在此处同步取完
  var entries = [];
  var items = dataTransfer.items;
  if (items && items.length) {
    for (var i = 0; i < items.length; i++) {
      var item = items[i];
      var entry = null;
      if (typeof item.webkitGetAsEntry === "function") entry = item.webkitGetAsEntry();
      else if (typeof item.getAsEntry === "function") entry = item.getAsEntry();
      if (entry) entries.push(entry);
    }
  }

  // 老浏览器 / 无 entry 支持 → 降级
  if (!entries.length) return Array.prototype.slice.call(dataTransfer.files || []);

  var out = [];
  for (var k = 0; k < entries.length; k++) {
    await walkEntry(entries[k], out);
  }
  return out;
}

function walkEntry(entry, out) {
  return new Promise(function (resolve) {
    if (!entry || out.length >= MAX_FILES) return resolve();

    if (entry.isFile) {
      entry.file(function (f) {
        try { f.__tgPath = entry.fullPath; } catch (e) { /* noop */ }
        out.push(f);
        resolve();
      }, function () { resolve(); });
      return;
    }

    if (entry.isDirectory) {
      var reader = entry.createReader();
      var children = [];
      // readEntries 每次最多返回约 100 条，必须循环读到返回空数组为止
      var readBatch = function () {
        reader.readEntries(function (batch) {
          if (!batch || batch.length === 0) {
            var i = 0;
            var next = function () {
              if (i >= children.length || out.length >= MAX_FILES) return resolve();
              walkEntry(children[i++], out).then(next);
            };
            next();
            return;
          }
          for (var b = 0; b < batch.length; b++) children.push(batch[b]);
          readBatch();
        }, function () { resolve(); });
      };
      readBatch();
      return;
    }

    resolve();
  });
}

// ---------- B. 分块提交状态机 ----------

function makeErrorResult(name, msg) {
  return {
    status: "error",
    label: "error",
    risk_level: "error",
    fake_prob: 0,
    risk_score: 0,
    elapsed_ms: 0,
    explanation_brief: msg,
    explanation: msg,
    overlay_b64: "",
    mask_b64: "",
    bbox_image_b64: null,
    tamper_overlay_b64: null,
    content_category: "unavailable",
    is_super_oversight_domain: false,
    file: name,
  };
}

// 分流判据必须与后端 explanation/api/routes.py 的 _is_pass 逐字一致；
// 任何一侧改动都要同步另一侧。
// 局部篡改（local_tamper）即使 risk_level==low 也不放行。
function routeResult(r, idx, file) {
  var s = state.screen;
  r.file = file ? (file.name || ("图片 " + (idx + 1))) : ("图片 " + (idx + 1));

  var isPass = r.status === "success"
    && r.label === "real"
    && r.risk_level === "low"
    && r.tamper_type !== "local_tamper";

  if (isPass) {
    s.passed.push({ idx: idx, name: r.file, fake_prob: Number(r.fake_prob || 0) });
    return;
  }

  if (r.status !== "success") s.errors++;
  if (r.status === "success" && !r.overlay_b64) {
    console.warn("evidence_policy 判据疑似漂移", r.file);
  }
  s.flagged.push({ idx: idx, name: r.file, data: r });
}

function setScreeningUiBusy(busy) {
  el.batchAnalyzeButton.disabled = busy;
  el.batchAnalyzeButton.classList.toggle("loading", busy);
  el.batchAnalyzeButton.textContent = busy ? text.batchAnalyzing : text.batchAnalyze;
  el.clearFilesButton.disabled = busy;
  el.multiDropzone.classList.toggle("disabled", busy);
  el.folderButton.classList.toggle("disabled", busy);
  el.folderButton.disabled = busy;
}

function showProgress() {
  el.screenProgress.style.display = "";
  el.abortButton.disabled = false;
  el.abortButton.textContent = "中断 ×";
  el.progressFill.style.width = "0%";
  updateProgress();
}

function hideProgress() {
  el.screenProgress.style.display = "none";
}

function updateProgress() {
  var s = state.screen;
  el.progressText.textContent = s.done + " / " + s.total;

  var eta = "--";
  if (s.done >= s.chunkSize && s.done < s.total && s.done > 0) {
    eta = formatDuration((s.elapsedMs / s.done) * (s.total - s.done));
  } else if (s.done >= s.total && s.total > 0) {
    eta = "0s";
  }
  el.progressMeta.textContent = "已拦截 " + s.flagged.length + " · 预计剩余 " + eta;
  el.progressFill.style.width = s.total > 0 ? ((s.done / s.total) * 100).toFixed(1) + "%" : "0%";
}

async function postBatch(imagesBase64, options) {
  var res = await fetch("/api/v1/analyze/batch", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ images_base64: imagesBase64, options: options }),
  });
  var data = await res.json();
  if (!res.ok) throw new Error(data.detail || "HTTP " + res.status);
  return data;
}

async function submitBatch() {
  if (state.files.length === 0 || state.screen.running) return;

  resetScreening();
  var s = state.screen;
  s.running = true;
  s.total = state.files.length;
  s.startedAt = (window.performance && performance.now) ? performance.now() : Date.now();

  setScreeningUiBusy(true);
  showProgress();
  el.batchEmptyState.textContent = text.batchConvert;
  el.batchEmptyState.style.display = "";

  var options = {
    overlay_alpha: Number(el.multiAlphaRange.value),
    enable_localization: el.multiLocalizationToggle.checked,
    language: "zh",
    detail_level: "standard",
    // 通过项不回传证据图，千张批次下省掉绝大部分 base64 传输
    evidence_policy: "flagged",
  };

  var now = function () {
    return (window.performance && performance.now) ? performance.now() : Date.now();
  };

  try {
    for (var start = 0; start < state.files.length; start += s.chunkSize) {
      // 中断只在块边界生效，当前块跑完即停，已出结果保留
      if (s.abortRequested) {
        s.interrupted = true;
        break;
      }

      var chunk = state.files.slice(start, start + s.chunkSize);
      var data = null;
      var failMsg = "";

      try {
        // 仅本块转 base64，绝不整批
        var payload = await Promise.all(chunk.map(function (f) { return fileToBase64(f); }));
        try {
          data = await postBatch(payload, options);
        } catch (err1) {
          await sleep(1000);   // 单次自动重试
          data = await postBatch(payload, options);
        }
      } catch (err2) {
        data = null;
        failMsg = (err2 && err2.message) ? err2.message : String(err2);
      }

      if (data && Array.isArray(data.results)) {
        for (var j = 0; j < chunk.length; j++) {
          var r = data.results[j] || makeErrorResult(chunk[j].name, "后端未返回该条结果");
          routeResult(r, start + j, chunk[j]);
        }
      } else {
        for (var k = 0; k < chunk.length; k++) {
          routeResult(makeErrorResult(chunk[k].name, text.batchFailed + ": " + failMsg), start + k, chunk[k]);
        }
      }

      s.done = Math.min(start + chunk.length, s.total);
      s.elapsedMs = now() - s.startedAt;
      updateProgress();
    }
  } finally {
    s.elapsedMs = now() - s.startedAt;
    s.running = false;
    s.finished = true;
    hideProgress();
    setScreeningUiBusy(false);
    el.batchAnalyzeButton.disabled = state.files.length === 0;
    renderFunnelResults();
  }
}

// ---------- C. 漏斗结果 UI ----------

function isLocalTamper(r) {
  return r.label === "local_tamper" || r.tamper_type === "local_tamper";
}

function severityRank(r) {
  if (r.status === "error" || r.label === "error") return 5;
  if (isSuperOversightDomain(r)) return 0;  // 最高优先级：超监管领域
  if (isHighConfidenceFake(r)) return 1;    // 高置信伪造（非超监管）
  if (r.label === "fake") return 2;         // AIGC 伪造
  if (isLocalTamper(r)) return 3;           // 局部篡改
  return 4; // real 但 medium/high —— 需复核真图
}

function compareSeverity(a, b) {
  var ra = severityRank(a.data);
  var rb = severityRank(b.data);
  if (ra !== rb) return ra - rb;
  var sa = Number(a.data.risk_score || 0);
  var sb = Number(b.data.risk_score || 0);
  if (sa !== sb) return sb - sa;
  return Number(b.data.fake_prob || 0) - Number(a.data.fake_prob || 0);
}

function clearResultArea() {
  revokeAll(resultUrlRegistry);
  var cards = el.resultGrid.querySelectorAll(".result-card, .show-more-button");
  for (var c = 0; c < cards.length; c++) cards[c].remove();
  var passed = document.getElementById("passedSection");
  if (passed) passed.remove();
}

function resetScreening() {
  state.screen = newScreenState();
  clearResultArea();
  el.exportBatchButton.style.display = "none";
  el.batchStats.style.display = "none";
  el.batchInterrupted.style.display = "none";
  el.batchLatencyText.textContent = "-- ms";
  el.batchEmptyState.textContent = text.batchEmpty;
  el.batchEmptyState.style.display = "";
  hideProgress();
}

var renderedFlaggedCount = 0;
var FIRST_PAGE = 60;

function renderFunnelResults() {
  var s = state.screen;
  s.sortedFlagged = s.flagged.slice().sort(compareSeverity);

  clearResultArea();

  // --- 统计面板（超监管与高置信独立计数，可重叠）---
  var soCount = 0, highConf = 0, fakeCount = 0, tamperCount = 0, reviewCount = 0;
  s.sortedFlagged.forEach(function (entry) {
    if (isSuperOversightDomain(entry.data)) soCount++;
    if (isHighConfidenceFake(entry.data)) highConf++;
    if (entry.data.label === "fake") fakeCount++;
    if (isLocalTamper(entry.data)) tamperCount++;
    var rank = severityRank(entry.data);
    if (rank === 4) reviewCount++;
  });

  el.batchTotalCount.textContent = String(s.total);
  el.batchPassedCount.textContent = String(s.passed.length);
  el.batchFlaggedCount.textContent = String(s.flagged.length);
  el.batchSoCount.textContent = String(soCount);
  el.batchHighConfCount.textContent = String(highConf);
  el.batchErrorCount.textContent = String(s.errors);
  el.batchBreakdown.textContent =
    (soCount > 0 ? "超监管高危 " + soCount + " · " : "") +
    (highConf > 0 ? "高置信伪造 " + highConf + " · " : "") +
    "AIGC 伪造 " + fakeCount + " · 局部篡改 " + tamperCount + " · 需复核真图 " + reviewCount;

  if (s.interrupted) {
    el.batchInterrupted.textContent = "已中断：完成 " + s.done + "/" + s.total;
    el.batchInterrupted.style.display = "";
  } else {
    el.batchInterrupted.style.display = "none";
  }

  el.batchStats.style.display = "block";
  el.batchLatencyText.textContent = Math.round(s.elapsedMs) + " ms";

  // --- 待处置卡片 ---
  if (s.sortedFlagged.length === 0) {
    el.batchEmptyState.textContent = text.batchAllPassed;
    el.batchEmptyState.style.display = "";
  } else {
    el.batchEmptyState.style.display = "none";
    renderedFlaggedCount = 0;
    appendFlaggedCards(FIRST_PAGE);
  }

  renderPassedSection();

  el.exportBatchButton.style.display = s.sortedFlagged.length > 0 ? "block" : "none";
}

function appendFlaggedCards(count) {
  var s = state.screen;
  var existing = el.resultGrid.querySelector(".show-more-button");
  if (existing) existing.remove();

  var end = Math.min(renderedFlaggedCount + count, s.sortedFlagged.length);
  for (var i = renderedFlaggedCount; i < end; i++) {
    el.resultGrid.appendChild(createResultCard(s.sortedFlagged[i], i));
  }
  renderedFlaggedCount = end;

  var remaining = s.sortedFlagged.length - renderedFlaggedCount;
  if (remaining > 0) {
    var btn = document.createElement("button");
    btn.className = "show-more-button";
    btn.type = "button";
    btn.textContent = "显示更多（余 " + remaining + "）";
    btn.addEventListener("click", function () { appendFlaggedCards(FIRST_PAGE); });
    el.resultGrid.appendChild(btn);
  }
}

function renderPassedSection() {
  var s = state.screen;
  if (s.passed.length === 0) return;

  var section = document.createElement("section");
  section.className = "passed-section";
  section.id = "passedSection";

  var toggle = document.createElement("button");
  toggle.className = "passed-toggle";
  toggle.type = "button";
  toggle.textContent = "筛选通过 " + s.passed.length + " 张 ▼";

  var list = document.createElement("div");
  list.className = "passed-list";
  list.style.display = "none";

  var built = false;
  toggle.addEventListener("click", function () {
    var open = list.style.display !== "none";
    if (open) {
      list.style.display = "none";
      toggle.textContent = "筛选通过 " + s.passed.length + " 张 ▼";
      return;
    }
    if (!built) {
      // 首次展开才构建 DOM
      var frag = document.createDocumentFragment();
      s.passed.forEach(function (p) {
        var row = document.createElement("div");
        row.className = "passed-row";
        row.textContent = p.name + " · 伪造概率 " + asPercent(p.fake_prob);
        frag.appendChild(row);
      });
      list.appendChild(frag);
      built = true;
    }
    list.style.display = "";
    toggle.textContent = "筛选通过 " + s.passed.length + " 张 ▲";
  });

  section.appendChild(toggle);
  section.appendChild(list);
  el.resultGrid.parentNode.insertBefore(section, el.resultGrid.nextSibling);
}

// entry = {idx, name, data}；displayIndex 为 state.screen.sortedFlagged 中的下标
function createResultCard(entry, displayIndex) {
  var result = entry.data;
  var card = document.createElement("article");
  var label = result.label || "error";
  card.className = "result-card " + label;
  var isSO = isSuperOversightDomain(result);
  var isHighConf = isHighConfidenceFake(result);
  if (isSO) card.classList.add("super-oversight");
  else if (isHighConf) card.classList.add("high-confidence-fake");
  card.dataset.index = String(displayIndex);
  card.style.setProperty("--i", String(displayIndex % FIRST_PAGE));

  var file = state.files[entry.idx];
  var fileName = entry.name || (file ? file.name : ("图片 " + (entry.idx + 1)));
  var thumbSrc = file ? trackURL(file, resultUrlRegistry) : "";

  // Head
  var head = document.createElement("div");
  head.className = "card-head";

  var thumb = document.createElement("img");
  thumb.className = "card-thumb";
  if (thumbSrc) thumb.src = thumbSrc;
  thumb.alt = "";

  var meta = document.createElement("div");
  meta.className = "card-meta";

  var nameEl = document.createElement("span");
  nameEl.className = "card-name";
  nameEl.textContent = fileName;

  var verdict = document.createElement("span");
  verdict.className = "card-verdict";
  verdict.textContent = text.label[label] || label;

  var badges = document.createElement("div");
  badges.className = "card-badges";
  badges.appendChild(verdict);

  // 两条独立判定链可同时显示 badge
  if (isSO) {
    var soBadge = document.createElement("span");
    soBadge.className = "card-rank-badge rank-hot";
    soBadge.textContent = text.rankLabel[0];  // "超监管高危"
    badges.appendChild(soBadge);
  }
  if (isHighConf) {
    var hcBadge = document.createElement("span");
    hcBadge.className = "card-rank-badge rank-hot";
    hcBadge.textContent = text.rankLabel[1];  // "高置信伪造"
    badges.appendChild(hcBadge);
  }
  // fallback: 非超监管、非高置信时，按 severityRank 显示一个标签
  if (!isSO && !isHighConf) {
    var rank = severityRank(result);
    var rankLabelText = text.rankLabel[rank];
    if (rankLabelText !== verdict.textContent) {
      var rankBadge = document.createElement("span");
      rankBadge.className = "card-rank-badge";
      rankBadge.textContent = rankLabelText;
      badges.appendChild(rankBadge);
    }
  }

  meta.appendChild(nameEl);
  meta.appendChild(badges);
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
  toggle.addEventListener("click", function () { expandCard(displayIndex); });

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
        tabBtn.dataset.cardIndex = String(displayIndex);
        tabBtn.textContent = evidenceLabels[view];
        tabBtn.addEventListener("click", function (evt) {
          evt.stopPropagation();
          switchMiniEvidence(displayIndex, view);
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
    miniView.dataset.cardIndex = String(displayIndex);

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

  // 高置信伪造及以上：显示伪造判据说明（超监管 + 普通高置信均展示）
  if (isHighConf) {
    var cardReview = document.createElement("p");
    cardReview.className = "card-review";
    cardReview.textContent = text.soCardReview;
    detail.appendChild(cardReview);
  }

  if (isSO) {
    var cardDimBars = document.createElement("div");
    cardDimBars.className = "card-dim-bars";
    renderDimensionBars(result.dimension_scores || {}, cardDimBars, true);
    detail.appendChild(cardDimBars);

    // 处置流程提示：与 cardReview 统一风格
    var processTip = document.createElement("p");
    processTip.className = "card-review";
    processTip.textContent = text.soProcessTip;
    detail.appendChild(processTip);
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

  var entry = state.screen.sortedFlagged[cardIndex];
  var result = entry && entry.data;
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
      const s = state.screen;
      const flagged = s.sortedFlagged || [];
      if (flagged.length === 0) {
        alert("本批次全部筛选通过，无待处置条目可导出");
        return null;
      }
      if (flagged.length > 100 &&
          !confirm("待处置条目较多(" + flagged.length + ")，报告生成与 PDF 渲染可能较慢，是否继续？")) {
        return null;
      }
      return {
        type: "batch",
        results: flagged.map(function (e) { return e.data; }),
        options: { include_llm: true },
        screening: {
          total: s.total,
          passed: s.passed.length,
          flagged: s.flagged.length,
          elapsed_ms: Math.round(s.elapsedMs),
        },
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
      if (type === "single") alert("没有可导出的检测结果");
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

  // --- Folder picker ---
  el.folderButton.addEventListener("click", function () {
    if (state.screen.running) return;
    el.folderInput.click();
  });
  el.folderInput.addEventListener("change", function (event) {
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

  el.multiDropzone.addEventListener("drop", async function (event) {
    event.preventDefault();
    if (state.screen.running) return;
    // collectFromDataTransfer 在首个 await 之前同步取完 entry
    var files = await collectFromDataTransfer(event.dataTransfer);
    addFiles(files);
  });

  // --- Batch analyze button ---
  el.batchAnalyzeButton.addEventListener("click", submitBatch);

  // --- Abort button ---
  el.abortButton.addEventListener("click", function () {
    if (!state.screen.running) return;
    state.screen.abortRequested = true;
    el.abortButton.disabled = true;
    el.abortButton.textContent = "正在停止…";
  });

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

  // --- Capability card modal (静态内容，无 JS 数据) ---
  function openCap() { el.capModal.style.display = "flex"; }
  function closeCap() { el.capModal.style.display = "none"; }
  el.capButton.addEventListener("click", openCap);
  el.capClose.addEventListener("click", closeCap);
  el.capOverlay.addEventListener("click", closeCap);

  // ESC to close modal
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    if (el.previewModal.style.display === "flex") {
      closePreview();
    } else if (el.capModal.style.display === "flex") {
      closeCap();
    }
  });
}

bindEvents();
loadHealth();
renderFileList();

// 调试钩子（浏览器自动化验证用）
window.__tg = {
  state: state,
  addFiles: addFiles,
  submitBatch: submitBatch,
  requestAbort: function () { state.screen.abortRequested = true; },
  switchMode: switchMode,
};
