const navToggle = document.querySelector("[data-nav-toggle]");
const navLinks = document.querySelector("[data-nav-links]");
const themeToggle = document.querySelector("[data-theme-toggle]");

const applyTheme = (theme) => {
  document.body.dataset.theme = theme;
  window.localStorage.setItem("fi-theme", theme);
};

applyTheme(window.localStorage.getItem("fi-theme") || "light");

if (themeToggle) {
  themeToggle.addEventListener("click", () => {
    applyTheme(document.body.dataset.theme === "dark" ? "light" : "dark");
  });
}

const showToast = (message) => {
  const stack = document.querySelector("[data-toast-stack]");
  if (!stack || !message) return;
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.textContent = message;
  stack.appendChild(toast);
  window.setTimeout(() => toast.remove(), 4200);
};

document.querySelectorAll(".flash").forEach((flash) => showToast(flash.textContent.trim()));

if (navToggle && navLinks) {
  navToggle.addEventListener("click", () => {
    navLinks.classList.toggle("open");
  });
}

document.querySelectorAll('input[type="file"]').forEach((input) => {
  input.addEventListener("change", () => {
    const label = input.closest("label");
    const target = label ? label.querySelector("[data-file-name]") : null;
    if (target && input.files.length) {
      target.textContent = input.files[0].name;
    }
    const preview = document.querySelector("[data-video-preview]");
    if (preview && input.files.length && input.files[0].type.startsWith("video/")) {
      preview.src = URL.createObjectURL(input.files[0]);
      preview.hidden = false;
    } else if (preview) {
      preview.hidden = true;
      preview.removeAttribute("src");
    }
  });
});

const startTransferProgress = (form) => {
  const rings = form.querySelectorAll(".loader-ring");
  const labels = form.querySelectorAll(".loader-percent");
  let progress = 0;

  const render = () => {
    rings.forEach((ring) => ring.style.setProperty("--progress", progress));
    labels.forEach((label) => {
      label.textContent = `${Math.round(progress)}%`;
    });
  };

  render();
  window.setInterval(() => {
    if (progress < 92) {
      progress += Math.max(1, (92 - progress) * 0.08);
      render();
    }
  }, 160);
};

document.querySelectorAll(".js-loading-form").forEach((form) => {
  form.addEventListener("submit", () => {
    if (form.matches("[data-football-analysis-form]")) return;
    form.classList.add("is-loading");
    startTransferProgress(form);
    form.querySelectorAll("button[type='submit']").forEach((button) => {
      button.disabled = true;
    });
  });
});

const footballForm = document.querySelector("[data-football-analysis-form]");

if (footballForm) {
  const progressBox = footballForm.querySelector("[data-football-progress]");
  const progressBar = footballForm.querySelector("[data-football-progress-bar]");
  const percentLabel = footballForm.querySelector("[data-football-percent]");
  const processedLabel = footballForm.querySelector("[data-football-processed]");
  const totalLabel = footballForm.querySelector("[data-football-total]");
  const leftLabel = footballForm.querySelector("[data-football-left]");
  const stageLabel = footballForm.querySelector("[data-football-stage]");

  const setFootballProgress = (data) => {
    const processed = Number(data.processed || 0);
    const total = Number(data.total || 0);
    const left = Number(data.remaining || Math.max(0, total - processed));
    const percent = total > 0 ? Math.min(100, Math.max(0, Number(data.percent || 0))) : 0;

    if (progressBar) progressBar.style.width = `${percent}%`;
    if (percentLabel) percentLabel.textContent = `${Math.round(percent)}%`;
    if (processedLabel) processedLabel.textContent = String(processed);
    if (totalLabel) totalLabel.textContent = String(total);
    if (leftLabel) leftLabel.textContent = String(left);
    if (stageLabel) stageLabel.textContent = data.message || "Processing";
  };

  const pollFootballJob = (jobId) => {
    window.setTimeout(async () => {
      try {
        const response = await fetch(`/football/jobs/${jobId}`);
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Could not read processing progress.");
        setFootballProgress(data);

        if (data.status === "complete" && data.result_url) {
          window.location.href = data.result_url;
          return;
        }
        if (data.status === "failed") {
          throw new Error(data.error || "Football analysis failed.");
        }
        pollFootballJob(jobId);
      } catch (error) {
        if (stageLabel) stageLabel.textContent = error.message;
        footballForm.querySelectorAll("button[type='submit']").forEach((button) => {
          button.disabled = false;
        });
      }
    }, 900);
  };

  footballForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    footballForm.classList.add("is-loading");
    if (progressBox) progressBox.hidden = false;
    setFootballProgress({ processed: 0, total: 0, remaining: 0, percent: 0, message: "Uploading" });
    footballForm.querySelectorAll("button[type='submit']").forEach((button) => {
      button.disabled = true;
    });

    try {
      const response = await fetch(footballForm.dataset.progressUrl, {
        method: "POST",
        body: new FormData(footballForm),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Could not start football analysis.");
      setFootballProgress({ processed: 0, total: 0, remaining: 0, percent: 0, message: "Queued" });
      pollFootballJob(data.job_id);
    } catch (error) {
      if (stageLabel) stageLabel.textContent = error.message;
      footballForm.querySelectorAll("button[type='submit']").forEach((button) => {
        button.disabled = false;
      });
    }
  });
}

