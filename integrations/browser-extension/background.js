// background.js

let videoUrls = {};

chrome.webRequest.onHeadersReceived.addListener(
    function(details) {
        if (details.type === "media" || details.url.includes(".m3u8") || details.url.includes(".mp4")) {
            const tabId = details.tabId;
            if (tabId >= 0) {
                if (!videoUrls[tabId]) {
                    videoUrls[tabId] = new Set();
                }
                videoUrls[tabId].add(details.url);
            }
        }
    },
    { urls: ["<all_urls>"] },
    ["responseHeaders"]
);

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "getVideoUrls") {
        const tabId = request.tabId;
        const urls = videoUrls[tabId] ? Array.from(videoUrls[tabId]) : [];
        sendResponse({ urls: urls });
    } else if (request.action === "clearVideoUrls") {
        const tabId = request.tabId;
        if (videoUrls[tabId]) {
            delete videoUrls[tabId];
        }
        sendResponse({ success: true });
    }
    return true;
});

chrome.tabs.onRemoved.addListener((tabId) => {
    if (videoUrls[tabId]) {
        delete videoUrls[tabId];
    }
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
    if (changeInfo.url) {
        if (videoUrls[tabId]) {
            delete videoUrls[tabId];
        }
    }
});
