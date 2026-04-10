const DEFAULT_SETTINGS = {
  apiBase: "http://127.0.0.1:8000",
  apiPrefix: "/api/v1",
  apiKeyHeaderName: "X-API-Key",
  apiKey: "",
  requesterId: "browser-user",
  providerOverride: "auto",
  qualityPreference: "best",
  pollIntervalSeconds: 1.0,
  maxWaitSeconds: 300,
  requestTimeoutSeconds: 60,
  saveAs: true,
};

const PROVIDER_HOSTS = {
  youtube: ["youtube.com", "youtu.be"],
  instagram: ["instagram.com"],
  tiktok: ["tiktok.com"],
  facebook: ["facebook.com", "fb.watch"],
  x: ["x.com", "twitter.com"],
  vimeo: ["vimeo.com", "player.vimeo.com"],
};

const TERMINAL_STATUSES = new Set(["completed", "failed", "canceled"]);

const ui = {
  apiBase: document.getElementById("apiBase"),
  apiPrefix: document.getElementById("apiPrefix"),
  apiKeyHeaderName: document.getElementById("apiKeyHeaderName"),
  apiKey: document.getElementById("apiKey"),
  requesterId: document.getElementById("requesterId"),
  providerOverride: document.getElementById("providerOverride"),
  qualityPreference: document.getElementById("qualityPreference"),
  pollIntervalSeconds: document.getElementById("pollIntervalSeconds"),
  maxWaitSeconds: document.getElementById("maxWaitSeconds"),
  saveAs: document.getElementById("saveAs"),
  saveBtn: document.getElementById("saveBtn"),
  downloadBtn: document.getElementById("downloadBtn"),
  activeTabUrl: document.getElementById("activeTabUrl"),
  status: document.getElementById("status"),
};

init().catch((error) => {
  setStatus(`Erro na inicializacao: ${error.message}`);
});

async function init() {
  const settings = await getSettings();
  writeForm(settings);
  await renderActiveTab();

  ui.saveBtn.addEventListener("click", async () => {
    try {
      const next = readForm();
      await saveSettings(next);
      appendStatus("Configuracao salva.");
    } catch (error) {
      appendStatus(`Erro ao salvar configuracao: ${error.message}`);
    }
  });

  ui.downloadBtn.addEventListener("click", async () => {
    await runDownloadFromActiveTab();
  });
}

async function runDownloadFromActiveTab() {
  ui.downloadBtn.disabled = true;
  ui.saveBtn.disabled = true;
  setStatus("Iniciando fluxo...\n");

  try {
    const settings = readForm();
    await saveSettings(settings);

    const tab = await getActiveTab();
    if (!tab.url || !/^https?:\/\//i.test(tab.url)) {
      throw new Error("A aba ativa nao possui URL HTTP/HTTPS valida.");
    }

    const provider =
      settings.providerOverride === "auto"
        ? inferProvider(tab.url)
        : settings.providerOverride;
    const generatedDownloadId = `dl-browser-${Date.now().toString(36)}-${randomHex(8)}`;

    appendStatus(`Aba ativa: ${tab.url}`);
    appendStatus(`Provider resolvido: ${provider}`);
    appendStatus(`download_id gerado: ${generatedDownloadId}`);

    const createPayload = {
      provider,
      video_reference: tab.url,
      download_id: generatedDownloadId,
      quality_preference: settings.qualityPreference,
      requester_id: settings.requesterId,
      authorization: {
        session_proof: `sess-${randomHex(16)}`,
        entitlement_proof: `ent-${randomHex(16)}`,
      },
      prefer_cached_authorization: true,
    };

    const createBody = await requestJson(settings, "POST", "/downloads", createPayload);
    const downloadId = createBody.download_id;
    if (createBody.message) {
      appendStatus(`API: ${createBody.message}`);
    }
    appendStatus(`Download enfileirado: ${downloadId}`);

    const finalStatus = await waitForTerminalStatus(settings, downloadId);
    if (finalStatus.queue_status !== "completed") {
      throw new Error(
        `Download finalizou com status ${finalStatus.queue_status} (code=${
          finalStatus.code || "n/a"
        })`
      );
    }

    appendStatus("Download concluido na API. Gerando token...");
    const tokenBody = await requestJson(
      settings,
      "POST",
      `/downloads/${encodeURIComponent(downloadId)}/file-token`,
      null
    );

    appendStatus("Baixando arquivo final...");
    const fileResponse = await requestRaw(
      settings,
      "GET",
      `/downloads/${encodeURIComponent(downloadId)}/file?token=${encodeURIComponent(tokenBody.token)}`,
      null
    );

    const blob = await fileResponse.blob();
    const suggestedName = resolveFilename(
      fileResponse.headers.get("content-disposition"),
      tab.url,
      downloadId
    );
    await downloadBlob(blob, suggestedName, settings.saveAs);

    appendStatus(`Arquivo salvo com sucesso: ${suggestedName}`);
  } catch (error) {
    appendStatus(`Falha: ${error.message}`);
  } finally {
    ui.downloadBtn.disabled = false;
    ui.saveBtn.disabled = false;
  }
}

