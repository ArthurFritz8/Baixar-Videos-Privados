// background.js

function isMediaUrl(url, type) {
    if (type === "media") return true;
    const lowerUrl = url.toLowerCase();
    if (lowerUrl.includes(".m3u8") || lowerUrl.includes(".mp4") || lowerUrl.includes(".ts") || lowerUrl.includes(".m4a") || lowerUrl.includes("/manifest")) return true;
    
    // Captura absurdamente agressiva para sites obscuros: pega todo fetch/xhr que retorne dados binarios na querystring, ou contenha "player"
    if (type === "xmlhttprequest" || type === "fetch" || type === "other") {
        if (lowerUrl.includes("stream") || lowerUrl.includes("video") || lowerUrl.includes("playlist") || lowerUrl.includes("player")) return true;
        // Pega tambem URLs com hls, dash...
        if (lowerUrl.includes("hls") || lowerUrl.includes("dash")) return true;
    }
    
    // As vezes sites piratas instanciam o arquivo em Object/Blob ou usam subresource. Nao temos acesso direto a Blob pelo webRequest, mas tentemos pegar o ping
    if (type === "sub_frame" && lowerUrl.includes("player")) return true;
    
    return false;
}

function saveUrlForTab(tabId, url) {
    if (tabId < 0) return;
    chrome.storage.local.get(["videoUrls"], (res) => {
        let vUrls = res.videoUrls || {};
        if (!vUrls[tabId]) vUrls[tabId] = [];
        
        // Mantém apenas os ultimos 30 links agora q seremos mais agressivos
        if (!vUrls[tabId].includes(url)) {
            vUrls[tabId].push(url);
            if (vUrls[tabId].length > 30) {
                vUrls[tabId].shift(); // Remove oldest
            }
            chrome.storage.local.set({ videoUrls: vUrls });
        }
    });
}

chrome.webRequest.onBeforeRequest.addListener(
    function(details) {
        if (isMediaUrl(details.url, details.type)) {
            // Ignorar tráfego de imagens ou scripts aleatorios que tentam fingir ser media
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
    chrome.storage.local.get(["videoUrls"], (res) => {
        let vUrls = res.videoUrls || {};
        if (vUrls[tabId]) {
            delete vUrls[tabId];
            chrome.storage.local.set({ videoUrls: vUrls });
        }
    });
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
    if (changeInfo.url) { // Navegou para nova página na mesma aba
        chrome.storage.local.get(["videoUrls"], (res) => {
            let vUrls = res.videoUrls || {};
            if (vUrls[tabId]) {
                delete vUrls[tabId];
                chrome.storage.local.set({ videoUrls: vUrls });
            }
        });
    }
});
