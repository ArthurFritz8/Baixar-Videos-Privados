// background.js

function isMediaUrl(url, type) {
    const lowerUrl = url.toLowerCase();
    
    // Extrai apenas o caminho principal da URL (sem query string par incertezas como .js&xyz=)
    const urlPath = lowerUrl.split("?")[0];

    // Bloqueia com urgencia qualquer script js, css, legendas e os minusculos arquivos TS (.ts) que frustram downloads
    if (urlPath.endsWith(".ts") || urlPath.endsWith(".js") || urlPath.endsWith(".css") || urlPath.endsWith(".vtt") || urlPath.endsWith(".png") || urlPath.endsWith(".jpg")) {
        return false;
    }

    if (type === "media") return true;
    
    // Master playlists
    if (lowerUrl.includes(".m3u8") || lowerUrl.includes(".mp4") || lowerUrl.includes(".m4a") || lowerUrl.includes("/manifest")) return true;
    
    // Captura toda query string suspeita
    if (lowerUrl.includes("token=") || lowerUrl.includes("hash=")) {
        if (type !== "image" && type !== "stylesheet" && type !== "font" && type !== "script") {
            return true;
        }
    }
    
    // As vezes o videojas/jwplayer carrega o m3u8 internamente como fetch
    if (type === "xmlhttprequest" || type === "fetch" || type === "other" || type === "sub_frame") {
        if (lowerUrl.includes("stream") || lowerUrl.includes("video") || lowerUrl.includes("playlist") || lowerUrl.includes("player")) {
            return true;
        }
        if (lowerUrl.includes("hls") || lowerUrl.includes("dash")) {
            return true;
        }
    }
    
    return false;
}

function saveUrlForTab(tabId, url) {
    if (tabId < 0) return;
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
