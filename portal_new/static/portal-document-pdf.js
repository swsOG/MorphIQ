/**
 * MorphIQ — PDF.js canvas preview (fit page in panel, resize-aware).
 * Uses min(width-scale, height-scale) so whole page is visible — not width-only zoom.
 * Requires pdfjsLib on window (loaded from document_view.html).
 */
(function (global) {
    "use strict";

    function debounce(fn, ms) {
        let t = null;
        return function debounced() {
            if (t) clearTimeout(t);
            const args = arguments;
            t = setTimeout(function () {
                fn.apply(null, args);
            }, ms);
        };
    }

    /**
     * @param {HTMLElement} rootEl — cleared and receives the scroll area
     * @param {string} pdfUrl — same-origin URL (cookies via withCredentials)
     */
    function mountPortalPdfViewer(rootEl, pdfUrl) {
        if (!rootEl || !pdfUrl) return;
        rootEl.innerHTML = "";
        const scroll = document.createElement("div");
        scroll.className = "document-view-pdf-scroll";
        rootEl.appendChild(scroll);

        if (!global.pdfjsLib) {
            scroll.innerHTML =
                '<div class="document-view-pdf-missing"><span>PDF preview unavailable</span></div>';
            return;
        }

        let pdfDoc = null;
        let renderToken = 0;
        let resizeObs = null;

        function measureViewportBox() {
            const pad = 24;
            const sr = scroll.getBoundingClientRect();
            let cw = Math.max(120, sr.width - pad);
            let ch = Math.max(0, sr.height - pad);
            if (ch < 64) {
                const pane = rootEl.closest(".document-view-pdf");
                if (pane) {
                    const pr = pane.getBoundingClientRect();
                    ch = Math.max(120, pr.height - pad);
                }
            }
            if (ch < 64) {
                ch = Math.max(200, window.innerHeight * 0.55);
            }
            return { cw, ch };
        }

        async function render() {
            const token = ++renderToken;
            if (!pdfDoc) return;
            await new Promise(function (r) {
                requestAnimationFrame(function () {
                    requestAnimationFrame(r);
                });
            });
            if (token !== renderToken) return;

            const box = measureViewportBox();
            scroll.innerHTML = "";
            for (let pageNum = 1; pageNum <= pdfDoc.numPages; pageNum++) {
                if (token !== renderToken) return;
                const page = await pdfDoc.getPage(pageNum);
                if (token !== renderToken) return;
                const vp1 = page.getViewport({ scale: 1 });
                const scaleW = box.cw / vp1.width;
                const scaleH = box.ch / vp1.height;
                const scale = Math.min(scaleW, scaleH);
                const viewport = page.getViewport({ scale });
                const canvas = document.createElement("canvas");
                const ctx = canvas.getContext("2d");
                if (!ctx) continue;
                canvas.width = viewport.width;
                canvas.height = viewport.height;
                canvas.className = "document-view-pdf-page-canvas";
                const wrap = document.createElement("div");
                wrap.className = "document-view-pdf-page";
                wrap.appendChild(canvas);
                scroll.appendChild(wrap);
                await page.render({ canvasContext: ctx, viewport: viewport }).promise;
            }
        }

        const loadingTask = global.pdfjsLib.getDocument({
            url: pdfUrl,
            withCredentials: true,
        });

        loadingTask.promise
            .then(function (pdf) {
                pdfDoc = pdf;
                return render();
            })
            .then(function () {
                if (resizeObs) resizeObs.disconnect();
                resizeObs = new ResizeObserver(debounce(render, 120));
                resizeObs.observe(scroll);
                const pane = rootEl.closest(".document-view-pdf");
                if (pane) resizeObs.observe(pane);
            })
            .catch(function () {
                rootEl.innerHTML =
                    '<div class="document-view-pdf-missing"><span>Could not load PDF preview</span></div>';
            });
    }

    global.MorphIQPortalPdf = { mount: mountPortalPdfViewer };
})(typeof window !== "undefined" ? window : this);
