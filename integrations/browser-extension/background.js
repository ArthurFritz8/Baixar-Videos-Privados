// background.js

function isMediaUrl(url, type) {
    if (type === "media") return true;
    if (url.includes(".m3u8") || url.includes(".mp4") || url.includes(".ts") || url.includes(".m4a") || url.includes("/manifest")) return true;
    return false;
}

function saveUrlForTab(tabId, url) {
    if (tabId < 0) return;
    chrome.storage.local.get(["videoUrls"], (res) => {
        let vUrls = res.videoUrls || {};
        if (!vUrls[tabId]) vUrls[tabId] = [];
        
        // Mantém apenas os ultimos 20 links pra nao explodir storage
        if (!vUrls[tabId].includes(url)) {
            vUrls[tabId].push(url);
            if (vUrls[tabId].length > 20) {
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