const transferMenu = document.querySelector("[data-transfer-menu]");

if (transferMenu) {
  const cards = document.querySelectorAll("[data-transfer-action]");
  const panels = document.querySelectorAll("[data-transfer-panel]");

  const activateTransferAction = (action) => {
    cards.forEach((card) => {
      card.classList.toggle("active", card.dataset.transferAction === action);
    });
    panels.forEach((panel) => {
      panel.classList.toggle("active", panel.dataset.transferPanel === action);
    });
  };

  cards.forEach((card) => {
    card.addEventListener("click", () => {
      activateTransferAction(card.dataset.transferAction);
    });
  });

  activateTransferAction(transferMenu.dataset.activeAction || "predict");
}

const drawBarChart = (ctx, values, width, height) => {
  const pad = 36;
  const max = Math.max(1, ...values.map((item) => Math.abs(Number(item.value) || 0)));
  const barWidth = Math.max(18, (width - pad * 2) / Math.max(1, values.length) - 12);
  ctx.font = "12px Inter, sans-serif";
  values.forEach((item, index) => {
    const value = Number(item.value) || 0;
    const x = pad + index * (barWidth + 12);
    const barHeight = Math.abs(value) / max * (height - 90);
    const y = value >= 0 ? height - pad - barHeight : height - pad;
    ctx.fillStyle = value >= 0 ? "#116a5c" : "#b53b45";
    ctx.fillRect(x, y, barWidth, barHeight);
    ctx.fillStyle = getComputedStyle(document.body).getPropertyValue("--muted");
    ctx.fillText(String(item.label).slice(0, 14), x, height - 12);
  });
};

const drawLineChart = (ctx, values, width, height) => {
  const pad = 38;
  const max = Math.max(1, ...values.map((item) => Number(item.value) || 0));
  const step = (width - pad * 2) / Math.max(1, values.length - 1);
  ctx.strokeStyle = "#116a5c";
  ctx.lineWidth = 3;
  ctx.beginPath();
  values.forEach((item, index) => {
    const x = pad + index * step;
    const y = height - pad - ((Number(item.value) || 0) / max) * (height - pad * 2);
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
};

const drawRadarChart = (ctx, values, width, height) => {
  const cx = width / 2;
  const cy = height / 2;
  const radius = Math.min(width, height) * 0.34;
  ctx.strokeStyle = "rgba(17,106,92,0.28)";
  ctx.fillStyle = "rgba(17,106,92,0.24)";
  values.forEach((item, index) => {
    const angle = -Math.PI / 2 + index * (Math.PI * 2 / values.length);
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + Math.cos(angle) * radius, cy + Math.sin(angle) * radius);
    ctx.stroke();
    ctx.fillStyle = getComputedStyle(document.body).getPropertyValue("--muted");
    ctx.fillText(item.label, cx + Math.cos(angle) * (radius + 18) - 18, cy + Math.sin(angle) * (radius + 18));
  });
  ctx.beginPath();
  values.forEach((item, index) => {
    const angle = -Math.PI / 2 + index * (Math.PI * 2 / values.length);
    const r = radius * Math.min(100, Math.max(0, Number(item.value) || 0)) / 100;
    const x = cx + Math.cos(angle) * r;
    const y = cy + Math.sin(angle) * r;
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.closePath();
  ctx.fillStyle = "rgba(17,106,92,0.28)";
  ctx.fill();
  ctx.strokeStyle = "#116a5c";
  ctx.stroke();
};

document.querySelectorAll("[data-simple-chart]").forEach((canvas) => {
  const values = JSON.parse(canvas.dataset.chartValues || "[]");
  const kind = canvas.dataset.chartKind || "bar";
  const rect = canvas.getBoundingClientRect();
  const width = Math.max(320, rect.width || canvas.parentElement.clientWidth || 360);
  const height = 280;
  canvas.width = width * window.devicePixelRatio;
  canvas.height = height * window.devicePixelRatio;
  canvas.style.height = `${height}px`;
  const ctx = canvas.getContext("2d");
  ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
  ctx.clearRect(0, 0, width, height);
  if (kind === "line") drawLineChart(ctx, values, width, height);
  else if (kind === "radar") drawRadarChart(ctx, values, width, height);
  else drawBarChart(ctx, values, width, height);
});