async function waitForTerminalStatus(settings, downloadId) {
  const startedAt = Date.now();
  let lastStatus = "";

  while (true) {
    const body = await requestJson(
      settings,
      "GET",
      `/downloads/${encodeURIComponent(downloadId)}`,
      null
    );

    if (body.queue_status !== lastStatus) {
      lastStatus = body.queue_status;
      appendStatus(`queue_status=${body.queue_status}`);
    }

    if (TERMINAL_STATUSES.has(body.queue_status)) {
      return body;
    }

    const elapsedSeconds = (Date.now() - startedAt) / 1000;
    if (elapsedSeconds >= settings.maxWaitSeconds) {
      throw new Error("Timeout aguardando conclusao do download.");
    }

    await sleep(settings.pollIntervalSeconds * 1000);
  }
}

function resolveFilename(contentDisposition, sourceUrl, downloadId) {
  const fromHeader = parseFilenameFromContentDisposition(contentDisposition);
  if (fromHeader) {
    return sanitizeFilename(fromHeader);
  }

  try {
    const parsed = new URL(sourceUrl);
    const pathName = parsed.pathname || "";
    const suffix = pathName.includes(".")
      ? pathName.slice(pathName.lastIndexOf("."))
      : ".bin";
    return sanitizeFilename(`${downloadId}${suffix}`);
  } catch {
    return `${downloadId}.bin`;
  }
}

function parseFilenameFromContentDisposition(contentDisposition) {
  if (!contentDisposition) {
    return null;
  }

  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match && utf8Match[1]) {
    return decodeURIComponent(utf8Match[1]);
  }

  const simpleMatch = contentDisposition.match(/filename="?([^";]+)"?/i);
  return simpleMatch && simpleMatch[1] ? simpleMatch[1] : null;
}

function sanitizeFilename(value) {
  return value.replace(/[<>:"/\\|?*]+/g, "_").trim() || "download.bin";
}

async function downloadBlob(blob, filename, saveAs) {
  const objectUrl = URL.createObjectURL(blob);
  try {
    await new Promise((resolve, reject) => {
      chrome.downloads.download(
        {
          url: objectUrl,
          filename,
          saveAs: Boolean(saveAs),
        },
        (downloadId) => {
          if (chrome.runtime.lastError) {
            reject(new Error(chrome.runtime.lastError.message));
            return;
          }
          if (!downloadId) {
            reject(new Error("Falha ao iniciar download no navegador."));
            return;
          }
          resolve(downloadId);
        }
      );
    });
  } finally {
    setTimeout(() => URL.revokeObjectURL(objectUrl), 60000);
  }
}

function inferProvider(videoUrl) {
  try {
    const hostname = (new URL(videoUrl).hostname || "").toLowerCase();
    for (const [provider, hosts] of Object.entries(PROVIDER_HOSTS)) {
      for (const host of hosts) {
        if (hostname === host || hostname.endsWith(`.${host}`)) {
          return provider;
        }
      }
    }
    return "panda_video";
  } catch {
    return "panda_video";
  }
}

function randomHex(length) {
  const bytes = new Uint8Array(Math.ceil(length / 2));
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0"))
    .join("")
    .slice(0, length);
}

async function renderActiveTab() {
  try {
    const tab = await getActiveTab();
    ui.activeTabUrl.textContent = `Aba atual: ${tab.url || "sem URL"}`;
  } catch (error) {
    ui.activeTabUrl.textContent = `Aba atual: erro (${error.message})`;
  }
}

function getActiveTab() {
  return new Promise((resolve, reject) => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
        return;
      }
      if (!tabs || tabs.length === 0) {
        reject(new Error("Nenhuma aba ativa encontrada."));
        return;
      }
      resolve(tabs[0]);
    });
  });
}

