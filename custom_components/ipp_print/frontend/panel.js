const STYLE = `
  :host { display: block; }
  .page {
    display: grid;
    grid-template-columns: minmax(320px, 420px) 1fr;
    gap: 16px;
    padding: 8px 8px 32px;
    color: var(--primary-text-color, #212121);
    font-family: var(--paper-font-body1_-_font-family, inherit);
  }
  @media (max-width: 800px) { .page { grid-template-columns: 1fr; } }
  .card {
    background: var(--card-background-color, #fff);
    border-radius: var(--ha-card-border-radius, 12px);
    box-shadow: var(--ha-card-box-shadow, 0 1px 3px rgba(0,0,0,.12));
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  h2 { margin: 0; font-size: 1.25rem; font-weight: 500; }
  .head { display: flex; flex-direction: column; gap: 2px; }
  .muted { color: var(--secondary-text-color, #727272); font-size: .875rem; }
  .drop {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    gap: 4px; padding: 22px 12px; cursor: pointer; text-align: center;
    border: 2px dashed var(--divider-color, #e0e0e0); border-radius: 10px;
    transition: border-color .15s, background .15s;
  }
  .drop:hover, .drop.over { border-color: var(--primary-color, #03a9f4); background: rgba(3,169,244,.06); }
  .drop-title { font-weight: 500; }
  .drop.filled { border-style: solid; }
  .row { display: flex; gap: 10px; align-items: flex-end; flex-wrap: wrap; }
  .row > * { flex: 1 1 0; min-width: 0; }
  .row.actions > .muted { flex: 2 1 120px; }
  .field-label { display: flex; flex-direction: column; gap: 4px; font-size: .8rem; color: var(--secondary-text-color, #727272); }
  .field {
    font: inherit; color: var(--primary-text-color, #212121);
    background: var(--card-background-color, #fff);
    border: 1px solid var(--divider-color, #e0e0e0);
    border-radius: 8px; padding: 9px 10px; min-width: 0;
  }
  .field:focus { outline: 2px solid var(--primary-color, #03a9f4); outline-offset: 1px; }
  .btn {
    font: inherit; cursor: pointer; padding: 9px 16px; border-radius: 8px;
    border: 1px solid var(--primary-color, #03a9f4);
    background: transparent; color: var(--primary-color, #03a9f4);
    flex: 0 0 auto;
  }
  .btn:hover:not(:disabled) { background: rgba(3,169,244,.1); }
  .btn.primary { background: var(--primary-color, #03a9f4); color: var(--text-primary-color, #fff); }
  .btn.primary:hover:not(:disabled) { filter: brightness(1.08); }
  .btn:disabled { opacity: .45; cursor: default; }
  .btn.icon { width: 36px; height: 36px; padding: 0; font-size: 1.1rem; line-height: 1; }
  .switch { display: flex; align-items: center; gap: 8px; font-size: .9rem; flex: 0 0 auto; padding-bottom: 8px; }
  .preview { align-items: center; }
  .sheet-wrap { display: flex; justify-content: center; width: 100%; }
  .sheet {
    width: 100%; max-width: 520px; aspect-ratio: 210 / 297;
    background: #fff; border: 1px solid var(--divider-color, #e0e0e0);
    box-shadow: 0 2px 10px rgba(0,0,0,.14);
    display: flex; align-items: center; justify-content: center; overflow: hidden;
  }
  .sheet img { width: 100%; height: 100%; object-fit: contain; display: block; }
  .sheet img[hidden] { display: none; }
  .sheet.empty::after {
    content: "Vorschau"; color: #bbb; font-size: .9rem;
  }
  .pager { display: flex; align-items: center; gap: 12px; }
  .pages-info { margin: -6px 0 0; min-height: 1.1em; }
  .error { color: var(--error-color, #db4437); }
`;

