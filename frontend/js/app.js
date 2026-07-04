// ── Config ────────────────────────────────────────────────────────────────
// On Vercel, API routes are on the same domain
const API = "";

// ── Elements ──────────────────────────────────────────────────────────────
const templateSelect = document.getElementById("template-select");
const dropzone       = document.getElementById("dropzone");
const fileInput      = document.getElementById("file-input");
const fileCount      = document.getElementById("file-count");
const depthSlider    = document.getElementById("depth-slider");
const depthLabel     = document.getElementById("depth-label");
const tagWrap        = document.getElementById("tag-wrap");
const tagList        = document.getElementById("tag-list");
const tagInput       = document.getElementById("tag-input");
const checkBtn       = document.getElementById("check-btn");
const spinner        = document.getElementById("spinner");
const resultCard     = document.getElementById("result-card");
const statusBar      = document.getElementById("status-bar");
const issuesSection  = document.getElementById("issues-section");
const mdSection      = document.getElementById("md-section");
const mdOutput       = document.getElementById("md-output");
const copyBtn        = document.getElementById("copy-btn");
const dlBtn          = document.getElementById("dl-btn");

const UNLIMITED = 10;
let collectedFiles = [];
let ignoreTags     = [];  // user-added extra folders to ignore

// ── Tag input ─────────────────────────────────────────────────────────────
function addTag(value) {
  const name = value.trim().replace(/^\/|\/$/g, ""); // strip slashes
  if (!name || ignoreTags.includes(name.toLowerCase())) return;

  ignoreTags.push(name.toLowerCase());

  const tag = document.createElement("span");
  tag.className = "tag";
  tag.innerHTML = `${name}<button class="tag-remove" title="Remove">×</button>`;
  tag.querySelector(".tag-remove").addEventListener("click", () => {
    ignoreTags = ignoreTags.filter(t => t !== name.toLowerCase());
    tag.remove();
  });
  tagList.appendChild(tag);
}

tagInput.addEventListener("keydown", e => {
  if (e.key === "Enter" || e.key === ",") {
    e.preventDefault();
    addTag(tagInput.value);
    tagInput.value = "";
  }
  // Backspace on empty input removes last tag
  if (e.key === "Backspace" && tagInput.value === "" && ignoreTags.length) {
    const last = tagList.lastElementChild;
    if (last) {
      ignoreTags.pop();
      last.remove();
    }
  }
});

// clicking the wrapper focuses the input
tagWrap.addEventListener("click", () => tagInput.focus());

// ── Depth slider ──────────────────────────────────────────────────────────
function getDepth() {
  const val = parseInt(depthSlider.value);
  return val >= UNLIMITED ? null : val;
}

depthSlider.addEventListener("input", () => {
  const val = parseInt(depthSlider.value);
  depthLabel.textContent = val >= UNLIMITED ? "unlimited" : val;
});

// ── Load templates ────────────────────────────────────────────────────────
async function loadTemplates() {
  try {
    const res  = await fetch(`${API}/templates`);
    const list = await res.json();
    templateSelect.innerHTML = list
      .map(t => `<option value="${t.id}">${t.label}</option>`)
      .join("");
  } catch {
    templateSelect.innerHTML = `<option value="">⚠ Could not reach API</option>`;
  }
}

loadTemplates();

// ── File handling ─────────────────────────────────────────────────────────
function handleFiles(fileList) {
  const files = Array.from(fileList);
  if (!files.length) return;

  collectedFiles = files.map(f => {
    const parts = (f.webkitRelativePath || f.name).replace(/\\/g, "/").split("/");
    return parts.slice(1).join("/") || f.name;
  }).filter(Boolean);

  fileCount.style.display = "block";
  fileCount.textContent   = `${collectedFiles.length} files detected`;
  updateBtn();
}

fileInput.addEventListener("change", () => handleFiles(fileInput.files));

dropzone.addEventListener("dragover",  e => { e.preventDefault(); dropzone.classList.add("drag-over"); });
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag-over"));
dropzone.addEventListener("drop", e => {
  e.preventDefault();
  dropzone.classList.remove("drag-over");
  handleFiles(e.dataTransfer.files);
});

templateSelect.addEventListener("change", updateBtn);

function updateBtn() {
  checkBtn.disabled = !(collectedFiles.length && templateSelect.value);
}

// ── Check ─────────────────────────────────────────────────────────────────
checkBtn.addEventListener("click", async () => {
  checkBtn.disabled        = true;
  spinner.style.display    = "block";
  resultCard.style.display = "none";

  try {
    const depth = getDepth();
    const body  = {
      template: templateSelect.value,
      files:    collectedFiles,
      ignore:   ignoreTags,
      ...(depth !== null && { depth }),
    };

    const res  = await fetch(`${API}/check`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(body),
    });

    const data = await res.json();
    spinner.style.display = "none";

    if (data.error) { showError(data.error); return; }
    renderResult(data);

  } catch {
    spinner.style.display = "none";
    showError("Could not reach the API. Is the backend running?");
  } finally {
    checkBtn.disabled = false;
  }
});

// ── Render ────────────────────────────────────────────────────────────────
function showError(msg) {
  resultCard.style.display = "block";
  statusBar.className      = "status-bar err";
  statusBar.innerHTML      = `<span>❌</span> ${msg}`;
  issuesSection.innerHTML  = "";
  mdSection.style.display  = "none";
}

function renderResult(data) {
  resultCard.style.display = "block";
  issuesSection.innerHTML  = "";

  const icons = { ok: "✅", warning: "⚠️", error: "❌" };
  const msgs  = {
    ok:      "Structure matches the template.",
    warning: "Mostly correct — a few recommended files are missing.",
    error:   "Structure does not match the template.",
  };

  statusBar.className = `status-bar ${data.status === "warning" ? "warn" : data.status}`;
  statusBar.innerHTML = `<span>${icons[data.status]}</span> ${msgs[data.status]}`;

  if (data.major_missing.length || data.major_forbidden.length) {
    const sec = document.createElement("div");
    sec.className = "issue-list";
    sec.innerHTML = `<h3>Missing required files</h3><ul>${
      data.major_missing.map(f   => `<li class="missing">missing &nbsp;→ <strong>${f}</strong></li>`).join("") +
      data.major_forbidden.map(f => `<li class="forbidden">forbidden → <strong>${f}</strong></li>`).join("")
    }</ul>`;
    issuesSection.appendChild(sec);
  }

  if (data.minor_missing.length) {
    const sec = document.createElement("div");
    sec.className = "issue-list";
    sec.innerHTML = `<h3>Recommended files not found</h3><ul>${
      data.minor_missing.map(f => `<li class="minor">recommended → <strong>${f}</strong></li>`).join("")
    }</ul>`;
    issuesSection.appendChild(sec);
  }

  if (data.markdown) {
    mdSection.style.display = "block";
    mdOutput.textContent    = data.markdown;
    const blob = new Blob([data.markdown], { type: "text/markdown" });
    dlBtn.href = URL.createObjectURL(blob);
  } else {
    mdSection.style.display = "none";
  }
}

// ── Copy ──────────────────────────────────────────────────────────────────
copyBtn.addEventListener("click", () => {
  navigator.clipboard.writeText(mdOutput.textContent).then(() => {
    copyBtn.textContent = "Copied!";
    copyBtn.classList.add("success");
    setTimeout(() => {
      copyBtn.textContent = "Copy markdown";
      copyBtn.classList.remove("success");
    }, 1800);
  });
});