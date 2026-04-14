// background.js

function getUrlPath(url) {
    try {
        return new URL(url).pathname.toLowerCase();
    } catch {
        return String(url || "").toLowerCase().split("?")[0];
    }
}

function isBlockedResourceUrl(url) {
    const lowerUrl = String(url || "").toLowerCase();
    const path = getUrlPath(url);

    const blockedExtensions = [
        ".ts", ".m4s", ".js", ".css", ".vtt", ".srt", ".ass", ".json", ".xml",
        ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".map"
    ];
    if (blockedExtensions.some((ext) => path.endsWith(ext))) {
        return true;
    }

    const blockedTokens = [
        "timedtext", "subtitle", "caption", "doubleclick", "googlesyndication", "googleads",
        "videojs.ads", "ima", "vast", "vmap", "adservice", "analytics", "tracker"
    ];
    if (blockedTokens.some((token) => lowerUrl.includes(token))) {
        return true;
    }

    // Segmentos e fragmentos sao ruidosos para lista manual.
    if ((path.includes("/segment") || path.includes("/chunk") || path.includes("/frag")) && !path.endsWith(".m3u8")) {
        return true;
    }

    return false;
}

function isMediaUrl(url, type) {
    const lowerUrl = String(url || "").toLowerCase();

    if (isBlockedResourceUrl(url)) {
        return false;
    }

    if (type === "media") return true;

    // Master playlists e midia direta
    if (lowerUrl.includes(".m3u8") || lowerUrl.includes(".mp4") || lowerUrl.includes(".m4a") || lowerUrl.includes(".mpd") || lowerUrl.includes("/manifest")) return true;

    // Captura query string tipica de links assinados de video
    if (lowerUrl.includes("token=") || lowerUrl.includes("hash=") || lowerUrl.includes("signature=") || lowerUrl.includes("expires=")) {
        if (type !== "image" && type !== "stylesheet" && type !== "font" && type !== "script") {
            return true;
        }
    }

    // Alguns players carregam via XHR/fetch sem extensao explicita.
    if (type === "xmlhttprequest" || type === "fetch" || type === "other" || type === "sub_frame") {
        if (lowerUrl.includes("stream") || lowerUrl.includes("video") || lowerUrl.includes("playlist") || lowerUrl.includes("player") || lowerUrl.includes("manifest") || lowerUrl.includes("hls") || lowerUrl.includes("dash")) {
            return true;
        }
    }

    return false;
}

function saveUrlForTab(tabId, url) {
    if (tabId < 0) return;
    if (isBlockedResourceUrl(url)) return;
    chrome.storage.local.get(["videoUrls"], (res) => {
        let vUrls = res.videoUrls || {};
        if (!vUrls[tabId]) vUrls[tabId] = [];
        
        // Mantém apenas os ultimos 40 links 
        if (!vUrls[tabId].includes(url)) {
            vUrls[tabId].push(url);
            if (vUrls[tabId].length > 40) {
                vUrls[tabId].shift(); // Remove oldest
            }
            chrome.storage.local.set({ videoUrls: vUrls });
        }
    });
}

function clearUrlsForTab(tabId) {
    chrome.storage.local.get(["videoUrls"], (res) => {
        const vUrls = res.videoUrls || {};
        if (!vUrls[tabId]) {
            return;
        }

        delete vUrls[tabId];
        chrome.storage.local.set({ videoUrls: vUrls });
    });
}

chrome.webRequest.onBeforeRequest.addListener(
    function(details) {
        if (isMediaUrl(details.url, details.type)) {
            // Ignorar script para nao floodar
            if (details.type !== "image" && details.type !== "script") {
               saveUrlForTab(details.tabId, details.url);
            }
        }
    },
    { urls: ["<all_urls>"] },
    []
);

// Fallback extra pra headers
chrome.webRequest.onHeadersReceived.addListener(
    function(details) {
        if (isMediaUrl(details.url, details.type)) {
            saveUrlForTab(details.tabId, details.url);
        }
    },
    { urls: ["<all_urls>"] },
    ["responseHeaders"]
);

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "getVideoUrls") {
        const tabId = request.tabId;
        chrome.storage.local.get(["videoUrls"], (res) => {
            const vUrls = res.videoUrls || {};
            sendResponse({ urls: vUrls[tabId] || [] });
        });
        return true; // async response
    } else if (request.action === "clearVideoUrls") {
        const tabId = request.tabId;
        chrome.storage.local.get(["videoUrls"], (res) => {
            const vUrls = res.videoUrls || {};
            if (vUrls[tabId]) {
                delete vUrls[tabId];
                chrome.storage.local.set({ videoUrls: vUrls }, () => {
                    sendResponse({ success: true });
                });
            } else {
                sendResponse({ success: true });
            }
        });
        return true;
    }
});

chrome.tabs.onRemoved.addListener((tabId) => {
    clearUrlsForTab(tabId);
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
    // Limpa cache em nova navegacao e tambem no reload (status loading), evitando lixos antigos.
    if (changeInfo.url || changeInfo.status === "loading") {
        clearUrlsForTab(tabId);
    }
});