const TEMPLATE = `
  <div class="page">
    <section class="card">
      <div class="head">
        <h2>Drucken</h2>
        <span id="printer" class="muted">Drucker wird geladen …</span>
      </div>
      <label class="drop" id="drop">
        <input id="file" type="file" accept="application/pdf,image/jpeg,image/png" hidden>
        <span class="drop-title" id="dropTitle">PDF, JPG oder PNG hierher ziehen</span>
        <span class="muted">oder klicken zum Auswählen</span>
      </label>
      <div class="row">
        <input id="url" class="field" type="url" placeholder="… oder URL zu PDF/Bild einfügen">
        <button id="load" class="btn">Laden</button>
      </div>
      <div class="row">
        <label class="field-label">Papier<select id="media" class="field"></select></label>
        <label class="field-label">Ausrichtung
          <select id="orient" class="field">
            <option value="portrait">Hochformat</option>
            <option value="landscape">Querformat</option>
          </select>
        </label>
      </div>
      <div class="row">
        <label class="field-label">Anpassen
          <select id="mode" class="field">
            <option value="fit">Einpassen</option>
            <option value="fill">Ausfüllen (beschneiden)</option>
          </select>
        </label>
        <label class="switch"><input id="color" type="checkbox" checked> Farbe</label>
      </div>
      <div class="row">
        <label class="field-label">Seiten
          <input id="pages" class="field" type="text" placeholder="alle · 1,3 · 1-3 · gerade">
        </label>
        <label class="field-label">Druck
          <select id="duplex" class="field">
            <option value="off">Einseitig</option>
            <option value="manual">Beidseitig (manuell)</option>
          </select>
        </label>
      </div>
      <p id="pageInfo" class="muted pages-info"></p>
      <div class="row actions">
        <button id="print" class="btn primary" disabled>Drucken</button>
        <button id="reset" class="btn" hidden>Zurücksetzen</button>
        <span id="status" class="muted"></span>
      </div>
    </section>
    <section class="card preview">
      <div class="sheet-wrap">
        <div class="sheet empty" id="sheet"><img id="preview" alt="" hidden></div>
      </div>
      <div class="pager">
        <button id="prev" class="btn icon" disabled>‹</button>
        <span id="pageno" class="muted">Kein Dokument</span>
        <button id="next" class="btn icon" disabled>›</button>
      </div>
    </section>
  </div>
`;

class IppPrintPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.shadowRoot.innerHTML = `<style>${STYLE}</style>${TEMPLATE}`;
    const $ = (id) => this.shadowRoot.getElementById(id);
    this._els = {
      drop: $("drop"), file: $("file"), dropTitle: $("dropTitle"),
      url: $("url"), load: $("load"), media: $("media"), orient: $("orient"),
      mode: $("mode"), color: $("color"), print: $("print"),
      pages: $("pages"), duplex: $("duplex"), pageInfo: $("pageInfo"), reset: $("reset"),
      status: $("status"), printer: $("printer"), sheet: $("sheet"),
      preview: $("preview"), prev: $("prev"), next: $("next"), pageno: $("pageno"),
    };
    this._source = null;
    this._page = 0;
    this._previewUrl = null;
    this._info = null;
    this._selection = null;
    this._duplexStage = null;
    this._wire();
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) this._loadInfo();
  }

  set panel(panel) {
    this._panel = panel;
  }

  _wire() {
    const e = this._els;
    e.drop.addEventListener("click", () => e.file.click());
    e.file.addEventListener("change", () => {
      if (e.file.files[0]) this._upload(e.file.files[0]);
    });
    for (const type of ["dragenter", "dragover"]) {
      e.drop.addEventListener(type, (ev) => {
        ev.preventDefault();
        e.drop.classList.add("over");
      });
    }
    for (const type of ["dragleave", "drop"]) {
      e.drop.addEventListener(type, () => e.drop.classList.remove("over"));
    }
    e.drop.addEventListener("drop", (ev) => {
      ev.preventDefault();
      if (ev.dataTransfer.files[0]) this._upload(ev.dataTransfer.files[0]);
    });
    e.load.addEventListener("click", () => this._loadUrl());
    e.url.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter") this._loadUrl();
    });
    for (const id of ["media", "orient", "mode", "color"]) {
      e[id].addEventListener("change", () => this._schedulePreview());
    }
    e.prev.addEventListener("click", () => this._go(-1));
    e.next.addEventListener("click", () => this._go(1));
    e.print.addEventListener("click", () => this._print());
    e.reset.addEventListener("click", () => {
      this._resetDuplex();
      this._updateSelection();
      this._setStatus("");
    });
    e.pages.addEventListener("input", () => {
      this._resetDuplex();
      clearTimeout(this._selectionTimer);
      this._selectionTimer = setTimeout(() => this._updateSelection(), 250);
    });
    e.duplex.addEventListener("change", () => {
      this._resetDuplex();
      this._updateSelection();
    });
  }

  async _fetch(path, init) {
    const response = await this._hass.fetchWithAuth(path, init);
    if (!response.ok) {
      let message = `${response.status} ${response.statusText}`;
      try {
        const body = await response.json();
        if (body && body.error) message = body.error;
      } catch (err) {
        /* not JSON – keep the status text */
      }
      throw new Error(message);
    }
    return response;
  }

  _setStatus(text, isError = false) {
    const el = this._els.status;
    el.textContent = text || "";
    el.classList.toggle("error", isError);
  }

  async _loadInfo() {
    try {
      const response = await this._fetch("/api/ipp_print/info");
      this._info = await response.json();
    } catch (err) {
      this._els.printer.textContent = err.message;
      this._els.printer.classList.add("error");
      return;
    }
    const info = this._info;
    this._els.printer.textContent = `${info.model} · ${this._stateLabel(info.state)}`;
    this._fillMedia(info.media, info.default_media);
  }

  _stateLabel(state) {
    return { idle: "bereit", processing: "druckt", stopped: "angehalten" }[state] || state;
  }

  _fillMedia(options, selected) {
    const select = this._els.media;
    select.innerHTML = "";
    for (const option of options || []) {
      const el = document.createElement("option");
      el.value = option.key;
      el.textContent = option.label;
      el.dataset.ratio = `${option.width_mm} / ${option.height_mm}`;
      if (option.key === selected) el.selected = true;
      select.appendChild(el);
    }
    this._updateSheet();
  }

  _updateSheet() {
    const option = this._els.media.selectedOptions[0];
    const landscape = this._els.orient.value === "landscape";
    if (!option) return;
    let [width, height] = option.dataset.ratio.split(" / ");
    if (landscape) [width, height] = [height, width];
    this._els.sheet.style.aspectRatio = `${width} / ${height}`;
  }

  _options() {
    return {
      media: this._els.media.value,
      landscape: this._els.orient.value === "landscape",
      mode: this._els.mode.value,
      color: this._els.color.checked,
    };
  }

  async _upload(file) {
    if (file.size > 25 * 1024 * 1024) {
      this._setStatus("Die Datei ist größer als 25 MB.", true);
      return;
    }
    this._setStatus("Datei wird geladen …");
    try {
      const response = await this._fetch(
        `/api/ipp_print/source?name=${encodeURIComponent(file.name)}`,
        {
          method: "POST",
          headers: { "Content-Type": file.type || "application/octet-stream" },
          body: file,
        },
      );
      this._useSource(await response.json());
    } catch (err) {
      this._setStatus(err.message, true);
    }
  }

  async _loadUrl() {
    const url = this._els.url.value.trim();
    if (!url) return;
    this._setStatus("URL wird geladen …");
    try {
      const response = await this._fetch(
        `/api/ipp_print/source?url=${encodeURIComponent(url)}`,
        { method: "POST" },
      );
      this._useSource(await response.json());
    } catch (err) {
      this._setStatus(err.message, true);
    }
  }

  _useSource(source) {
    this._source = source;
    this._page = 0;
    this._resetDuplex();
    this._els.dropTitle.textContent = source.name;
    this._els.drop.classList.add("filled");
    this._els.print.disabled = false;
    this._setStatus(`${source.pages} Seite${source.pages === 1 ? "" : "n"}`);
    this._updatePager();
    this._loadPreview();
    this._updateSelection();
  }

  _resetDuplex() {
    this._duplexStage = null;
    this._els.print.textContent = "Drucken";
    this._els.reset.hidden = true;
  }

  async _updateSelection() {
    const e = this._els;
    if (!this._source) {
      e.pageInfo.textContent = "";
      return;
    }
    const duplex = e.duplex.value === "manual";
    const query = new URLSearchParams({
      id: this._source.id,
      pages: duplex ? "ungerade" : e.pages.value.trim(),
    });
    try {
      const response = await this._fetch(`/api/ipp_print/pages?${query}`);
      const result = await response.json();
      const shown = result.pages.length > 12
        ? `${result.pages.slice(0, 12).join(", ")} …`
        : result.pages.join(", ");
      e.pageInfo.classList.remove("error");
      e.pageInfo.textContent = duplex
        ? `Beidseitig: ${result.count} Blatt, erst Vorderseiten (${shown}), dann Rückseiten`
        : `Druckt ${result.count} Seite${result.count === 1 ? "" : "n"}: ${shown}`;
      e.print.disabled = false;
    } catch (err) {
      e.pageInfo.classList.add("error");
      e.pageInfo.textContent = err.message;
      e.print.disabled = true;
    }
  }

  _go(delta) {
    if (!this._source) return;
    const next = this._page + delta;
    if (next < 0 || next >= this._source.pages) return;
    this._page = next;
    this._updatePager();
    this._loadPreview();
  }

  _updatePager() {
    const e = this._els;
    if (!this._source) {
      e.pageno.textContent = "Kein Dokument";
      e.prev.disabled = true;
      e.next.disabled = true;
      return;
    }
    e.pageno.textContent = `Seite ${this._page + 1} von ${this._source.pages}`;
    e.prev.disabled = this._page <= 0;
    e.next.disabled = this._page >= this._source.pages - 1;
  }

  _schedulePreview() {
    this._updateSheet();
    clearTimeout(this._timer);
    this._timer = setTimeout(() => this._loadPreview(), 150);
  }

  async _loadPreview() {
    if (!this._source) return;
    const opts = this._options();
    const query = new URLSearchParams({
      id: this._source.id,
      page: String(this._page),
      media: opts.media,
      landscape: opts.landscape ? "1" : "0",
      mode: opts.mode,
      color: opts.color ? "1" : "0",
    });
    try {
      const response = await this._fetch(`/api/ipp_print/preview?${query}`);
      const blob = await response.blob();
      if (this._previewUrl) URL.revokeObjectURL(this._previewUrl);
      this._previewUrl = URL.createObjectURL(blob);
      this._els.preview.src = this._previewUrl;
      this._els.preview.hidden = false;
      this._els.sheet.classList.remove("empty");
    } catch (err) {
      this._setStatus(err.message, true);
    }
  }

  async _print() {
    if (!this._source) return;
    const e = this._els;
    const opts = this._options();
    const duplex = e.duplex.value === "manual";
    let pages = e.pages.value.trim();
    let reverse = false;
    if (duplex) {
      if (this._duplexStage === "back") {
        pages = "gerade";
        reverse = true;
      } else {
        pages = "ungerade";
      }
    }
    e.print.disabled = true;
    this._setStatus("Wird gedruckt …");
    try {
      const response = await this._fetch("/api/ipp_print/print", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: this._source.id, ...opts, pages, reverse }),
      });
      const result = await response.json();
      if (duplex && this._duplexStage !== "back") {
        this._duplexStage = "back";
        e.print.textContent = "Rückseiten drucken";
        e.reset.hidden = false;
        this._setStatus(
          `${result.pages} Vorderseite(n) gedruckt. Blätter umdrehen, wieder einlegen, dann „Rückseiten drucken“.`,
        );
      } else if (duplex) {
        this._resetDuplex();
        this._setStatus(`Beidseitig fertig – ${result.pages} Rückseite(n) gedruckt.`);
        this._updateSelection();
      } else {
        this._setStatus(`An Drucker gesendet (${result.pages} Seite(n)).`);
      }
    } catch (err) {
      this._setStatus(err.message, true);
    } finally {
      e.print.disabled = false;
    }
  }
}

customElements.define("ipp-print-panel", IppPrintPanel);
