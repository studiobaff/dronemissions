'use strict';
/* Eigene Kartenebenen in den Einstellungen: Kachel-Dienste (XYZ/WMTS, optional mit API-Schlüssel) und Vektor-Ebenen.
   KML/KMZ und Shapefile-ZIP werden im Browser nach GeoJSON umgewandelt; der Server speichert nur bereinigtes GeoJSON. */
(() => {
 const el = id => document.getElementById(id);
 const PRESETS = {
  'mapbox-streets': { name: 'Mapbox Streets', url: 'https://api.mapbox.com/styles/v1/mapbox/streets-v12/tiles/256/{z}/{x}/{y}?access_token={key}', attribution: '© Mapbox · © OpenStreetMap-Mitwirkende', maxZoom: 22, key: true },
  'mapbox-satellite': { name: 'Mapbox Satellite', url: 'https://api.mapbox.com/styles/v1/mapbox/satellite-streets-v12/tiles/256/{z}/{x}/{y}?access_token={key}', attribution: '© Mapbox · © Maxar · © OpenStreetMap-Mitwirkende', maxZoom: 22, key: true },
  'basemapde': { name: 'Deutschland · basemap.de', url: 'https://sgx.geodatenzentrum.de/wmts_basemapde/tile/1.0.0/de_basemapde_web_raster_farbe/default/GLOBAL_WEBMERCATOR/{z}/{y}/{x}.png', attribution: '© GeoBasis-DE / BKG · dl-de/by-2-0', maxZoom: 19 },
  'topplus': { name: 'Deutschland · TopPlusOpen', url: 'https://sgx.geodatenzentrum.de/wmts_topplus_open/tile/1.0.0/web/default/WEBMERCATOR/{z}/{y}/{x}.png', attribution: '© BKG · TopPlusOpen · dl-de/by-2-0', maxZoom: 18 },
  'swisstopo-karte': { name: 'Schweiz · swisstopo Karte', url: 'https://wmts.geo.admin.ch/1.0.0/ch.swisstopo.pixelkarte-farbe/default/current/3857/{z}/{x}/{y}.jpeg', attribution: '© swisstopo', maxZoom: 18 },
  'swisstopo-luftbild': { name: 'Schweiz · swisstopo Luftbild', url: 'https://wmts.geo.admin.ch/1.0.0/ch.swisstopo.swissimage/default/current/3857/{z}/{x}/{y}.jpeg', attribution: '© swisstopo', maxZoom: 20 },
  'osm-hot': { name: 'Weltweit · OSM Humanitarian', url: 'https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png', attribution: '© OpenStreetMap-Mitwirkende · Tiles: Humanitarian OSM Team', maxZoom: 19 },
 };
 const tell = (id, text, error = false) => { const s = el(id); if (!s) return; s.textContent = text; s.classList.toggle('error', error); };
 let editing = null;

 async function loadList() {
  const list = el('layer-list'); if (!list) return;
  try {
   const { layers } = await api('layers'); list.replaceChildren();
   if (!layers.length) { list.textContent = 'Noch keine eigenen Ebenen. Die eingebauten Karten (basemap.at, OpenStreetMap, Esri) bleiben immer verfügbar.'; return; }
   const note = document.createElement('p'); note.className = 'hint'; note.textContent = 'Reihenfolge wie hier: so erscheinen die Ebenen in der Kartenwahl; Overlays weiter unten in der Liste liegen auf der Karte weiter oben.'; list.append(note);
   for (const l of layers) {
    const item = document.createElement('div'); item.className = 'layer-item';
    const swatch = document.createElement('span'); swatch.className = 'layer-swatch'; swatch.style.background = l.kind === 'vector' ? l.config.color : (l.config.overlay ? '#8460b5' : '#254e3b'); item.append(swatch);
    const text = document.createElement('div'); text.className = 'layer-text';
    const strong = document.createElement('strong'); strong.textContent = l.name; text.append(strong);
    const span = document.createElement('span'); span.textContent = l.kind === 'vector' ? `Vektor · ${l.config.features} Objekte${l.config.attribution ? ' · ' + l.config.attribution : ''}` : `${l.config.overlay ? 'Overlay' : 'Hintergrund'} · ${l.config.url}${l.config.keyHint ? ' · Schlüssel ' + l.config.keyHint : ''}`; text.append(span); item.append(text);
    if (l.kind === 'tile') { const edit = document.createElement('button'); edit.type = 'button'; edit.className = 'btn btn-outline btn-sm'; edit.textContent = 'Bearbeiten'; edit.onclick = () => { editing = l.id; el('layer-preset').value = ''; el('layer-name').value = l.name; el('layer-url').value = l.config.url; el('layer-key').value = ''; el('layer-key').placeholder = l.config.keyHint ? 'gespeichert (' + l.config.keyHint + '), leer lassen zum Behalten' : ''; el('layer-attribution').value = l.config.attribution || ''; el('layer-maxzoom').value = l.config.maxZoom || 19; el('layer-opacity').value = l.config.opacity ?? 1; el('layer-overlay').checked = Boolean(l.config.overlay); el('layer-save').textContent = 'Änderung speichern'; document.querySelector('.layer-add').open = true; el('layer-name').focus(); }; item.append(edit); }
    const order = document.createElement('span'); order.className = 'layer-order';
    for (const [label, delta, title] of [['▲', -1, 'Nach oben (weiter unten im Stapel)'], ['▼', 1, 'Nach unten (weiter oben im Stapel)']]) { const b = document.createElement('button'); b.type = 'button'; b.className = 'btn btn-icon btn-xs'; b.textContent = label; b.title = title; b.setAttribute('aria-label', title); b.disabled = (delta < 0 && layers[0] === l) || (delta > 0 && layers[layers.length - 1] === l); b.onclick = () => run(async () => { const ids = layers.map(x => x.id), i = ids.indexOf(l.id); ids.splice(i, 1); ids.splice(i + delta, 0, l.id); await api('layer-order', { ids }); await loadList(); await refresh(); }, b); order.append(b); }
    item.append(order);
    const del = document.createElement('button'); del.type = 'button'; del.className = 'btn btn-outline btn-sm'; del.textContent = 'Entfernen'; del.onclick = () => run(async () => { await api('layer-delete', { id: l.id }); await loadList(); await refresh(); toast('Ebene entfernt.'); }, del); item.append(del);
    list.append(item);
   }
  } catch (e) { list.textContent = e.message; }
 }
 function resetForm() { editing = null; el('layer-save').textContent = 'Ebene speichern'; for (const id of ['layer-name', 'layer-url', 'layer-key', 'layer-attribution']) el(id).value = ''; el('layer-key').placeholder = 'z. B. Mapbox-Token (pk.…)'; el('layer-maxzoom').value = 19; el('layer-opacity').value = 1; el('layer-overlay').checked = false; }

 document.addEventListener('click', e => { if (e.target.closest('#settings')) { editing = null; setTimeout(() => { resetForm(); loadList(); }, 0); } });
 document.addEventListener('change', e => {
  if (e.target.id === 'layer-preset') { const p = PRESETS[e.target.value]; if (!p) return; editing = null; el('layer-save').textContent = 'Ebene speichern'; el('layer-name').value = p.name; el('layer-url').value = p.url; el('layer-attribution').value = p.attribution; el('layer-maxzoom').value = p.maxZoom; el('layer-overlay').checked = false; el('layer-key').value = ''; tell('layer-status', p.key ? 'Für diese Vorlage den eigenen Zugangsschlüssel eintragen.' : 'Vorlage übernommen; Dienst und Lizenz vor dem Einsatz prüfen.'); }
 });
 document.addEventListener('click', e => {
  if (e.target.id === 'layer-save') run(async () => {
   const body = { id: editing || '', name: el('layer-name').value.trim(), url: el('layer-url').value.trim(), key: el('layer-key').value.trim(), attribution: el('layer-attribution').value.trim(), maxZoom: Number(el('layer-maxzoom').value), opacity: Number(el('layer-opacity').value), overlay: el('layer-overlay').checked };
   try { await api('layer-save', body); tell('layer-status', 'Gespeichert. Die Seite lädt nach „Speichern“ oder beim nächsten Öffnen neu, damit die Kachel-Adresse freigegeben ist.'); resetForm(); await loadList(); await refresh(); } catch (err) { tell('layer-status', err.message, true); }
  }, e.target);
  if (e.target.id === 'wmts-load') run(async () => {
   const list = el('wmts-list'); list.replaceChildren(); tell('wmts-status', 'Dienst wird gelesen …');
   try {
    const { layers } = await api('wmts-capabilities', { url: el('wmts-url').value.trim() }); tell('wmts-status', `${layers.length} Ebene(n) mit Web-Mercator-Kacheln.`);
    for (const l of layers) { const b = document.createElement('button'); b.type = 'button'; b.textContent = `${l.title} · ${l.matrixSet} · ${l.format}`; b.title = l.url; b.onclick = () => { editing = null; el('layer-save').textContent = 'Ebene speichern'; el('layer-name').value = l.title.slice(0, 60); el('layer-url').value = l.url; el('layer-maxzoom').value = l.maxZoom; tell('layer-status', 'Aus dem WMTS-Dienst übernommen. Quellenangabe ergänzen und speichern.'); el('layer-name').scrollIntoView({ block: 'center' }); }; list.append(b); }
   } catch (err) { tell('wmts-status', err.message, true); }
  }, e.target);
  if (e.target.id === 'vector-save') run(async () => {
   const file = el('vector-file').files[0]; if (!file) { tell('vector-status', 'Bitte eine Datei wählen.', true); return; }
   try {
    tell('vector-status', 'Datei wird gelesen …'); const geo = await toGeoJSON(file);
    const fd = new FormData(); fd.set('name', el('vector-name').value.trim() || file.name.replace(/\.[^.]+$/, '')); fd.set('color', el('vector-color').value); fd.set('attribution', el('vector-attribution').value.trim()); fd.set('file', new Blob([JSON.stringify(geo)], { type: 'application/geo+json' }), 'ebene.geojson');
    const result = await api('layer-upload', fd, true); tell('vector-status', `${result.features} Objekte gespeichert.`); el('vector-file').value = ''; el('vector-name').value = ''; await loadList(); await refresh();
   } catch (err) { tell('vector-status', err.message, true); }
  }, e.target);
 });

 /* ---------- Umwandlung nach GeoJSON ---------- */
 async function toGeoJSON(file) {
  const name = file.name.toLowerCase();
  if (name.endsWith('.geojson') || name.endsWith('.json')) { const geo = JSON.parse(await file.text()); if (geo.type === 'Feature') return { type: 'FeatureCollection', features: [geo] }; if (geo.type !== 'FeatureCollection') throw Error('GeoJSON muss eine FeatureCollection sein.'); return geo; }
  if (name.endsWith('.kml')) return kmlToGeoJSON(await file.text());
  const entries = await unzip(new Uint8Array(await file.arrayBuffer()));
  if (name.endsWith('.kmz')) { const kml = [...entries.keys()].find(k => k.toLowerCase().endsWith('.kml')); if (!kml) throw Error('KMZ enthält keine KML-Datei.'); return kmlToGeoJSON(new TextDecoder().decode(entries.get(kml))); }
  const shp = [...entries.keys()].find(k => k.toLowerCase().endsWith('.shp')); if (!shp) throw Error('ZIP enthält weder KML noch Shapefile (.shp).');
  const stem = shp.slice(0, -4), find = ext => { const key = [...entries.keys()].find(k => k.toLowerCase() === (stem + ext).toLowerCase()); return key ? entries.get(key) : null; };
  const prj = find('.prj'); if (prj) { const text = new TextDecoder().decode(prj); if (!/WGS[_ ]?1984|WGS84|4326/i.test(text) || /PROJCS|Mercator|UTM|MGI|Lambert/i.test(text)) throw Error('Shapefile ist nicht in WGS84 (EPSG:4326). Bitte vorher umprojizieren, z. B. in QGIS.'); }
  return shpToGeoJSON(entries.get(shp), find('.dbf'));
 }
 async function unzip(bytes) {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength); let eocd = -1;
  for (let i = bytes.length - 22; i >= Math.max(0, bytes.length - 66000); i--) if (view.getUint32(i, true) === 0x06054b50) { eocd = i; break; }
  if (eocd < 0) throw Error('ZIP-Datei nicht lesbar.');
  const count = view.getUint16(eocd + 10, true); let offset = view.getUint32(eocd + 16, true); const entries = new Map();
  for (let n = 0; n < count; n++) {
   if (view.getUint32(offset, true) !== 0x02014b50) throw Error('ZIP-Verzeichnis beschädigt.');
   const method = view.getUint16(offset + 10, true), compressed = view.getUint32(offset + 20, true), size = view.getUint32(offset + 24, true), nameLen = view.getUint16(offset + 28, true), extraLen = view.getUint16(offset + 30, true), commentLen = view.getUint16(offset + 32, true), local = view.getUint32(offset + 42, true);
   const name = new TextDecoder().decode(bytes.subarray(offset + 46, offset + 46 + nameLen)); offset += 46 + nameLen + extraLen + commentLen;
   if (name.endsWith('/') || name.includes('..')) continue; if (size > 64 * 1024 * 1024) throw Error('ZIP-Eintrag zu groß.');
   const lnameLen = view.getUint16(local + 26, true), lextraLen = view.getUint16(local + 28, true), start = local + 30 + lnameLen + lextraLen, raw = bytes.subarray(start, start + compressed);
   if (method === 0) entries.set(name, raw);
   else if (method === 8) { if (typeof DecompressionStream === 'undefined') throw Error('Dieser Browser kann ZIP nicht entpacken. Bitte GeoJSON oder KML hochladen.'); const stream = new Blob([raw]).stream().pipeThrough(new DecompressionStream('deflate-raw')); entries.set(name, new Uint8Array(await new Response(stream).arrayBuffer())); }
   else throw Error('ZIP-Kompressionsmethode nicht unterstützt.');
  }
  return entries;
 }
 function kmlToGeoJSON(text) {
  const doc = new DOMParser().parseFromString(text, 'application/xml'); if (doc.querySelector('parsererror')) throw Error('KML nicht lesbar.');
  const coords = node => (node.textContent || '').trim().split(/\s+/).filter(Boolean).map(t => t.split(',').map(Number)).filter(c => c.length >= 2 && Number.isFinite(c[0]) && Number.isFinite(c[1])).map(c => [c[0], c[1]]);
  const geometries = placemark => { const out = [];
   for (const g of placemark.querySelectorAll('Point, LineString, Polygon')) { if (g.closest('Placemark') !== placemark) continue; const tag = g.localName;
    if (tag === 'Point') { const c = coords(g.querySelector('coordinates') || g); if (c.length) out.push({ type: 'Point', coordinates: c[0] }); }
    else if (tag === 'LineString') { const c = coords(g.querySelector('coordinates') || g); if (c.length > 1) out.push({ type: 'LineString', coordinates: c }); }
    else { const rings = []; const outer = g.querySelector('outerBoundaryIs coordinates'); if (outer) rings.push(coords(outer)); for (const inner of g.querySelectorAll('innerBoundaryIs coordinates')) rings.push(coords(inner)); if (rings.length && rings[0].length > 2) out.push({ type: 'Polygon', coordinates: rings }); } }
   return out; };
  const features = [];
  for (const p of doc.getElementsByTagName('Placemark')) { const gs = geometries(p); if (!gs.length) continue; const props = { name: p.querySelector(':scope > name')?.textContent?.trim() || '', description: (p.querySelector(':scope > description')?.textContent || '').replace(/<[^>]+>/g, ' ').trim().slice(0, 500) };
   for (const d of p.querySelectorAll('ExtendedData Data')) { const k = d.getAttribute('name'); if (k) props[k] = d.querySelector('value')?.textContent?.trim() || ''; }
   features.push({ type: 'Feature', geometry: gs.length === 1 ? gs[0] : { type: 'GeometryCollection', geometries: gs }, properties: props }); }
  for (const f of features) if (f.geometry.type === 'GeometryCollection') { const g = f.geometry.geometries; const types = new Set(g.map(x => x.type)); if (types.size === 1) { const t = [...types][0]; f.geometry = { type: 'Multi' + t, coordinates: g.map(x => x.coordinates) }; } else f.geometry = g[0]; }
  if (!features.length) throw Error('KML enthält keine Punkte, Linien oder Flächen.');
  return { type: 'FeatureCollection', features };
 }
 function shpToGeoJSON(shp, dbf) {
  const view = new DataView(shp.buffer, shp.byteOffset, shp.byteLength); if (view.getInt32(0, false) !== 9994) throw Error('Shapefile nicht lesbar.');
  const records = dbf ? readDbf(dbf) : []; const features = []; let offset = 100, index = 0;
  const ringArea = r => { let a = 0; for (let i = 0; i < r.length - 1; i++) a += (r[i + 1][0] - r[i][0]) * (r[i + 1][1] + r[i][1]); return a; }; // >0 im Uhrzeigersinn = Außenring
  while (offset + 8 <= shp.byteLength) {
   const length = view.getInt32(offset + 4, false) * 2; const start = offset + 8; offset = start + length; if (length < 4) continue;
   const type = view.getInt32(start, true); let geometry = null;
   if (type === 1 || type === 11 || type === 21) geometry = { type: 'Point', coordinates: [view.getFloat64(start + 4, true), view.getFloat64(start + 12, true)] };
   else if (type === 8 || type === 18 || type === 28) { const n = view.getInt32(start + 36, true), pts = []; for (let i = 0; i < n; i++) pts.push([view.getFloat64(start + 40 + i * 16, true), view.getFloat64(start + 48 + i * 16, true)]); geometry = { type: 'MultiPoint', coordinates: pts }; }
   else if ([3, 5, 13, 15, 23, 25].includes(type)) {
    const parts = view.getInt32(start + 36, true), points = view.getInt32(start + 40, true), partIndex = []; for (let i = 0; i < parts; i++) partIndex.push(view.getInt32(start + 44 + i * 4, true));
    const base = start + 44 + parts * 4, pts = []; for (let i = 0; i < points; i++) pts.push([view.getFloat64(base + i * 16, true), view.getFloat64(base + 8 + i * 16, true)]);
    const rings = partIndex.map((s, i) => pts.slice(s, i + 1 < partIndex.length ? partIndex[i + 1] : points));
    if (type === 3 || type === 13 || type === 23) geometry = rings.length === 1 ? { type: 'LineString', coordinates: rings[0] } : { type: 'MultiLineString', coordinates: rings };
    else { const polys = []; for (const r of rings) { if (r.length < 4) continue; if (ringArea(r) > 0 || !polys.length) polys.push([r]); else polys[polys.length - 1].push(r); } geometry = polys.length === 1 ? { type: 'Polygon', coordinates: polys[0] } : { type: 'MultiPolygon', coordinates: polys }; }
   }
   if (geometry) features.push({ type: 'Feature', geometry, properties: records[index] || {} }); index++;
   if (features.length > 20000) throw Error('Maximal 20000 Objekte je Ebene.');
  }
  if (!features.length) throw Error('Shapefile enthält keine darstellbaren Objekte.');
  const sample = features.find(f => f.geometry.type === 'Point')?.geometry.coordinates || features[0].geometry.coordinates.flat(3).slice(0, 2);
  if (Math.abs(sample[0]) > 180 || Math.abs(sample[1]) > 90) throw Error('Koordinaten liegen nicht in WGS84 (Grad). Bitte umprojizieren.');
  return { type: 'FeatureCollection', features };
 }
 function readDbf(bytes) {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength); const count = view.getUint32(4, true), headerLen = view.getUint16(8, true), recordLen = view.getUint16(10, true);
  const fields = []; let p = 32; const ascii = (s, e) => { let t = ''; for (let i = s; i < e; i++) { const c = bytes[i]; if (c === 0) break; t += String.fromCharCode(c); } return t.trim(); };
  while (p + 32 <= headerLen && bytes[p] !== 0x0d) { fields.push({ name: ascii(p, p + 11), type: String.fromCharCode(bytes[p + 11]), length: bytes[p + 16] }); p += 32; }
  const decoder = new TextDecoder('utf-8', { fatal: false }), latin = new TextDecoder('windows-1252'); const records = [];
  for (let r = 0; r < count && r < 20000; r++) { let o = headerLen + r * recordLen; if (o + recordLen > bytes.length) break; const rec = {}; o += 1;
   for (const f of fields) { const slice = bytes.subarray(o, o + f.length); let text = decoder.decode(slice); if (text.includes('�')) text = latin.decode(slice); text = text.replace(/\0/g, '').trim(); rec[f.name] = f.type === 'N' || f.type === 'F' ? (text === '' ? null : Number(text)) : text; o += f.length; }
   records.push(rec); }
  return records;
 }
})();
