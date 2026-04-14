const DEFAULT_SETTINGS = {
  apiBase: "http://127.0.0.1:8010",
  apiPrefix: "/api/v1",
  apiKeyHeaderName: "X-API-Key",
  apiKey: "",
  requesterId: "browser-user",
  manualVideoReference: "",
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
  manualVideoReference: document.getElementById("manualVideoReference"),
  providerOverride: document.getElementById("providerOverride"),
  qualityPreference: document.getElementById("qualityPreference"),
  pollIntervalSeconds: document.getElementById("pollIntervalSeconds"),
  maxWaitSeconds: document.getElementById("maxWaitSeconds"),
  saveAs: document.getElementById("saveAs"),
  saveBtn: document.getElementById("saveBtn"),
  downloadBtn: document.getElementById("downloadBtn"),
  activeTabUrl: document.getElementById("activeTabUrl"),
  status: document.getElementById("status"),
  sniffedPanel: document.getElementById("sniffedPanel"),
  sniffedList: document.getElementById("sniffedList"),
};

init().catch((error) => {
  setStatus(`Erro na inicializacao: ${error.message}`);
});

async function init() {
  const settings = await getSettings();
  writeForm(settings);
  await renderActiveTab();
  await renderSniffedPanel();

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

    const resolvedReference = settings.manualVideoReference
      ? {
          videoReference: settings.manualVideoReference,
          source: "manual-input",
          candidatesCount: 1,
        }
      : await resolveVideoReference(tab);

    if (
      settings.manualVideoReference &&
      !/^https?:\/\//i.test(settings.manualVideoReference)
    ) {
      throw new Error("Referencia manual invalida. Use URL iniciando com http:// ou https://.");
    }

    const provider =
      settings.providerOverride === "auto"
        ? inferProvider(resolvedReference.videoReference)
        : settings.providerOverride;
    const generatedDownloadId = `dl-browser-${Date.now().toString(36)}-${randomHex(8)}`;

    appendStatus(`Aba ativa: ${tab.url}`);
    appendStatus(`Referencia usada: ${resolvedReference.videoReference}`);
    if (resolvedReference.source !== "tab-url") {
      appendStatus(`Fonte detectada: ${resolvedReference.source}`);
    }
    appendStatus(`Provider resolvido: ${provider}`);
    appendStatus(`download_id gerado: ${generatedDownloadId}`);

    const createPayload = {
      provider,
      video_reference: resolvedReference.videoReference,
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
      resolvedReference.videoReference,
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

      if (body.queue_status === "failed" && body.diagnostic_detail) {
        const diagnostic = formatDiagnosticDetail(body.diagnostic_detail);
        if (diagnostic) {
          appendStatus(`Diagnostico API: ${diagnostic}`);
        }
      }
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

function sanitizeDiagnosticDetail(value) {
  return String(value || "")
    .replace(/\x1b\[[0-9;]*m/gi, "")
    .replace(/\s+/g, " ")
    .trim();
}

function formatDiagnosticDetail(value) {
  const clean = sanitizeDiagnosticDetail(value);
  if (!clean) {
    return "";
  }

  const lower = clean.toLowerCase();
  if (
    lower.includes("cloudflare anti-bot challenge") ||
    lower.includes("source_protected_by_cloudflare_antibot_challenge")
  ) {
    return "Fonte protegida por desafio anti-bot (Cloudflare).";
  }

  return clean;
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

function getSniffedUrlPath(videoUrl) {
  try {
    return (new URL(videoUrl).pathname || "").toLowerCase();
  } catch {
    return String(videoUrl || "").toLowerCase().split("?")[0];
  }
}

function isBlockedSniffedUrl(videoUrl) {
  const href = String(videoUrl || "").toLowerCase();
  const path = getSniffedUrlPath(videoUrl);

  const blockedExtensions = [
    ".ts", ".m4s", ".js", ".css", ".vtt", ".srt", ".ass", ".json", ".xml",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".map"
  ];
  if (blockedExtensions.some((ext) => path.endsWith(ext))) {
    return true;
  }

  const blockedTokens = [
    "timedtext", "subtitle", "caption", "doubleclick", "googlesyndication", "googleads",
    "videojs.ads", "vast", "vmap", "adservice"
  ];
  if (blockedTokens.some((token) => href.includes(token))) {
    return true;
  }

  if ((path.includes("/segment") || path.includes("/chunk") || path.includes("/frag")) && !href.includes(".m3u8")) {
    return true;
  }

  return false;
}

function scoreSniffedUrl(videoUrl) {
  if (isBlockedSniffedUrl(videoUrl)) {
    return -1000;
  }

  const href = String(videoUrl || "").toLowerCase();
  const path = getSniffedUrlPath(videoUrl);
  let score = 0;

  if (href.includes("master.m3u8")) score += 400;
  if (href.includes(".m3u8")) score += 300;
  if (href.includes("playlist")) score += 140;
  if (href.includes("/manifest") || href.includes("manifest")) score += 140;
  if (href.includes(".mpd")) score += 220;
  if (href.includes(".mp4")) score += 160;
  if (href.includes("hls") || href.includes("dash")) score += 90;
  if (href.includes("token=") || href.includes("hash=") || href.includes("signature=") || href.includes("expires=")) score += 40;

  if ((path.includes("/segment") || path.includes("/chunk") || path.includes("/frag")) && !href.includes(".m3u8")) {
    score -= 500;
  }

  return score;
}

function rankSniffedUrls(urls) {
  const uniqueUrls = Array.from(new Set((urls || []).filter(Boolean).map((item) => String(item).trim())));

  const ranked = uniqueUrls
    .map((url) => ({
      url,
      score: scoreSniffedUrl(url),
    }))
    .filter((item) => item.score > -1000)
    .sort((a, b) => b.score - a.score);

  // Prioriza candidatos fortes, mas nao esconde completamente os demais.
  const strong = ranked.filter((item) => item.score > 0);
  return (strong.length > 0 ? strong : ranked).map((item) => item.url);
}

function isLikelyDirectMediaReference(videoUrl) {
  try {
    const parsed = new URL(videoUrl);
    const host = (parsed.hostname || "").toLowerCase();
    const path = (parsed.pathname || "").toLowerCase();
    const href = videoUrl.toLowerCase();

    if (
      href.includes(".m3u8") ||
      href.includes("playlist.m3u8") ||
      href.includes(".mp4")
    ) {
      return true;
    }

    if (
      path.includes("/embed") ||
      path.includes("/watch") ||
      path.includes("/videos/") ||
      path.includes("/status/")
    ) {
      return true;
    }

    const knownMediaHosts = [
      "pandavideo.com.br",
      "youtube.com",
      "youtu.be",
      "vimeo.com",
      "player.vimeo.com",
      "facebook.com",
      "fb.watch",
      "tiktok.com",
      "instagram.com",
      "twitter.com",
      "x.com",
    ];

    return knownMediaHosts.some((candidateHost) => {
      return host === candidateHost || host.endsWith(`.${candidateHost}`);
    });
  } catch {
    return false;
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

async function renderSniffedPanel() {
  try {
    const tab = await getActiveTab();
    if (!tab || !tab.id) return;

    chrome.runtime.sendMessage({ action: "getVideoUrls", tabId: tab.id }, (response) => {
      if (!chrome.runtime.lastError && response && response.urls && response.urls.length > 0) {
        const rankedUrls = rankSniffedUrls(response.urls);
        if (rankedUrls.length === 0) {
          ui.sniffedPanel.style.display = "none";
          ui.sniffedList.innerHTML = "";
          return;
        }

        ui.sniffedPanel.style.display = "block";
        ui.sniffedList.innerHTML = "";

        rankedUrls.slice(0, 25).forEach(url => {
          const li = document.createElement("li");
          li.style.marginBottom = "8px";
          li.style.wordBreak = "break-all";
          
          const alink = document.createElement("a");
          alink.href = "#";
          alink.textContent = url;
          alink.style.color = "#0052cc";
          alink.addEventListener("click", (e) => {
            e.preventDefault();
            ui.manualVideoReference.value = url;
            ui.manualVideoReference.style.backgroundColor = "#e6ffe6";
            setTimeout(() => { ui.manualVideoReference.style.backgroundColor = ""; }, 500);
            appendStatus("Referencia copiada com sucesso para o input! Clique em baixar.");
          });
          
          li.appendChild(alink);
          ui.sniffedList.appendChild(li);
        });
      }
    });

  } catch (err) {
    console.error("Falha ao abrir sniff panel", err);
  }
}

async function resolveVideoReference(tab) {
  if (!tab.id) {
    return { videoReference: tab.url, source: "tab-url", candidatesCount: 1 };
  }

  const tabProvider = inferProvider(tab.url);
  if (tabProvider !== "panda_video") {
    appendStatus(`Suporte nativo detectado (${tabProvider}). Usando URL da aba diretamente.`);
    return { videoReference: tab.url, source: "tab-url", candidatesCount: 1 };
  }

  try {
    const sniffedUrls = await new Promise((resolve) => {
      chrome.runtime.sendMessage({ action: "getVideoUrls", tabId: tab.id }, (response) => {
        if (chrome.runtime.lastError || !response || !response.urls) {
          resolve([]);
        } else {
          resolve(response.urls);
        }
      });
    });

    const rankedUrls = rankSniffedUrls(sniffedUrls);

    if (sniffedUrls.length > 0) {
      appendStatus(`Rede: ${sniffedUrls.length} URL(s) capturada(s), ${rankedUrls.length} candidata(s) apos filtro.`);
    }

    if (rankedUrls.length > 0) {
      const firstCandidate = rankedUrls[0];
      const firstScore = scoreSniffedUrl(firstCandidate);
      if (firstScore > 0 || isLikelyDirectMediaReference(firstCandidate)) {
        return {
          videoReference: firstCandidate,
          source: "network-sniffed",
          candidatesCount: rankedUrls.length,
        };
      }

      appendStatus("Rede: candidatos de baixa confianca; tentando fallback por DOM/iframe...");
    }

    const domCandidate = await extractVideoReferenceFromDom(tab.id);
    if (
      domCandidate &&
      domCandidate.url &&
      domCandidate.url !== tab.url &&
      !isBlockedSniffedUrl(domCandidate.url)
    ) {
      appendStatus(`DOM: candidato detectado via ${domCandidate.source} (${domCandidate.candidatesCount} opcoes).`);
      return {
        videoReference: domCandidate.url,
        source: "dom-fallback",
        candidatesCount: domCandidate.candidatesCount || 1,
      };
    }

    if (sniffedUrls.length > 0) {
      appendStatus("Rede: apenas fragmentos/ads detectados; ignorando links de baixa qualidade.");
    }
  } catch (err) {
    appendStatus(`Aviso: falha ao checar camada de rede (${err.message}).`);
  }

  // Ultimo fallback: URL da pagina.
  return { videoReference: tab.url, source: "tab-url", candidatesCount: 1 };
}

async function extractVideoReferenceFromDom(tabId) {
  const results = await new Promise((resolve, reject) => {
    chrome.scripting.executeScript(
      {
        target: { tabId },
        func: () => {
          const mediaHostHints = [
            "pandavideo.com.br",
            "youtube.com",
            "youtu.be",
            "vimeo.com",
            "tiktok.com",
            "instagram.com",
            "facebook.com",
            "twitter.com",
            "x.com",
          ];

          const socialHostHints = [
            "facebook.com",
            "twitter.com",
            "x.com",
            "linkedin.com",
            "whatsapp.com",
            "t.me",
            "pinterest.com",
          ];

          const isSocialHost = (host) =>
            socialHostHints.some((hint) => host === hint || host.endsWith(`.${hint}`));

          const extractShareTarget = (value) => {
            let parsed;
            try {
              parsed = new URL(value, window.location.href);
            } catch {
              return null;
            }

            const host = (parsed.hostname || "").toLowerCase();
            if (!isSocialHost(host)) {
              return null;
            }

            for (const key of ["u", "url", "target", "status", "text"]) {
              const candidate = parsed.searchParams.get(key);
              if (!candidate) {
                continue;
              }

              try {
                const decoded = decodeURIComponent(candidate);
                const absolute = new URL(decoded, window.location.href).toString();
                if (/^https?:\/\//i.test(absolute) && absolute !== parsed.toString()) {
                  return absolute;
                }
              } catch {
                continue;
              }
            }

            return null;
          };

          const isShareOrRedirectUrl = (value) => {
            let parsed;
            try {
              parsed = new URL(value, window.location.href);
            } catch {
              return false;
            }

            const host = (parsed.hostname || "").toLowerCase();
            const path = (parsed.pathname || "").toLowerCase();
            const hasTargetUrlParam =
              parsed.searchParams.has("u") ||
              parsed.searchParams.has("url") ||
              parsed.searchParams.has("target");

            const hasShareTextParam =
              parsed.searchParams.has("status") ||
              parsed.searchParams.has("text");

            if ((host === "x.com" || host.endsWith(".x.com")) && parsed.searchParams.has("logout")) {
              return true;
            }

            if (host.includes("facebook.com") && path.includes("/sharer")) {
              return true;
            }
            if ((host.includes("twitter.com") || host === "x.com" || host.endsWith(".x.com")) && path.includes("/intent/")) {
              return true;
            }
            if ((host.includes("twitter.com") || host === "x.com" || host.endsWith(".x.com")) && (path === "/" || path === "/home" || path.startsWith("/home/")) && hasShareTextParam) {
              return true;
            }
            if (host.includes("linkedin.com") && path.includes("/share")) {
              return true;
            }
            if (host.includes("whatsapp.com") && (path.includes("/send") || path.includes("/share"))) {
              return true;
            }
            if (host.includes("t.me") && path.includes("/share")) {
              return true;
            }
            if (host.includes("pinterest.com") && path.includes("/pin/create")) {
              return true;
            }

            if (hasTargetUrlParam && (host.includes("facebook.com") || host.includes("twitter.com") || host.includes("x.com") || host.includes("linkedin.com") || host.includes("whatsapp.com"))) {
              return true;
            }

            if (hasShareTextParam && (host.includes("twitter.com") || host.includes("x.com") || host.includes("facebook.com"))) {
              return true;
            }

            return false;
          };

          const likelyMedia = (value) => {
            const lower = value.toLowerCase();
            let parsed;
            try {
              parsed = new URL(value, window.location.href);
            } catch {
              return false;
            }

            const host = (parsed.hostname || "").toLowerCase();
            const path = (parsed.pathname || "").toLowerCase();
            const currentHost = (window.location.hostname || "").toLowerCase();

            if (host.includes("facebook.com") || host.includes("twitter.com") || host === "x.com" || host.endsWith(".x.com")) {
              return (
                lower.includes(".m3u8") ||
                lower.includes(".mp4") ||
                path.includes("/video") ||
                path.includes("/videos/") ||
                path.includes("/watch") ||
                path.includes("/status/") ||
                path.includes("/embed")
              );
            }

            if (host === currentHost || host.endsWith(`.${currentHost}`)) {
              if (
                lower.includes(".m3u8") ||
                lower.includes(".mp4") ||
                lower.includes("playlist") ||
                lower.includes("manifest") ||
                path.includes("/player") ||
                path.includes("/embed") ||
                path.includes("/stream")
              ) {
                return true;
              }
            }

            return (
              mediaHostHints.some((hint) => lower.includes(hint)) ||
              lower.includes(".m3u8") ||
              lower.includes(".mp4") ||
              lower.includes("playlist")
            );
          };

          const scoreCandidate = (url, source) => {
            const lower = url.toLowerCase();
            let score = 0;

            if (lower.includes("pandavideo.com.br")) {
              score += 120;
            }
            if (lower.includes("youtube.com") || lower.includes("youtu.be")) {
              score += 100;
            }
            if (lower.includes(".m3u8") || lower.includes("playlist.m3u8")) {
              score += 160;
            }
            if (lower.includes(".mp4")) {
              score += 130;
            }
            if (lower.includes("/embed")) {
              score += 40;
            }
            if (source.startsWith("iframe")) {
              score += 25;
            }
            if (source.startsWith("video") || source.startsWith("source")) {
              score += 35;
            }
            if (url === window.location.href) {
              score -= 40;
            }

            return score;
          };

          const seen = new Set();
          const candidates = [];
          const addCandidate = (rawValue, source) => {
            if (!rawValue) {
              return;
            }

            const normalized = String(rawValue).trim().replace(/&amp;/gi, "&");
            if (!normalized) {
              return;
            }

            let absolute;
            try {
              absolute = new URL(normalized, window.location.href).toString();
            } catch {
              return;
            }

            if (!/^https?:\/\//i.test(absolute)) {
              return;
            }

            if (isShareOrRedirectUrl(absolute)) {
              const shareTarget = extractShareTarget(absolute);
              if (shareTarget && shareTarget !== absolute) {
                addCandidate(shareTarget, `${source}.share-target`);
              }
              return;
            }

            if (!likelyMedia(absolute)) {
              return;
            }

            if (seen.has(absolute)) {
              return;
            }

            seen.add(absolute);
            candidates.push({
              url: absolute,
              source,
              score: scoreCandidate(absolute, source),
            });
          };

          addCandidate(window.location.href, "tab.url");

          for (const iframe of document.querySelectorAll("iframe[src]")) {
            addCandidate(iframe.getAttribute("src"), "iframe.src");
          }

          for (const video of document.querySelectorAll("video[src]")) {
            addCandidate(video.getAttribute("src"), "video.src");
          }

          for (const source of document.querySelectorAll("video source[src], source[src]")) {
            addCandidate(source.getAttribute("src"), "source.src");
          }

          for (const node of document.querySelectorAll("[data-src], [data-url], [data-video], [data-iframe]")) {
            addCandidate(node.getAttribute("data-src"), "data-src");
            addCandidate(node.getAttribute("data-url"), "data-url");
            addCandidate(node.getAttribute("data-video"), "data-video");
            addCandidate(node.getAttribute("data-iframe"), "data-iframe");
          }

          for (const anchor of document.querySelectorAll("a[href]")) {
            addCandidate(anchor.getAttribute("href"), "a.href");
          }

          const html = document.documentElement ? document.documentElement.innerHTML : "";
          const regex = /https?:\/\/[^\s"'<>]+/g;
          for (const match of html.match(regex) || []) {
            addCandidate(match, "html.regex");
          }

          if (!candidates.length) {
            return {
              url: null,
              source: "none",
              candidatesCount: 0,
            };
          }

          candidates.sort((a, b) => b.score - a.score);
          const selected = candidates[0];
          return {
            url: selected.url,
            source: selected.source,
            candidatesCount: candidates.length,
          };
        },
      },
      (executionResults) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
          return;
        }
        resolve(executionResults || []);
      }
    );
  });

  if (!results.length || !results[0].result) {
    return null;
  }

  return results[0].result;
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

  let response;
  try {
    response = await fetchWithTimeout(
      url,
      {
        method,
        headers,
        body: body === null ? undefined : JSON.stringify(body),
      },
      settings.requestTimeoutSeconds * 1000
    );
  } catch (error) {
    if (error && error.message === "Timeout da requisicao HTTP.") {
      throw error;
    }
    throw new Error(
      `Falha de conexao com a API em ${url}. Verifique se a API esta em execucao.`
    );
  }

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
    manualVideoReference: ui.manualVideoReference.value.trim(),
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
  ui.manualVideoReference.value = settings.manualVideoReference || "";
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