function normalizeBaseUrl(baseUrl) {
  return String(baseUrl || "").trim().replace(/\/+$/, "");
}

function normalizeApiPrefix(prefix) {
  const trimmed = String(prefix || "").trim();
  if (!trimmed) {
    return "/api/v1";
  }
  return trimmed.startsWith("/") ? trimmed : `/${trimmed}`;
}

async function requestJson(settings, method, path, body) {
  const response = await requestRaw(settings, method, path, body);
  if (response.status === 204) {
    return null;
  }
  return response.json();
}

async function requestRaw(settings, method, path, body) {
  const url = `${normalizeBaseUrl(settings.apiBase)}${normalizeApiPrefix(settings.apiPrefix)}${path}`;
  const headers = {};

  if (body !== null) {
    headers["Content-Type"] = "application/json";
  }
  if (settings.apiKey) {
    headers[settings.apiKeyHeaderName] = settings.apiKey;
  }

  const response = await fetchWithTimeout(url, {
    method,
    headers,
    body: body === null ? undefined : JSON.stringify(body),
  }, settings.requestTimeoutSeconds * 1000);

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const errorBody = await response.json();
      detail = `${errorBody.code || response.status}: ${errorBody.message || detail}`;
    } catch {
      const errorText = await response.text();
      if (errorText) {
        detail = errorText;
      }
    }
    throw new Error(`HTTP ${response.status} - ${detail}`);
  }

  return response;
}

async function fetchWithTimeout(url, options, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, {
      ...options,
      signal: controller.signal,
    });
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error("Timeout da requisicao HTTP.");
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function getSettings() {
  const data = await new Promise((resolve, reject) => {
    chrome.storage.local.get(["settings"], (result) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
        return;
      }
      resolve(result);
    });
  });

  return {
    ...DEFAULT_SETTINGS,
    ...(data.settings || {}),
  };
}

async function saveSettings(next) {
  await new Promise((resolve, reject) => {
    chrome.storage.local.set({ settings: next }, () => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
        return;
      }
      resolve();
    });
  });
}

function readForm() {
  const settings = {
    apiBase: ui.apiBase.value.trim(),
    apiPrefix: normalizeApiPrefix(ui.apiPrefix.value),
    apiKeyHeaderName: ui.apiKeyHeaderName.value.trim() || "X-API-Key",
    apiKey: ui.apiKey.value.trim(),
    requesterId: ui.requesterId.value.trim() || "browser-user",
    providerOverride: ui.providerOverride.value,
    qualityPreference: ui.qualityPreference.value,
    pollIntervalSeconds: Number(ui.pollIntervalSeconds.value),
    maxWaitSeconds: Number(ui.maxWaitSeconds.value),
    requestTimeoutSeconds: DEFAULT_SETTINGS.requestTimeoutSeconds,
    saveAs: ui.saveAs.checked,
  };

  if (!settings.apiBase) {
    throw new Error("Informe API Base.");
  }
  if (!Number.isFinite(settings.pollIntervalSeconds) || settings.pollIntervalSeconds <= 0) {
    throw new Error("Poll deve ser maior que zero.");
  }
  if (!Number.isFinite(settings.maxWaitSeconds) || settings.maxWaitSeconds < 10) {
    throw new Error("Timeout deve ser pelo menos 10 segundos.");
  }

  return settings;
}

function writeForm(settings) {
  ui.apiBase.value = settings.apiBase;
  ui.apiPrefix.value = settings.apiPrefix;
  ui.apiKeyHeaderName.value = settings.apiKeyHeaderName;
  ui.apiKey.value = settings.apiKey;
  ui.requesterId.value = settings.requesterId;
  ui.providerOverride.value = settings.providerOverride;
  ui.qualityPreference.value = settings.qualityPreference;
  ui.pollIntervalSeconds.value = String(settings.pollIntervalSeconds);
  ui.maxWaitSeconds.value = String(settings.maxWaitSeconds);
  ui.saveAs.checked = Boolean(settings.saveAs);
}

function setStatus(text) {
  ui.status.textContent = text;
}

function appendStatus(text) {
  const stamp = new Date().toLocaleTimeString();
  ui.status.textContent += `[${stamp}] ${text}\n`;
  ui.status.scrollTop = ui.status.scrollHeight;
}
