'use strict';
/* Drone Missions · Oberflächenlogik
   Die API (api.php) und das Datenmodell bleiben unverändert; diese Datei kümmert sich nur um Darstellung und Interaktion.
   zones.js (Kartenpanel, Geozonen, Adresssuche, Standortansicht) nutzt von hier: $, esc, api, picking, folder, canEdit, openPoint. */

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const icon = (name, cls = 'icon') => `<svg class="${cls}" aria-hidden="true"><use href="#${name}"/></svg>`;

/* ---------- Zustand ---------- */
let csrf = '';
let data = { folders: [], missions: [], points: [], role: 'viewer', scope: null };
let view = 'all';          // all | unfiled | archive | folder
let folder = null;         // aktive Ordner-ID
let filter = 'all';        // all | kmz | csv | native | mproj | points
let sort = 'map';      // updated | name | distance
let showMap = false,showList=false,missionOrderDrag=null;
let picking = false;       // Planungspunkt per Kartenklick (auch von zones.js gelesen)
let selected = null, uploadMission = null, editFolder = null, editPoint = null;
let overview = null, overviewLayers = null, detailMap = null;
let loaded = false;
let checkedMissions = new Set(), draggedMissions = null;
const archiveExpanded = new Set();

const ROUTE_COLORS = ['#7f9c2a', '#2f7f9a', '#b0632e', '#6f5fa6'];
const FORMAT = { 'litchi-csv': 'CSV', 'litchi-lchm': 'LCHM', 'litchi-lchz': 'LCHZ', 'mapcreator-project': 'MPROJ' };
const sourceType = m => FORMAT[m.details.sourceFormat] || 'KMZ';
const isNative = m => m.details.previewAvailable === false;
const isProject = m => ['MPROJ', 'LCHM', 'LCHZ'].includes(sourceType(m));
const canEdit = () => data.role !== 'viewer';
const isOwner = () => data.role === 'owner';
const includeSubfolders = () => $('#include-subfolders').checked;

/* ---------- Formatierung ---------- */
const nf = new Intl.NumberFormat('de-AT', { maximumFractionDigits: 1 });
const nf2 = new Intl.NumberFormat('de-AT', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const plural = (n, one, many) => `${new Intl.NumberFormat('de-AT').format(n)} ${n === 1 ? one : many}`;
const km = (meters, digits = 1) => `${(digits === 2 ? nf2 : nf).format(meters / 1000)} km`;
function fmtDate(iso, withTime = false) {
 const d = new Date(iso); if (Number.isNaN(d.getTime())) return '—';
 const diff = (Date.now() - d.getTime()) / 86400000;
 if (!withTime) {
  if (diff < 1 && diff >= 0 && d.toDateString() === new Date().toDateString()) return 'heute';
  if (diff < 2 && new Date(Date.now() - 86400000).toDateString() === d.toDateString()) return 'gestern';
  if (diff < 7 && diff >= 0) return `vor ${plural(Math.floor(diff), 'Tag', 'Tagen')}`;
 }
 return d.toLocaleString('de-AT', withTime ? { dateStyle: 'medium', timeStyle: 'short' } : { dateStyle: 'medium' });
}
const fmtBytes = b => b >= 1048576 ? `${nf.format(b / 1048576)} MB` : b >= 1024 ? `${Math.round(b / 1024)} KB` : `${b} B`;
const timeEl = (iso, withTime = false) => `<time datetime="${esc(iso)}" title="${esc(new Date(iso).toLocaleString('de-AT'))}">${esc(fmtDate(iso, withTime))}</time>`;

/* ---------- Rückmeldungen ---------- */
let pending = 0;
function progress(on) { pending = Math.max(0, pending + (on ? 1 : -1)); $('#progress').classList.toggle('on', pending > 0); }
function toast(message, error = false) {
 const el = $('#toast'); $('#toast-text').textContent = message; $('#toast-icon').setAttribute('href', error ? '#i-alert' : '#i-check');
 el.classList.toggle('error', error); el.hidden = false; clearTimeout(toast.timer);
 toast.timer = setTimeout(() => { el.hidden = true; }, error ? 8000 : 5000);
}
$('#toast').addEventListener('click', () => { $('#toast').hidden = true; });
function busy(button, on) {
 if (!button) return;
 if (on) { button.dataset.label = button.querySelector('span')?.textContent ?? ''; button.setAttribute('aria-busy', 'true'); button.disabled = true; const t = button.dataset.busy; if (t && button.querySelector('span')) button.querySelector('span').textContent = t; }
 else { button.removeAttribute('aria-busy'); button.disabled = false; if (button.dataset.label && button.querySelector('span')) button.querySelector('span').textContent = button.dataset.label; }
}
function confirmDialog(title, text, okLabel = 'Ja, fortfahren', danger = false) {
 const d = $('#confirm-dialog'); $('#confirm-title').textContent = title; $('#confirm-text').textContent = text;
 const ok = $('#confirm-ok'); ok.textContent = okLabel; ok.classList.toggle('btn-danger', danger);
 d.returnValue = ''; d.showModal(); ok.focus();
 return new Promise(resolve => { d.addEventListener('close', () => resolve(d.returnValue === 'ok'), { once: true }); });
}

/* ---------- API ---------- */
async function api(action, body, form = false) {
 const options = body === undefined ? {} : { method: 'POST', headers: { 'X-CSRF-Token': csrf, ...(!form ? { 'Content-Type': 'application/json' } : {}) }, body: form ? body : JSON.stringify(body) };
 progress(true);
 try {
  const r = await fetch(`api.php?action=${action}`, options);
  let d; try { d = await r.json(); } catch { throw Error('Serverantwort konnte nicht gelesen werden.'); }
  if (!r.ok) throw Error(d.error || 'Anfrage fehlgeschlagen.');
  return d;
 } finally { progress(false); }
}
async function run(fn, button = null) { busy(button, true); try { await fn(); } catch (e) { toast(e.message, true); } finally { busy(button, false); } }

/* ---------- Ordnerlogik ---------- */
const folderById = id => data.folders.find(f => f.id === id);
function pathList(id) { const names = [], seen = new Set(); let f = folderById(id); while (f && !seen.has(f.id)) { seen.add(f.id); names.unshift(f); f = folderById(f.parent); } return names; }
const pathFor = id => pathList(id).map(f => f.name).join(' / ');
function descendants(id) { const ids = new Set([id]); let change = true; while (change) { change = false; for (const f of data.folders) if (ids.has(f.parent) && !ids.has(f.id)) { ids.add(f.id); change = true; } } return ids; }
const scopeIds = () => folder ? (includeSubfolders() ? descendants(folder) : new Set([folder])) : null;
function isArchived(id) { let f = folderById(id), seen = new Set(); while (f && !seen.has(f.id)) { seen.add(f.id); if (Number(f.archived) || f.inheritedArchived) return true; f = folderById(f.parent); } return false; }
function folderOptions(selectedId = null, exclude = null) {
 const out = []; if (!data.scope) out.push('<option value="">Ohne Projektordner</option>');
 for (const f of data.folders) { if (exclude && descendants(exclude).has(f.id)) continue; out.push(`<option value="${f.id}" ${f.id === selectedId ? 'selected' : ''}>${esc(pathFor(f.id))}${isArchived(f.id) ? ' (archiviert)' : ''}</option>`); }
 return out.join('');
}

/* ---------- Sichtbare Elemente ---------- */
const query = () => $('#search').value.trim().toLocaleLowerCase();
function matchesFilter(m) {
 if (filter === 'all') return true; if (filter === 'points') return false;
 const t = sourceType(m); return { kmz: t === 'KMZ', csv: t === 'CSV', native: t === 'LCHM' || t === 'LCHZ', mproj: t === 'MPROJ' }[filter];
}
function visibleMissions() {
 const q = query(), ids = scopeIds();
 const list = data.missions.filter(m => {
  const archived = m.archived || isArchived(m.folder);
  if (view === 'archive' ? !archived : view === 'folder' && isArchived(folder) ? false : archived) return false;
  if (view === 'unfiled' && m.folder) return false;
  if (ids && !ids.has(m.folder)) return false;
  if (!matchesFilter(m)) return false;
  return `${m.name} ${m.filename} ${pathFor(m.folder)} ${m.notes}`.toLocaleLowerCase().includes(q);
 });
 const by = { updated: (a, b) => new Date(b.updated) - new Date(a.updated), name: (a, b) => dmPermitNameKey(a).localeCompare(dmPermitNameKey(b),'de',{numeric:true,sensitivity:'base'}), map: (a,b)=>(a.mapOrder??Number.MAX_SAFE_INTEGER)-(b.mapOrder??Number.MAX_SAFE_INTEGER)||dmPermitNameKey(a).localeCompare(dmPermitNameKey(b),'de',{numeric:true,sensitivity:'base'}), distance: (a, b) => (b.details.distance || 0) - (a.details.distance || 0) }[sort];
 return list.sort(by);
}
function visiblePoints() {
 if ((filter !== 'all' && filter !== 'points') || view === 'unfiled') return [];
 const ids = scopeIds(), q = query();
 return data.points.filter(p => (!ids || ids.has(p.folder)) && (view === 'archive' ? isArchived(p.folder) : view === 'folder' && isArchived(folder) ? true : !isArchived(p.folder)) && `${p.name} ${p.notes} ${pathFor(p.folder)}`.toLocaleLowerCase().includes(q)).sort((a, b) => a.name.localeCompare(b.name, 'de'));
}

/* ---------- Rendern ---------- */
async function refresh() { data = await api('library'); loaded = true; if (folder && !folderById(folder)) { folder = null; view = 'all'; } render(); }
function navigate(nextView, nextFolder = null) { view = nextView; folder = nextFolder; closeSidebar(); render(); window.scrollTo({ top: 0, behavior: 'auto' }); syncHash(); }
/* Adresszeile: #projekt=<id>, #ansicht=archiv|ohne, #mission=<id>; Lesezeichen und geteilte Links öffnen dieselbe Ansicht. Kundenlinks (#share=) bleiben unverändert. */
let hashSyncing = false;
function syncHash() {
 if (!loaded) return; const parts = [];
 if (view === 'folder' && folder) parts.push('projekt=' + encodeURIComponent(folder)); else if (view === 'archive') parts.push('ansicht=archiv'); else if (view === 'unfiled') parts.push('ansicht=ohne');
 if (selected && $('#detail-dialog').open) parts.push('mission=' + encodeURIComponent(selected.id));
 const next = parts.length ? '#' + parts.join('&') : ''; if ((location.hash || '') === next) return;
 hashSyncing = true; history.replaceState(null, '', location.pathname + location.search + next); hashSyncing = false;
}
function applyHash() {
 const q = new URLSearchParams(location.hash.slice(1)); if (q.get('share')) return;
 const project = q.get('projekt'), ansicht = q.get('ansicht'), mission = q.get('mission');
 if (project && folderById(project)) { view = 'folder'; folder = project; } else if (ansicht === 'archiv') { view = 'archive'; folder = null; } else if (ansicht === 'ohne') { view = 'unfiled'; folder = null; }
 render();
 if (mission && data.missions.some(m => m.id === mission)) openMission(mission); else syncHash();
}
window.addEventListener('hashchange', () => { if (!hashSyncing && loaded) applyHash(); });

function renderSidebar() {
 const active = data.missions.filter(m => !m.archived && !isArchived(m.folder));
 $('#count').textContent = active.length; $('#count-archive').textContent = data.missions.length - active.length || ''; $('#count-unfiled').textContent = active.filter(m => !m.folder).length || '';
 $('[data-view=unfiled]').classList.toggle('hidden', !!data.scope);
 $('#role-label').textContent = { owner: 'Eigentümer · privater Zugang', editor: 'Projektfreigabe · bearbeiten', viewer: 'Kundenansicht · Orte & Navigation' }[data.role];
 $$('.nav-item').forEach(e => e.classList.toggle('active', e.dataset.view === view));
 const renderFolder = (f, depth = 0) => `<button type="button" class="folder-item ${folder === f.id ? 'active' : ''}" data-folder="${f.id}" style="padding-left:${10 + Math.min(depth, 6) * 14}px" title="${esc(pathFor(f.id))}" aria-label="Projekt ${esc(pathFor(f.id))}">${icon('i-folder')}<span>${esc(f.name)}</span>${Number(f.archived) ? '<i class="badge badge-muted">Archiv</i>' : ''}</button>${data.folders.filter(c => c.parent === f.id).map(c => renderFolder(c, depth + 1)).join('')}`;
 const roots = data.folders.filter(f => !f.parent || !folderById(f.parent));
 $('#folders').innerHTML = roots.map(f => renderFolder(f)).join('') || '<p class="sidebar-hint">Projekte bringen Ordnung in deine Missionen. Lege oben ein neues Projekt an.</p>';
}
function renderHeader() {
 $('#new-project').classList.toggle('hidden', !canEdit()); $('#add-folder').classList.toggle('hidden', !canEdit());
 $('#upload').classList.toggle('hidden', !canEdit()); $('#upload-compact').classList.toggle('hidden', !canEdit()); $('#empty-upload').classList.toggle('hidden', !canEdit());
 $('#manage-shares').classList.toggle('hidden', !isOwner()); $('#settings').classList.toggle('hidden', !isOwner()); $('#bridge').classList.toggle('hidden', !canEdit());
 $('#share-project').classList.toggle('hidden', !folder || !isOwner()); $('#folder-options').classList.toggle('hidden', !folder || !canEdit()); $('#add-point').classList.toggle('hidden', !folder || !canEdit());
 $('#subfolders-control').classList.toggle('hidden', !folder); $('#selection-tools').classList.toggle('hidden', !canEdit() || showMap);
 $('#sort').closest('.sort').classList.toggle('hidden', !canEdit());
 const crumbs = [];
 const link = (label, v, f = null, current = false) => `<button type="button" data-nav="${v}" ${f ? `data-nav-folder="${f}"` : ''} class="${current ? 'current' : ''}">${esc(label)}</button>`;
 if (folder) { crumbs.push(link('Projekte', 'all')); const list = pathList(folder); list.forEach((f, i) => crumbs.push(link(f.name, 'folder', f.id, i === list.length - 1))); }
 else crumbs.push(link('Bibliothek', 'all', null, view === 'all'), ...(view === 'archive' ? [link('Archiv', 'archive', null, true)] : view === 'unfiled' ? [link('Ohne Projekt', 'unfiled', null, true)] : []));
 $('#breadcrumb').innerHTML = crumbs.join(icon('i-chevron'));
 const current = folder ? folderById(folder) : null;
 const archivedBadge = current && isArchived(folder) ? '<span class="badge badge-muted">Archiviert</span>' : '';
 $('#page-title').innerHTML = `<span>${esc(current ? current.name : view === 'archive' ? 'Archiv' : view === 'unfiled' ? 'Ohne Projekt' : canEdit() ? 'Alle Missionen' : 'Freigegebene Orte')}</span>${archivedBadge}`;
 $('#page-subtitle').textContent = !canEdit() ? 'Standorte dieses Projekts mit Navigation. Flugrouten und Missionsdateien sind nicht Teil dieser Freigabe.' : folder ? 'Flugmissionen und wiederverwendbare Panorama-Standorte an einem Ort.' : view === 'archive' ? 'Gesichert für später. Originaldateien und Versionen bleiben erhalten.' : view === 'unfiled' ? 'Missionen ohne Projektordner. Per Auswahl oder Ziehen in ein Projekt verschieben.' : 'Geplant in Litchi oder Map Creator. Hier bereit für den nächsten Einsatz.';
 if (folder && canEdit() && !isArchived(folder)) { const ids = scopeIds(); const archived = data.missions.filter(m => ids.has(m.folder) && m.archived).length; if (archived) $('#page-subtitle').textContent += ` ${plural(archived, 'archivierte Mission ist', 'archivierte Missionen sind')} unter „Archiv“ im selben Projektordner zu finden.`; }
}
function renderStats(missions, points) {
 $('#total-missions').textContent = missions.length; $('#total-missions-label').textContent = canEdit() ? (missions.length === 1 ? 'Mission' : 'Missionen') : (missions.length === 1 ? 'Standort' : 'Standorte');
 const projects = folder ? scopeIds().size : data.folders.length;
 $('#total-projects').textContent = projects;
 const measurable = missions.filter(m => !isNative(m));
 $('#total-distance').textContent = measurable.length && canEdit() ? km(measurable.reduce((s, m) => s + m.details.distance, 0)) : '—';
 $('#total-points').textContent = points.length; $('#total-points-label').textContent = points.length === 1 ? 'Planungspunkt' : 'Planungspunkte';
}
function navigation(m) {
 const p = m.overviewPoint; if (!p) return '';
 const coords = encodeURIComponent(`${Number(p.lat)},${Number(p.lng)}`);
 return `<div class="navigation-links"><a class="btn btn-outline btn-sm" href="https://www.google.com/maps/dir/?api=1&destination=${coords}" target="_blank" rel="noreferrer noopener">${icon('i-navigate')}<span>Google Maps</span></a><a class="btn btn-outline btn-sm" href="https://maps.apple.com/?daddr=${coords}" target="_blank" rel="noreferrer noopener">${icon('i-navigate')}<span>Apple Maps</span></a>${m.id && !m.locationOnly ? `<a class="btn btn-outline btn-sm" href="api.php?action=location&id=${m.id}">${icon('i-globe')}<span>Ort für Google Earth</span></a>` : ''}</div>`;
}
function missionCard(m,position=0) {
 if(showList)return missionListRow(m,position);
 const archived = m.archived || isArchived(m.folder), native = isNative(m), type = sourceType(m), checked = checkedMissions.has(m.id);
 if (!canEdit()) return `<article class="card card-location" data-mission="${m.id}" tabindex="0" role="button" aria-label="Standort ${esc(m.name)} öffnen"><div class="card-media">${icon('i-pin')}<small>Freigegebener Standort</small></div><div class="card-body"><div class="card-path">${icon('i-folder')}<span>${esc(pathFor(m.folder))}</span></div><h2 title="${esc(m.name)}">${esc(m.name)}</h2><p class="card-notes num">${Number(m.overviewPoint.lat).toFixed(5)}, ${Number(m.overviewPoint.lng).toFixed(5)}</p>${navigation(m)}</div></article>`;
 return `<article class="card ${archived ? 'is-archived' : ''} ${checked ? 'is-selected' : ''}" data-mission="${m.id}" draggable="true" tabindex="0" role="button" aria-label="Mission ${esc(m.name)} öffnen">
  <label class="card-select"><input type="checkbox" data-select="${m.id}" ${checked ? 'checked' : ''} aria-label="${esc(m.name)} auswählen"></label>
  <div class="card-media"><span class="card-position" title="Listenposition in der aktuellen Sortierung">${position+1}</span><img src="api.php?action=preview&id=${m.id}&version=${m.versionId}" alt="" loading="lazy" decoding="async"><div class="card-badges"><span class="badge badge-dark">V${m.version} · ${type}</span>${archived ? '<span class="badge badge-muted">Archiv</span>' : ''}${m.overviewPoint ? `<span class="badge badge-dark" title="In der Projektkarte">${icon('i-pin')}</span>` : ''}</div><span class="card-arrow">${icon('i-arrow')}</span></div>
  <div class="card-body"><button type="button" class="card-path card-path-link" data-project="${m.folder || ''}" title="${esc(pathFor(m.folder) || 'Ohne Projekt')} · nach Projekt filtern">${icon('i-folder')}<span>${esc(pathFor(m.folder) || 'Ohne Projekt')}</span></button><h2 title="${esc(m.name)}">${esc(m.name)}</h2>
  <div class="card-meta">${native ? `<span>${icon('i-file')}${type === 'MPROJ' ? 'Map-Creator-Projekt' : 'Litchi-Original'}</span><span>${icon('i-route')}Route offen</span>` : `<span>${icon('i-route')}${plural(m.details.count, 'Wegpunkt', 'Wegpunkte')}</span><span>${icon('i-ruler')}${km(m.details.distance, 2)}</span>`}${m.attachments?.length ? `<span>${icon('i-link')}${plural(m.attachments.length, 'Projektdatei', 'Projektdateien')}</span>` : ''}</div>
  <div class="card-foot"><span class="verified">${icon('i-shield')}Original geprüft</span>${timeEl(m.updated)}</div></div></article>`;
}
function missionListRow(m,position){return `<article class="card mission-list-row ${checkedMissions.has(m.id)?'is-selected':''}" data-mission="${m.id}" tabindex="0" role="button" aria-label="Mission ${esc(m.name)} öffnen">${canEdit()?`<label class="list-check"><input type="checkbox" data-select="${m.id}" ${checkedMissions.has(m.id)?'checked':''} aria-label="${esc(m.name)} auswählen"></label><button type="button" class="permit-row-grip" draggable="true" data-order-grip="${m.id}" aria-label="${esc(m.name)} in Liste verschieben" title="Reihenfolge ändern · ziehen oder Pfeiltaste hoch/runter">⠿</button>`:''}<span class="list-position">${position+1}</span><strong class="list-title">${esc(m.name)}</strong><button type="button" class="card-path-link list-chip" data-project="${m.folder||''}">${esc(pathFor(m.folder)||'Ohne Projekt')}</button><span class="list-chip">${esc(sourceType(m))}</span><button type="button" class="btn btn-outline btn-sm" data-open-list="${m.id}">Öffnen</button></article>`;}
function pointCard(p) {
 const body = canEdit() ? `<p class="card-notes">${esc(p.notes || 'Wiederverwendbarer Aufnahmeort')}</p><div class="card-foot"><span class="num">${Number(p.lat).toFixed(5)}, ${Number(p.lng).toFixed(5)}</span><span>${plural(Number(p.settings?.height ?? 0), 'm', 'm')} · ${esc({ sphere: 'Kugel', wideAngle: 'Weitwinkel', photo: 'Foto' }[p.settings?.capture] || 'Panorama')}</span></div>` : `<p class="card-notes num">${Number(p.lat).toFixed(5)}, ${Number(p.lng).toFixed(5)}</p>${navigation({ overviewPoint: p })}`;
 return `<article class="card card-point" data-point="${p.id}" tabindex="0" role="button" aria-label="Planungspunkt ${esc(p.name)} öffnen"><div class="card-media">${icon('i-crosshair')}<small>Panorama-Standort</small></div><div class="card-body"><div class="card-path" title="${esc(pathFor(p.folder))}">${icon('i-folder')}<span>${esc(pathFor(p.folder))}</span></div><h2 title="${esc(p.name)}">${esc(p.name)}</h2>${body}</div></article>`;
}
function archiveCards(missions, points) {
 const groups = new Map();
 const group = id => {
  const key = id || 'unfiled';
  if (!groups.has(key)) groups.set(key, { id, missions: [], points: [] });
  return groups.get(key);
 };
 missions.forEach(m => group(m.folder).missions.push(m));
 points.forEach(p => group(p.folder).points.push(p));
 if (!query() && filter === 'all') data.folders.filter(f => isArchived(f.id)).forEach(f => group(f.id));
 return [...groups.entries()].sort(([, a], [, b]) => (pathFor(a.id) || 'Ohne Projekt').localeCompare(pathFor(b.id) || 'Ohne Projekt', 'de')).map(([key, g]) => {
  const label = pathFor(g.id) || 'Ohne Projekt';
  const count = plural(g.missions.length, 'Mission', 'Missionen') + (g.points.length ? ` · ${plural(g.points.length, 'Planungspunkt', 'Planungspunkte')}` : '');
  return `<details class="archive-group" data-archive-group="${esc(key)}" ${archiveExpanded.has(key) || query() ? 'open' : ''}><summary><span>${icon('i-folder')}${esc(label)}</span><span class="badge badge-muted">${count}</span></summary><div class="cards">${g.missions.map(missionCard).join('')}${g.points.map(pointCard).join('')}${!g.missions.length && !g.points.length ? '<p class="hint">Keine archivierten Einträge in diesem Ordner.</p>' : ''}</div></details>`;
 }).join('');
}
$('#cards').addEventListener('toggle', e => {
 const group = e.target.closest('[data-archive-group]');
 if (!group) return;
 if (group.open) archiveExpanded.add(group.dataset.archiveGroup); else archiveExpanded.delete(group.dataset.archiveGroup);
}, true);
function render() {
 const missions = visibleMissions(), points = visiblePoints();
 checkedMissions = new Set([...checkedMissions].filter(id => missions.some(m => m.id === id)));
 renderSidebar(); renderHeader(); renderStats(missions, points);
 $$('#filters .chip').forEach(c => c.classList.toggle('selected', c.dataset.filter === filter));
 $('#filters').classList.toggle('hidden', !canEdit());
 $('#cards').innerHTML = view === 'archive' ? archiveCards(missions, points) : missions.map(missionCard).join('') + points.map(pointCard).join('');
 const total = missions.length + points.length, q = query(), filtered = q || filter !== 'all';
 const unit = canEdit() ? ['Mission', 'Missionen'] : ['Standort', 'Standorte'];
 $('#result-line').textContent = total ? `${plural(missions.length, ...unit)}${points.length ? ` · ${plural(points.length, 'Planungspunkt', 'Planungspunkte')}` : ''}${filtered ? ' gefunden' : ''}` : '';
 const empty = $('#empty');
 empty.classList.toggle('hidden', total > 0 || showMap || (view === 'archive' && $('#cards').children.length > 0));
 if (!total) {
  $('#empty-upload').classList.add('hidden'); $('#empty-clear').classList.add('hidden');
  if (filtered) { $('#empty-title').textContent = 'Nichts gefunden.'; $('#empty-text').textContent = q ? `Kein Eintrag passt zu „${$('#search').value.trim()}“. Prüfe die Schreibweise oder setze den Filter zurück.` : 'Kein Eintrag passt zum gewählten Filter.'; $('#empty-clear').classList.remove('hidden'); }
  else if (!canEdit()) { $('#empty-title').textContent = 'Noch kein freigegebener Standort.'; $('#empty-text').textContent = 'Der Eigentümer hat in diesem Projekt noch keinen Punkt für die Projektkarte ausgewählt.'; }
  else if (view === 'archive') { $('#empty-title').textContent = 'Das Archiv ist leer.'; $('#empty-text').textContent = 'Archivierte Missionen und Projekte erscheinen hier. Originaldateien bleiben dabei immer erhalten.'; }
  else if (view === 'unfiled') { $('#empty-title').textContent = 'Alles zugeordnet.'; $('#empty-text').textContent = 'Jede Mission liegt in einem Projektordner.'; }
  else { $('#empty-title').textContent = folder ? 'Noch keine Mission in diesem Projekt.' : 'Raum für deinen nächsten Flug.'; $('#empty-text').textContent = 'Lade KMZ, CSV, native Litchi-Missionen oder Map-Creator-Projekte hoch. Route und Höhenprofil für KMZ/CSV; Projektdateien werden unverändert archiviert.'; $('#empty-upload').classList.toggle('hidden', !canEdit()); }
 }
 updateSelection();
 document.body.classList.toggle('permit-map-active',showMap);$('#permit-tools').classList.toggle('hidden',!showMap);$('#cards').classList.toggle('hidden', showMap); $('#overview-map').classList.toggle('hidden', !showMap);
 $('#planner-open').classList.toggle('hidden',!canEdit());
 $('#project-reference').classList.toggle('hidden',data.role!=='owner'||!folder);
 if (showMap) renderOverview();
}
function renderSkeleton() { $('#cards').innerHTML = Array.from({ length: 6 }, () => '<article class="card skeleton" aria-hidden="true"><div class="card-media"></div><div class="card-body"><span class="sk" style="width:40%"></span><span class="sk" style="width:75%;height:1.1em"></span><span class="sk" style="width:55%"></span></div></article>').join(''); }

/* ---------- Auswahl, Verschieben, Ziehen ---------- */
function updateSelection() {
 if (!canEdit()) return;
 const visible = visibleMissions(); $('#selection-count').textContent = `${checkedMissions.size} ausgewählt`;
 $('#move-selected').disabled = $('#clear-selection').disabled = !checkedMissions.size;
 const all = $('#select-visible'); all.checked = visible.length > 0 && visible.every(m => checkedMissions.has(m.id)); all.indeterminate = checkedMissions.size > 0 && !all.checked;
 $$('.card[data-mission]').forEach(el => el.classList.toggle('is-selected', checkedMissions.has(el.dataset.mission)));
}
async function moveMissions(ids, target) {
 const missions = ids.map(id => data.missions.find(m => m.id === id)).filter(Boolean).map(m => ({ id: m.id, revision: m.revision }));
 if (!missions.length) return; await api('missions-move', { folder: target || null, missions }); checkedMissions.clear(); await refresh();
 toast(`${plural(missions.length, 'Mission', 'Missionen')} verschoben nach „${target ? pathFor(target) : 'Ohne Projektordner'}“.`);
}
$('#include-subfolders').onchange = render;
$('#cards').onchange = e => { if (e.target.matches('[data-select]')) { if (e.target.checked) checkedMissions.add(e.target.dataset.select); else checkedMissions.delete(e.target.dataset.select); updateSelection(); } };
$('#select-visible').onchange = e => { checkedMissions = e.target.checked ? new Set(visibleMissions().map(m => m.id)) : new Set(); render(); };
$('#clear-selection').onclick = () => { checkedMissions.clear(); render(); };
$('#move-selected').onclick = () => { $('#move-folder').innerHTML = folderOptions(folder); $('#move-summary').textContent = `${plural(checkedMissions.size, 'ausgewählte Mission', 'ausgewählte Missionen')} gemeinsam einem Projektordner zuordnen. Originaldateien bleiben unverändert.`; $('#move-dialog').showModal(); };
$('#move-form').onsubmit = e => { e.preventDefault(); run(async () => { await moveMissions([...checkedMissions], $('#move-folder').value); $('#move-dialog').close(); }, $('button[type=submit]', e.target)); };
$('#cards').ondragstart = e => {const grip=e.target.closest('[data-order-grip]');if(grip&&canEdit()){missionOrderDrag=grip.dataset.orderGrip;draggedMissions=null;e.dataTransfer.effectAllowed='move';e.dataTransfer.setData('text/plain',missionOrderDrag);return;}const card = e.target.closest('[data-mission]'); if (!card || !canEdit() || e.target.closest('input,button,a')) { e.preventDefault(); return; } draggedMissions = checkedMissions.has(card.dataset.mission) ? [...checkedMissions] : [card.dataset.mission]; e.dataTransfer.effectAllowed = 'move'; e.dataTransfer.setData('text/plain', `${draggedMissions.length} Missionen`); card.classList.add('is-dragging'); };
$('#cards').ondragover=e=>{if(!missionOrderDrag)return;const row=e.target.closest('[data-mission]');if(row){e.preventDefault();$$('.drop-target').forEach(x=>x.classList.remove('drop-target'));row.classList.add('drop-target');}};$('#cards').ondrop=e=>{const row=e.target.closest('[data-mission]');if(!row||!missionOrderDrag)return;e.preventDefault();const id=missionOrderDrag;missionOrderDrag=null;dmMoveMissionOrder(id,row.dataset.mission,visibleMissions());};
$('#cards').ondragend = () => {missionOrderDrag=null; draggedMissions = null; $$('.drop-target').forEach(el => el.classList.remove('drop-target')); $$('.is-dragging').forEach(el => el.classList.remove('is-dragging')); };
$('#folders').ondragover = e => { const target = e.target.closest('[data-folder]'); if (!target || !draggedMissions || !canEdit()) return; e.preventDefault(); e.dataTransfer.dropEffect = 'move'; $$('.drop-target').forEach(el => el.classList.remove('drop-target')); target.classList.add('drop-target'); };
$('#folders').ondragleave = e => { const target = e.target.closest('[data-folder]'); if (target && !target.contains(e.relatedTarget)) target.classList.remove('drop-target'); };
$('#folders').ondrop = e => { const target = e.target.closest('[data-folder]'); if (!target || !draggedMissions || !canEdit()) return; e.preventDefault(); const ids = draggedMissions; draggedMissions = null; target.classList.remove('drop-target'); run(() => moveMissions(ids, target.dataset.folder)); };

/* ---------- Karte ---------- */
function referenceStyle(layer,feature){
 const p=feature?.properties||{},source=layer.useSourceStyle!==false;
 const color=source&&/^#[0-9a-f]{6}$/i.test(p.stroke||'')?p.stroke:layer.color;
 const width=Number(p['stroke-width']),alpha=Number(p['stroke-opacity']);
 return {color,weight:source&&p['stroke-width']!==undefined&&Number.isFinite(width)&&width>=0&&width<=32?width:(layer.weight??1.5),opacity:source&&p['stroke-opacity']!==undefined&&Number.isFinite(alpha)&&alpha>=0&&alpha<=1?alpha:1,fillOpacity:.15};
}
function referenceLayers(projectFolder){
 const ancestors=new Set();let f=folderById(projectFolder);while(f&&!ancestors.has(f.id)){ancestors.add(f.id);f=folderById(f.parent);}
 return (data.layers||[]).filter(l=>!l.folder||ancestors.has(l.folder));
}
function tiles(map,projectFolder=folder) {
 map.on('unload',()=>{map.dmDisposed=true;});
 const attribution = 'Datenquelle: <a href="https://basemap.at/#lizenz" target="_blank" rel="noreferrer">basemap.at</a> · CC BY 4.0';
 const austria = { bounds: [[46.35, 9.45], [49.05, 17.2]], maxNativeZoom: 19, maxZoom: 20, attribution };
 const base = {
  'Österreich · basemap.at': L.tileLayer('https://mapsneu.wien.gv.at/basemap/geolandbasemap/normal/google3857/{z}/{y}/{x}.png', austria),
  'Österreich · Luftbild': L.tileLayer('https://mapsneu.wien.gv.at/basemap/bmaporthofoto30cm/normal/google3857/{z}/{y}/{x}.jpeg', austria),
  'Weltweit · OpenStreetMap': L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, referrerPolicy: 'strict-origin-when-cross-origin', attribution: '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a>' }),
  'Weltweit · Esri Satellit': L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', { maxZoom: 19, attribution: 'Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community' })
 };
 const roads = L.tileLayer('https://mapsneu.wien.gv.at/basemap/bmapoverlay/normal/google3857/{z}/{y}/{x}.png', { ...austria, zIndex: 350 });
 for (const l of referenceLayers(projectFolder)) if (l.kind === 'tile' && !l.overlay) base[l.name] = L.tileLayer(l.url, { maxZoom: l.maxZoom || 19, opacity: l.opacity ?? 1, attribution: esc(l.attribution || ''), referrerPolicy: 'strict-origin-when-cross-origin' });
 const store = { get: k => { try { return localStorage.getItem(k); } catch { return null; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch { /* privater Modus */ } } };
 const saved = store.get('dm-map-layer'); let activeBase = base[saved] ? saved : Object.keys(base)[0], syncingRoads = false; base[activeBase].addTo(map);
 const syncRoads = () => { const preference = store.get('dm-map-roads'), show = preference === null ? activeBase === 'Österreich · Luftbild' : preference === 'true'; syncingRoads = true; if (show) roads.addTo(map); else map.removeLayer(roads); syncingRoads = false; };
 map.on('baselayerchange', e => { activeBase = e.name; store.set('dm-map-layer', e.name); queueMicrotask(syncRoads); });
 map.on('overlayadd overlayremove', e => { if (e.layer === roads && !syncingRoads) store.set('dm-map-roads', String(e.type === 'overlayadd')); });
 const overlays = {};
 referenceLayers(projectFolder).forEach((l, index) => {
  // Stapelung folgt der Reihenfolge aus den Einstellungen: Kachel-Overlays über den Straßen (350), Vektor-Ebenen in eigenen Panes zwischen Geozonen (380) und dem Routen-Pane (400), damit Missionsrouten und Wegpunkte immer oben bleiben.
  if (l.kind === 'tile') { if (l.overlay) overlays[l.id] = { label: l.name, layer: L.tileLayer(l.url, { maxZoom: l.maxZoom || 19, opacity: l.opacity ?? 1, attribution: esc(l.attribution || ''), referrerPolicy: 'strict-origin-when-cross-origin', zIndex: 360 + index }) }; }
  else overlays[l.id] = { defaultOn:Boolean(l.folder), label: `${l.name} (${l.features})`, layer: null, load: async () => { const r = await fetch(`api.php?action=layer-data&id=${encodeURIComponent(l.id)}`); if (!r.ok) throw Error('Ebene konnte nicht geladen werden.'); const geo = await r.json(); const pane = 'layer-' + l.id; if (!map.getPane(pane)) { map.createPane(pane); map.getPane(pane).style.zIndex = String(381 + Math.min(index, 18)); } const layer=L.geoJSON(geo, { pane, attribution: esc(l.attribution || ''), style: f=>referenceStyle(l,f), pointToLayer: (f, latlng) => L.circleMarker(latlng, { radius: 5, ...referenceStyle(l,f), fillOpacity: .7 }), onEachFeature: (f, layer) => { const rows = Object.entries(f.properties || {}).filter(([, v]) => v !== null && v !== '').slice(0, 12); if (rows.length) layer.bindPopup(`<strong>${esc(l.name)}</strong><br>` + rows.map(([k, v]) => `${esc(k)}: ${esc(String(v))}`).join('<br>')); } }); if(map===overview&&!map.dmDisposed&&l.folder&&layer.getBounds().isValid()){map.dmReferenceBounds=map.dmReferenceBounds?map.dmReferenceBounds.extend(layer.getBounds()):layer.getBounds();map.dmFitProject?.();}return layer; } };
 });
 dmMapControls(map, base, roads, overlays); syncRoads(); L.control.scale({ imperial: false }).addTo(map);
 let lastError = 0; [...Object.values(base), roads].forEach(layer => layer.on('tileerror', () => { if (Date.now() - lastError > 15000) { lastError = Date.now(); toast('Kartenkacheln nicht erreichbar. Bitte Verbindung oder Kartenebene prüfen.', true); } }));
}
function drawRoute(map, mission, group = null, numbered = true) {
 const target = group || map, points = mission.details.points;
 mission.details.routes.forEach((route, i) => { const coords = points.slice(route.start, route.start + route.count).map(p => [p.lat, p.lng]); L.polyline(coords, { color: '#1b2f27', weight: 6, opacity: numbered ? .35 : .2 }).addTo(target); L.polyline(coords, { color: numbered ? ROUTE_COLORS[i % ROUTE_COLORS.length] : '#b5e34c', weight: 3, opacity: numbered ? .95 : .7 }).addTo(target); });
 if (numbered) {
  const stride = Math.max(1, Math.ceil(points.length / (window.innerWidth < 900 ? 60 : 150)));
  points.forEach((p, i) => { if (i % stride && i !== points.length - 1) return; const marker = L.marker([p.lat, p.lng], { icon: L.divIcon({ className: 'waypoint-marker', html: `<span>${i + 1}</span>`, iconSize: [24, 24], iconAnchor: [12, 12] }), keyboard: false }).addTo(target); marker.bindTooltip(`Wegpunkt ${i + 1} · ${p.height === null ? 'Höhe unbekannt' : p.height + ' m'}`); marker.on('click', () => { const select = $('#mission-overview'); if (canEdit() && select && !select.disabled) { select.value = String(i); toast(`Wegpunkt ${i + 1} als Projektkarten-Punkt gewählt. Zum Übernehmen Änderungen speichern.`); } }); });
 }
 (mission.details.pois || []).forEach(p => L.marker([p.lat,p.lng], {icon:L.divIcon({className:'poi-marker',html:`<span>◆ ${esc(p.label)}</span>`,iconSize:[80,28],iconAnchor:[12,14]})}).addTo(target).bindTooltip(esc(p.label)+' · Blickziel (Lage)'));
 return points.concat(mission.details.pois||[]).map(p => [p.lat,p.lng]);
}
function renderOverview() {
 const keepPermitView=dmPermitKeepView;dmPermitKeepView=false;
 const previousPermitView=overview?{center:overview.getCenter(),zoom:overview.getZoom(),nature:overview.dmNature?.enabled()}:null;
 dmRenderPermitTools();
 if(overview){overview.remove();overview=null;}
 if (!overview) {
  overview = L.map('overview-map').setView([47.8968, 16.3674], 13); tiles(overview); overviewLayers = L.layerGroup().addTo(overview);
  overview.on('click', e => { if (mapPointPick) { dmPickStart(e.latlng);return; } if (picking) { stopPicking(); openPoint(null, e.latlng); } });
 }
 overviewLayers.clearLayers(); const coords = [];
 for (const m of dmPermitMissions()) {
  if (dmDrawPermitMission(overview,m,overviewLayers,coords)) continue;
  const p = m.overviewPoint; if (!p) continue; coords.push([p.lat, p.lng]);
  L.marker([p.lat, p.lng], { icon: L.divIcon({ className: 'mission-marker-wrap', html: '<span class="mission-marker"></span>', iconSize: [16, 16], iconAnchor: [8, 8] }), keyboard: false }).addTo(overviewLayers).bindTooltip(esc(m.name)).on('click', () => run(() => openMission(m.id)));
 }
 for (const p of visiblePoints()) { coords.push([p.lat, p.lng]); L.marker([p.lat, p.lng], { icon: L.divIcon({ className: 'pano-marker', html: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="5"/><path d="M12 3v4M12 17v4M3 12h4M17 12h4"/></svg>', iconSize: [30, 30], iconAnchor: [15, 15] }), keyboard: false }).addTo(overviewLayers).bindTooltip(esc(p.name)).on('click', () => canEdit() ? openPoint(p) : openCustomerMission({ ...p, overviewPoint: p, locationOnly: true })); }
 const currentMap=overview;currentMap.dmKeepPermitView=keepPermitView;currentMap.dmFitProject=()=>{if(currentMap.dmDisposed||currentMap.dmKeepPermitView||picking||mapPointPick)return;const bounds=L.latLngBounds(coords);if(currentMap.dmReferenceBounds)bounds.extend(currentMap.dmReferenceBounds);if(bounds.isValid())currentMap.fitBounds(bounds,{padding:[45,45],maxZoom:17});};
 setTimeout(()=>{if(currentMap.dmDisposed)return;currentMap.invalidateSize();if(keepPermitView&&previousPermitView)currentMap.setView(previousPermitView.center,previousPermitView.zoom,{animate:false});else currentMap.dmFitProject();if(previousPermitView?.nature)currentMap.dmNature?.enable();},80);
}
function stopPicking() { picking = false; $('#overview-map').classList.remove('picking'); $('#add-point span').textContent = 'Planungspunkt'; }

/* ---------- Höhenprofil ---------- */
function chart(details) {
 if (details.previewAvailable === false) return '<p class="chart-empty">Originalprojekt gesichert. Route und Höhenprofil sind für dieses Projektformat nicht ausgelesen. Für die Vorschau einen DJI-KMZ-Export zuordnen.</p>';
 const pts = details.points, valid = pts.filter(p => p.height !== null);
 if (!valid.length) return '<p class="chart-empty">Keine Höhenwerte in der ausführbaren Flugroute gefunden.</p>';
 const heights = valid.map(p => p.height); let lo = Math.min(...heights), hi = Math.max(...heights); if (hi - lo < 2) { lo -= 1; hi += 1; }
 const W = 760, H = 220, L0 = 46, R = 16, T = 18, B = 34, pw = W - L0 - R, ph = H - T - B;
 let dist = 0; const ds = [0];
 for (let i = 1; i < pts.length; i++) { if (!details.routes.some(r => r.start === i)) dist += L.latLng(pts[i - 1].lat, pts[i - 1].lng).distanceTo([pts[i].lat, pts[i].lng]); ds.push(dist); }
 const x = i => L0 + ds[i] / Math.max(dist, 1) * pw, y = h => T + ph - (h - lo) / (hi - lo) * ph;
 const ticks = [lo, (lo + hi) / 2, hi];
 const grid = ticks.map(t => `<line class="grid" x1="${L0}" x2="${W - R}" y1="${y(t).toFixed(1)}" y2="${y(t).toFixed(1)}"/><text x="${L0 - 8}" y="${(y(t) + 4).toFixed(1)}" text-anchor="end">${Math.round(t)} m</text>`).join('');
 const paths = details.routes.map((r, ri) => { let d = '', area = '', active = false, first = null, last = null; for (let i = r.start; i < r.start + r.count; i++) { if (pts[i].height === null) { active = false; continue; } const px = x(i).toFixed(1), py = y(pts[i].height).toFixed(1); d += `${active ? 'L' : 'M'}${px},${py} `; if (first === null) first = px; last = px; active = true; } if (first !== null) area = `M${first},${T + ph} ${d.replace(/M/g, 'L')} L${last},${T + ph} Z`; const c = ROUTE_COLORS[ri % ROUTE_COLORS.length]; return `<path class="area" d="${area}" fill="${c}"/><path class="line" d="${d}" stroke="${c}"/>`; }).join('');
 const samples = pts.map((p, i) => p.height === null ? null : [+x(i).toFixed(1), +y(p.height).toFixed(1), i]).filter(Boolean);
 const legend = details.routes.length > 1 ? `<div class="chart-legend">${details.routes.map((r, i) => `<span><i style="background:${ROUTE_COLORS[i % ROUTE_COLORS.length]}"></i>Flugroute ${esc(r.id || i + 1)}</span>`).join('')}</div>` : '';
 return `<div class="chart" data-samples="${esc(JSON.stringify(samples))}" data-dist="${esc(JSON.stringify(ds.map(v => Math.round(v))))}"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Höhenprofil der gespeicherten Missionshöhen">${grid}<line class="axis" x1="${L0}" x2="${W - R}" y1="${T + ph}" y2="${T + ph}"/>${paths}<line class="cursor" x1="0" x2="0" y1="${T}" y2="${T + ph}"/><circle class="dot" r="4.5" cx="0" cy="0" stroke="${ROUTE_COLORS[0]}"/><text x="${L0}" y="${H - 10}">Start</text><text x="${W - R}" y="${H - 10}" text-anchor="end">${km(dist, 2)}</text></svg><div class="chart-tip"></div></div>${legend}<p class="hint">Höhenbezug: ${esc(details.heightMode)}. Gespeicherte Missionshöhe, kein Geländeprofil. Strecke ohne Start-/Rückflug.</p>`;
}
function bindChart(root, details) {
 const box = $('.chart', root); if (!box) return;
 const svg = $('svg', box), cursor = $('.cursor', box), dot = $('.dot', box), tip = $('.chart-tip', box);
 const samples = JSON.parse(box.dataset.samples), ds = JSON.parse(box.dataset.dist); if (!samples.length) return;
 const move = e => {
  const rect = svg.getBoundingClientRect(), vb = svg.viewBox.baseVal, px = (e.clientX - rect.left) / rect.width * vb.width;
  let best = samples[0]; for (const s of samples) if (Math.abs(s[0] - px) < Math.abs(best[0] - px)) best = s;
  cursor.setAttribute('x1', best[0]); cursor.setAttribute('x2', best[0]); dot.setAttribute('cx', best[0]); dot.setAttribute('cy', best[1]);
  const p = details.points[best[2]];
  tip.innerHTML = `<b>Wegpunkt ${best[2] + 1}</b> ${p.height} m · ${km(ds[best[2]], 2)}${p.speed ? ` · ${nf.format(p.speed)} m/s` : ''}`;
  const left = Math.min(Math.max(best[0] / vb.width * rect.width - tip.offsetWidth / 2, 4), rect.width - tip.offsetWidth - 4);
  tip.style.left = `${left + 10}px`; tip.style.top = `${Math.max(best[1] / vb.height * rect.height - tip.offsetHeight - 12, 2)}px`; box.classList.add('hover');
 };
 svg.addEventListener('pointermove', move); svg.addEventListener('pointerdown', move); svg.addEventListener('pointerleave', () => box.classList.remove('hover'));
}

/* ---------- Kundenansicht (Lesefreigabe): nur Standort und Navigation ---------- */
function openCustomerMission(m) {
 const p = m.overviewPoint||m.takeoffPoint;
 $('#detail-content').innerHTML = `<div class="dialog-head"><div><div class="eyebrow">${esc(pathFor(m.folder) || 'Standort')}</div><h2>${esc(m.name)}</h2></div><button class="btn btn-icon" type="button" data-close aria-label="Schließen">${icon('i-close')}</button></div><div class="dialog-body"><div id="customer-map" class="detail-map"></div><p class="num hint" style="margin-top:.6rem">${Number(p.lat).toFixed(5)}, ${Number(p.lng).toFixed(5)}</p>${navigation(m)}<p class="notice">${icon('i-info')}<span>Navigation zum freigegebenen Ort. Flugroute und Missionsdatei sind nicht Teil dieser Freigabe.</span></p></div>`;
 if (detailMap) { detailMap.remove(); detailMap = null; }
 const dlg = $('#detail-dialog'); dlg.classList.add('dialog-customer'); if (!dlg.open) dlg.showModal();
 setTimeout(() => { if (!$('#customer-map')) return; detailMap = L.map('customer-map').setView([p.lat, p.lng], 16); tiles(detailMap,m.folder); L.marker([p.lat, p.lng], { icon: L.divIcon({ className: 'mission-marker-wrap', html: '<span class="mission-marker"></span>', iconSize: [18, 18], iconAnchor: [9, 9] }), keyboard: false }).addTo(detailMap).bindTooltip(esc(m.name)); }, 60);
}

/* ---------- Missionsdetails ---------- */
async function openMission(id) {
 selected = data.missions.find(m => m.id === id); if (!selected) return; const m = selected;
 if (!canEdit()) { openCustomerMission(m); return; }
 if (sourceType(m)==='KMZ' && !Array.isArray(m.details.pois)) {
  const extra=await api('preview-details&id='+encodeURIComponent(m.id));
  if (!selected || selected.id!==id) return;
  if (extra.versionId!==m.versionId) throw Error('Mission wurde inzwischen geändert. Bitte Bibliothek neu laden.');
  m.details.pois=extra.pois;
 }

 $('#detail-dialog').classList.remove('dialog-customer');
 const native = isNative(m), type = sourceType(m), archived = m.archived, kmz = type === 'KMZ';
 const sources = data.missions.filter(x => isProject(x) && !x.archived && x.id !== m.id);
 const formatLabel = kmz ? `DJI KMZ · Gerät ${esc(m.details.droneEnum ?? 'unbekannt')} / ${esc(m.details.droneSubEnum ?? 'unbekannt')}` : type === 'MPROJ' ? `Map Creator · Originalprojekt${m.details.planningType ? ` (${esc(m.details.planningType)}, ${plural(m.details.planningVertexCount || 0, 'Eckpunkt', 'Eckpunkte')})` : ''}` : `Litchi ${type} · Originalexport`;
 const litchiLink = m.litchi_url ? `<a class="btn btn-outline" href="${esc(m.litchi_url)}" target="_blank" rel="noreferrer noopener">${icon('i-external')}<span>In Litchi öffnen</span></a>` : type.startsWith('LCH') ? `<a class="btn btn-outline" href="https://hub.flylitchi.com/" target="_blank" rel="noreferrer noopener">${icon('i-external')}<span>Litchi öffnen</span></a>` : '';
 $('#detail-content').innerHTML = `
  <div class="dialog-head"><div><div class="eyebrow">${esc(pathFor(m.folder) || 'Ohne Projekt')} · Version ${m.version}</div><h2>${esc(m.name)}</h2></div><button class="btn btn-icon" type="button" data-close aria-label="Schließen">${icon('i-close')}</button></div>
  <div class="dialog-body">
   <div class="detail-grid">
    <div>
     <div id="detail-map" class="detail-map"></div>
     <section class="detail-section"><div class="detail-section-head"><h3>${icon('i-route')}Höhenprofil</h3><p class="hint">Zeiger über das Profil bewegen für Wegpunkt-Details.</p></div><div id="chart-root">${chart(m.details)}</div></section>
     <section class="detail-section files">
      <div class="detail-section-head"><h3>${icon('i-file')}Dateien dieser Mission</h3>${m.details.plannerId?`<button type="button" class="btn btn-outline btn-sm" data-planner-id="${esc(m.details.plannerId)}">Planung bearbeiten</button>`:''}<button type="button" class="btn btn-outline btn-sm" id="edit-preview">Vorschau einstellen</button></div>
      <div class="file-row"><span class="badge badge-muted">${type}</span><span class="name">${esc(m.filename)}</span><span class="size">${fmtBytes(Number(m.bytes))}</span><a class="btn btn-outline btn-sm" href="api.php?action=original&id=${m.id}">${icon('i-download')}<span>Original</span></a></div>
      ${(m.attachments || []).map(a => `<div class="file-row"><span class="badge badge-muted">${esc(a.format.toUpperCase())}</span><span class="name">${esc(a.filename)}<small>Projektdatei</small></span><span class="size">${fmtBytes(Number(a.bytes))}</span><a class="btn btn-outline btn-sm" href="api.php?action=attachment&id=${m.id}&version=${a.id}">${icon('i-download')}<span>Projektdatei</span></a></div>`).join('')}
      ${kmz && sources.length ? `<div class="attach-row"><label class="field"><span>Projektdatei zuordnen</span><select id="source-attachment"><option value="">Vorhandene Projektdatei auswählen …</option>${sources.map(x => `<option value="${x.id}">${esc(pathFor(x.folder) || 'Ohne Projekt')} / ${esc(x.name)} · ${esc(x.filename)}</option>`).join('')}</select></label><button id="attach-source" class="btn btn-outline" type="button" data-busy="Wird zugeordnet …">${icon('i-link')}<span>Zugehörige Dateien hinzufügen</span></button></div><p class="hint">Die Projektdatei (MPROJ, LCHM, LCHZ) gehört danach zu dieser KMZ-Mission. Ihr bisheriger Eintrag wandert ins Archiv, Originale bleiben unverändert.</p>` : kmz ? '<p class="hint">Map-Creator- oder Litchi-Projektdateien lassen sich dieser Mission zuordnen, sobald eine als eigener Eintrag hochgeladen wurde.</p>' : '<p class="hint">Für die Übertragung auf DJI Fly wird ein DJI-KMZ-Export benötigt. Diese Projektdatei kann einer KMZ-Mission zugeordnet werden.</p>'}
     </section>
    </div>
    <div class="detail-side">
     <div class="detail-stats"><div class="detail-stat"><strong>${m.details.count ?? '—'}</strong><span>Wegpunkte</span></div><div class="detail-stat"><strong>${native ? '—' : km(m.details.distance, 2)}</strong><span>Route</span></div><div class="detail-stat"><strong>${m.details.estimatedSeconds ? `${Math.round(m.details.estimatedSeconds / 60)} min` : '—'}</strong><span>Flugzeit ca.</span></div></div>
     <div class="detail-form">
      <label class="field"><span>Missionsname</span><input id="mission-name" value="${esc(m.name)}" maxlength="200"></label>
      <label class="field"><span>Projektordner</span><select id="mission-folder">${folderOptions(m.folder)}</select></label>
      <label class="field"><span>Punkt für Projektkarte <em>Kunden &amp; Navigation</em></span><select id="mission-overview" ${kmz ? '' : 'disabled'}><option value="">Nicht in der Projektkarte anzeigen</option>${kmz ? m.details.points.map((p, i) => `<option value="${i}" ${m.overviewPoint && Number(m.overview_waypoint) === i ? 'selected' : ''}>Wegpunkt ${i + 1} · ${Number(p.lat).toFixed(5)}, ${Number(p.lng).toFixed(5)}</option>`).join('') : ''}</select></label>
      <p class="hint">${kmz ? 'Nur dieser Punkt wird für Kunden und Navigation freigegeben. Wegpunkt auch direkt auf der Karte anklicken. Nach einer neuen Dateiversion erneut auswählen.' : 'Nur DJI-KMZ-Missionen können einen Punkt für die Projektkarte freigeben.'}</p>
      <button id="mission-single-map" type="button" class="btn btn-outline">Missionskarte &amp; PDF</button><button id="mission-set-start" type="button" class="btn btn-outline"><span class="start-h-icon" aria-hidden="true">H</span>Startplatz auf Karte setzen</button><label class="field"><span>Litchi-Hub-Link <em>optional</em></span><input id="mission-litchi" value="${esc(m.litchi_url || '')}" inputmode="url" placeholder="https://hub.flylitchi.com/?m=…"></label>
      ${m.takeoffPoint?'<p class="hint">Freigabekarte: separater Startplatz und fest Wegpunkt 2 als Aufnahmepunkt.</p>':''}<label class="field"><span>Notizen</span><textarea id="mission-notes" rows="3" maxlength="20000" placeholder="Startpunkt, Besonderheiten, Freigaben …">${esc(m.notes)}</textarea></label>
      <button id="save-mission" class="btn btn-primary btn-block" type="button" data-busy="Wird gespeichert …">${icon('i-check')}<span>Änderungen speichern</span></button>
     </div>
     <dl class="facts">
      <dt>Quell-UUID</dt><dd><span>${esc(m.details.sourceUUID || 'Keine UUID im Dateinamen')}</span></dd>
      <dt>Format</dt><dd><span>${formatLabel}</span></dd>
      <dt>SHA-256</dt><dd><span class="mono">${esc(m.sha256)}</span><button class="btn btn-icon btn-xs" type="button" data-copy="${esc(m.sha256)}" title="Prüfsumme kopieren" aria-label="Prüfsumme kopieren">${icon('i-copy')}</button></dd>
      <dt>Geändert</dt><dd><span>${timeEl(m.updated, true)}</span></dd>
     </dl>
     <p class="notice">${icon('i-shield')}<span>Dateiintegrität geprüft. Kompatibilität und Darstellung in DJI Fly sind damit noch nicht bestätigt.</span></p>
     ${m.overviewPoint ? `<div class="detail-nav"><h3>${icon('i-navigate')}Navigation zum Standort</h3>${navigation(m)}</div>` : ''}
    </div>
   </div>
   <div id="versions" class="versions"></div>
  </div>
  <div class="dialog-foot detail-actions">
   <a class="btn btn-primary" href="api.php?action=original&id=${m.id}">${icon('i-download')}<span>${type} herunterladen</span></a>
   <a class="btn btn-outline" href="api.php?action=package&id=${m.id}">${icon('i-download')}<span>Archivpaket</span></a>
   ${litchiLink}
   ${type==='KMZ'&&canEdit()?'<button id="edit-kmz" class="btn btn-outline" type="button">Wegpunkte bearbeiten</button>':''}
   <button id="new-version" class="btn btn-outline" type="button">${icon('i-plus')}<span>Neue Version</span></button>
   <button id="archive-mission" class="btn btn-outline" type="button">${icon(archived ? 'i-restore' : 'i-archive')}<span>${archived ? 'Wiederherstellen' : 'Archivieren'}</span></button>
   <span class="hint">USB-Übertragung über die Bridge-App</span>
  </div>`;
 if (detailMap) { detailMap.remove(); detailMap = null; }
 const dlg = $('#detail-dialog'); if (!dlg.open) dlg.showModal(); $('.dialog-body', dlg).scrollTop = 0; syncHash();
 bindChart($('#chart-root'), m.details);
 setTimeout(() => {
  if (!dlg.open || selected?.id !== m.id) return;
  const el = $('#detail-map');
  if (!m.details.points.length) { el.innerHTML = `${icon('i-file')}<span>Originalprojekt gesichert. Für die Routenvorschau einen DJI-KMZ-Export zuordnen.</span>`; el.classList.add('native-preview'); return; }
  detailMap = L.map('detail-map'); tiles(detailMap,m.folder); const coords = drawRoute(detailMap, m); detailMap.fitBounds(coords, { padding: [35, 35], maxZoom: 18 });
 }, 60);
 $('#save-mission').onclick = e => run(async () => { await api('mission', { id: m.id, revision: m.revision, name: $('#mission-name').value, folder: $('#mission-folder').value, notes: $('#mission-notes').value, overviewWaypoint: $('#mission-overview').value === '' ? null : Number($('#mission-overview').value), litchiURL: $('#mission-litchi').value.trim() }); dlg.close(); await refresh(); toast('Name und Metadaten gespeichert. Originaldatei unverändert.'); }, e.currentTarget);
 $('#new-version').onclick = () => openUpload(m);
 const editKmz=$('#edit-kmz');if(editKmz)editKmz.onclick=()=>run(()=>window.dmKmzEditor.open(m.id));
 $('#archive-mission').onclick = e => run(async () => { await api('mission', { id: m.id, revision: m.revision, archived: !m.archived }); dlg.close(); await refresh(); toast(m.archived ? 'Mission wiederhergestellt.' : 'Mission archiviert. Originaldateien bleiben erhalten.'); }, e.currentTarget);
 const singleMapButton=$('#mission-single-map');if(singleMapButton)singleMapButton.onclick=()=>dmOpenMissionMap(m);
 const startButton=$('#mission-set-start');if(startButton)startButton.onclick=()=>{const id=m.id;$('#detail-dialog').close();folder=m.folder;view=folder?'folder':'all';setMode(true);dmBeginStartPick(id);};
 const attach = $('#attach-source'); if (attach) attach.onclick = e => run(async () => { const source = data.missions.find(x => x.id === $('#source-attachment').value); if (!source) throw Error('Bitte eine Projektdatei auswählen.'); await api('attach-source', { target: m.id, targetRevision: m.revision, source: source.id, sourceRevision: source.revision }); await refresh(); await openMission(m.id); toast('Projektdatei und KMZ gehören jetzt zu einem Missionseintrag. Originale unverändert.'); }, e.currentTarget);
 await renderVersions(m.id);
}
async function renderVersions(id) {
 const d = await api(`versions&id=${encodeURIComponent(id)}`);
 $('#versions').innerHTML = `<h3>${icon('i-history')}Versionsverlauf</h3>` + d.versions.map(v => `<div class="version-row"><span class="badge badge-muted">V${v.ordinal}</span><span class="name">${esc(v.filename)}</span><span class="size">${fmtBytes(Number(v.bytes))}</span>${timeEl(v.created, true)}<a class="btn btn-outline btn-sm" href="api.php?action=original&id=${id}&version=${v.id}">${icon('i-download')}<span>Original</span></a></div>`).join('');
}

/* ---------- Dialoge ---------- */
function fileLabel(input) {
 const text = input.parentElement.querySelector('.file-drop-text'), drop = input.parentElement.querySelector('.file-drop'), f = input.files?.[0];
 text.textContent = f ? `${f.name} · ${fmtBytes(f.size)}` : text.dataset.empty; drop.classList.toggle('has-file', !!f);
}
function openUpload(m = null) {
 if (!canEdit()) return; uploadMission = m; const f = $('#upload-form'); f.reset(); $$('input[type=file]', f).forEach(fileLabel);
 $('#upload-title').textContent = m ? 'Neue Originalversion' : 'Mission hinzufügen';
 f.elements.name.value = m?.name || ''; f.elements.folder.innerHTML = folderOptions(m?.folder || folder || data.scope); f.elements.folder.disabled = !!m;
 $('#upload-dialog').showModal();
}
function openFolder(existing = null, root = false) {
 editFolder = existing; const f = $('#folder-form'); f.reset(); $('#folder-title').textContent = existing ? 'Ordner bearbeiten' : root ? 'Neues Projekt' : 'Neuer Unterordner';
 f.elements.name.value = existing?.name || ''; f.elements.parent.innerHTML = folderOptions(existing?.parent || (root ? data.scope : folder) || data.scope, existing?.id);
 const a = $('#archive-folder'); a.classList.toggle('hidden', !existing); $('span', a).textContent = Number(existing?.archived) ? 'Ordner wiederherstellen' : 'Ordner archivieren'; $('use', a).setAttribute('href', Number(existing?.archived) ? '#i-restore' : '#i-archive');
 $('#delete-folder').classList.toggle('hidden', !existing || !isOwner());
 $('#folder-dialog').showModal(); f.elements.name.focus();
}
function openPoint(p = null, coords = null) {
 editPoint = p; const f = $('#point-form'); f.reset(); const settings = p?.settings || {};
 $('#point-title').textContent = p ? p.name : 'Neuer Planungspunkt';
 for (const k of ['name', 'notes', 'lat', 'lng']) f.elements[k].value = p?.[k] ?? (k === 'lat' ? coords?.lat?.toFixed(6) : k === 'lng' ? coords?.lng?.toFixed(6) : '') ?? '';
 for (const k of ['height', 'heightMode', 'heading', 'gimbal', 'capture']) f.elements[k].value = settings[k] ?? ({ height: 60, heightMode: 'relativeToStartPoint', heading: 0, gimbal: -90, capture: 'sphere' }[k]);
 for (const e of [...f.elements]) if (e.name) e.disabled = !canEdit();
 $('button[type=submit]', f).classList.toggle('hidden', !canEdit()); $('#delete-point').classList.toggle('hidden', !p || !canEdit());
 $('#point-dialog').showModal();
}
async function loadShareList() {
 const d = await api('shares');
 $('#share-list').innerHTML = `<h3>Aktive Freigaben</h3>` + (d.shares.map(s => `<div class="share-row"><div><strong>${esc(s.name)}</strong><small>${s.role === 'edit' ? 'Administratoren · bearbeiten' : 'Kunden · Orte & Navigation'} · gültig bis ${esc(new Date(s.expires * 1000).toLocaleDateString('de-AT'))}</small></div><button class="btn btn-outline btn-sm btn-danger" type="button" data-revoke="${s.id}">Widerrufen</button></div>`).join('') || '<p class="hint">Noch keine Projektfreigaben. Wähle oben ein Projekt und erstelle einen Link.</p>');
}
async function openShares() {
 $('#share-link-wrap').classList.add('hidden');
 const select = $('#share-folder'); select.innerHTML = folderOptions(folder || data.scope).replace('<option value="">Ohne Projektordner</option>', '<option value="">Projekt auswählen …</option>'); select.value = folder || data.scope || '';
 const dlg = $('#share-dialog'); if (!dlg.open) dlg.showModal();
 await loadShareList();
}

/* ---------- Navigation / Seitenleiste ---------- */
function openSidebar() { $('#sidebar').classList.add('open'); const s = $('#scrim'); s.hidden = false; requestAnimationFrame(() => s.classList.add('on')); $('#menu-toggle').setAttribute('aria-expanded', 'true'); }
function closeSidebar() { $('#sidebar').classList.remove('open'); const s = $('#scrim'); s.classList.remove('on'); setTimeout(() => { s.hidden = true; }, 200); $('#menu-toggle').setAttribute('aria-expanded', 'false'); }
$('#menu-toggle').onclick = () => $('#sidebar').classList.contains('open') ? closeSidebar() : openSidebar();
$('#scrim').onclick = closeSidebar;
function setSidebarCollapsed(collapsed) {
 document.body.classList.toggle('sidebar-collapsed', collapsed); const b = $('#sidebar-toggle');
 b.setAttribute('aria-expanded', String(!collapsed)); b.setAttribute('aria-label', collapsed ? 'Seitenleiste ausklappen' : 'Seitenleiste einklappen'); b.title = b.getAttribute('aria-label');
 if (overview) setTimeout(() => overview.invalidateSize(), 220);
}
try { setSidebarCollapsed(localStorage.getItem('dm-sidebar-collapsed') === 'true'); } catch { /* ignorieren */ }
$('#sidebar-toggle').onclick = () => { const collapsed = !document.body.classList.contains('sidebar-collapsed'); try { localStorage.setItem('dm-sidebar-collapsed', String(collapsed)); } catch { /* ignorieren */ } setSidebarCollapsed(collapsed); };
function showLibrary() { $('#login').classList.add('hidden'); $('#shell').classList.remove('hidden'); if (!loaded) renderSkeleton(); }

/* ---------- Ereignisse ---------- */
$('#login-form').onsubmit = e => { e.preventDefault(); const b = $('button[type=submit]', e.target); run(async () => { try { const d = await api('login', { password: $('#password').value }); csrf = d.csrf; $('#password').value = ''; $('#login-error').textContent = ''; showLibrary(); await refresh(); applyHash(); dmApplyPermitView(); } catch (err) { $('#login-error').textContent = err.message; $('#password').focus(); } }, b); };
$('#settings').onclick = () => run(async () => { const d = await api('settings'); $('#settings-form').elements.authorName.value = d.authorName; $('#settings-dialog').showModal(); });
$('#settings-form').onsubmit = e => { e.preventDefault(); run(async () => { await api('settings', { authorName: e.target.elements.authorName.value }); location.reload(); }, $('button[type=submit]', e.target)); };
$('#logout').onclick = () => run(async () => { await api('logout', {}); location.href = location.pathname; });
$$('[data-view]').forEach(b => b.onclick = () => navigate(b.dataset.view));
$('#folders').onclick = e => { const b = e.target.closest('[data-folder]'); if (b) navigate('folder', b.dataset.folder); };
$('#breadcrumb').onclick = e => { const b = e.target.closest('[data-nav]'); if (b) navigate(b.dataset.nav, b.dataset.navFolder || null); };
$('#search').oninput = render;
$('#search').onkeydown = e => { if (e.key === 'Escape' && e.target.value) { e.target.value = ''; render(); } };
$('#filters').onclick = e => { const c = e.target.closest('[data-filter]'); if (c) { filter = c.dataset.filter; render(); } };
$('#sort').onchange = e => { sort = e.target.value; render(); };
$('#empty-clear').onclick = () => { $('#search').value = ''; filter = 'all'; render(); };
$('#upload').onclick = () => openUpload(); $('#upload-compact').onclick = () => openUpload(); $('#empty-upload').onclick = () => openUpload();
$('#new-project').onclick = () => openFolder(null, true); $('#add-folder').onclick = () => openFolder(); $('#folder-options').onclick = () => openFolder(folderById(folder));
$('#cards').onclick = e => {
 const open=e.target.closest('[data-open-list]');if(open){run(()=>openMission(open.dataset.openList));return;}
 if (e.target.closest('.card-select,.list-check')) return;
 const chip = e.target.closest('[data-project]'); if (chip) { if (chip.dataset.project) navigate('folder', chip.dataset.project); else { $('#search').value = ''; filter = 'all'; navigate('unfiled'); } return; }
 if (e.target.closest('a,button,input,select')) return;
 const m = e.target.closest('[data-mission]'), p = e.target.closest('[data-point]');
 if (m) run(() => openMission(m.dataset.mission));
 if (p) { const point = data.points.find(x => x.id === p.dataset.point); if (canEdit()) openPoint(point); else openCustomerMission({ ...point, overviewPoint: point, locationOnly: true }); }
};
$('#cards').onkeydown = e => {const grip=e.target.closest('[data-order-grip]');if(grip&&['ArrowUp','ArrowDown'].includes(e.key)){e.preventDefault();const rows=visibleMissions(),i=rows.findIndex(m=>m.id===grip.dataset.orderGrip),target=rows[i+(e.key==='ArrowUp'?-1:1)];if(target)dmMoveMissionOrder(grip.dataset.orderGrip,target.id,rows);return;} if (e.target.closest('input,button,a,select')) return; if ((e.key === 'Enter' || e.key === ' ') && e.target.matches('[role=button]')) { e.preventDefault(); e.target.click(); } };
function setMode(map,list=false) { showMap = map;showList=!map&&list;document.body.classList.toggle('mission-list-active',showList);$('#list-toggle').classList.toggle('selected',showList);$('#list-toggle').setAttribute('aria-pressed',String(showList)); if (!map) stopPicking(); $('#cards-toggle').classList.toggle('selected', !map&&!showList); $('#map-toggle').classList.toggle('selected', map); $('#cards-toggle').setAttribute('aria-pressed', String(!map&&!showList)); $('#map-toggle').setAttribute('aria-pressed', String(map)); render(); }
$('#list-toggle').onclick=()=>setMode(false,true);$('#cards-toggle').onclick = () => setMode(false); $('#map-toggle').onclick = () => setMode(true);
$('#add-point').onclick = () => { if (picking) { stopPicking(); return; } showMap = true; picking = true; setMode(true); $('#overview-map').classList.add('picking'); $('#add-point span').textContent = 'Auf die Karte klicken …'; toast('Klicke auf die Karte, um den Panorama-Standort zu setzen.'); };
document.addEventListener('keydown', e => { if (e.key === '/' && !e.ctrlKey && !e.metaKey && !e.altKey && !$('dialog[open]') && !/^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName)) { e.preventDefault(); $('#search').focus(); } });

/* Dateifelder */
$$('.field-file input[type=file]').forEach(input => { input.onchange = () => { fileLabel(input); if (input.name === 'kmz' && !uploadMission) $('#upload-form').elements.name.value = input.files[0]?.name.replace(/\.(kmz|csv|lchm|lchz|mproj)$/i, '') || ''; }; });
$$('.field-file').forEach(field => { const input = $('input[type=file]', field); ['dragenter', 'dragover'].forEach(t => field.addEventListener(t, e => { e.preventDefault(); field.classList.add('dragging'); })); ['dragleave', 'drop'].forEach(t => field.addEventListener(t, e => { e.preventDefault(); field.classList.remove('dragging'); })); field.addEventListener('drop', e => { if (e.dataTransfer.files.length) { input.files = e.dataTransfer.files; input.dispatchEvent(new Event('change')); } }); });

$('#upload-form').onsubmit = e => { e.preventDefault(); run(async () => { const form = new FormData(e.target); if (uploadMission) { form.set('mission', uploadMission.id); form.set('revision', uploadMission.revision); } await api('upload', form, true); $('#upload-dialog').close(); if ($('#detail-dialog').open) $('#detail-dialog').close(); await refresh(); toast(uploadMission ? 'Neue Version gesichert. Frühere Versionen bleiben erhalten.' : 'Mission gespeichert. Originaldatei und Prüfsumme gesichert.'); }, $('button[type=submit]', e.target)); };
$('#folder-form').onsubmit = e => { e.preventDefault(); run(async () => { const d = await api('folder', { name: e.target.elements.name.value, parent: e.target.elements.parent.value, id: editFolder?.id }); $('#folder-dialog').close(); folder = d.id; view = 'folder'; await refresh(); toast(editFolder ? 'Ordner gespeichert.' : 'Projekt angelegt.'); }, $('button[type=submit]', e.target)); };
$('#archive-folder').onclick = e => run(async () => { await api('folder-archive', { id: editFolder.id, archived: !Number(editFolder.archived) }); $('#folder-dialog').close(); await refresh(); toast('Projektstatus gespeichert. Dateien bleiben erhalten.'); }, e.currentTarget);
$('#delete-folder').onclick = async () => {
 const id = editFolder.id;
 if (data.folders.some(f => f.parent === id) || data.missions.some(m => m.folder === id) || data.points.some(p => p.folder === id)) { toast(`Dieser Ordner enthält noch Missionen, Planungspunkte oder Unterordner. Davon ${data.missions.filter(m => m.folder === id && m.archived).length} archivierte Missionen: unter „Archiv“ im selben Projektordner zu finden. Bitte Inhalte zuerst verschieben.`, true); return; }
 if (await confirmDialog('Leeren Ordner löschen?', `„${editFolder.name}“ wird endgültig entfernt. Vorhandene Freigabelinks dieses Ordners werden widerrufen.`, 'Endgültig löschen', true)) run(async () => { await api('folder-delete', { id, parent: editFolder.parent, name: editFolder.name }); $('#folder-dialog').close(); await refresh(); toast('Leerer Projektordner gelöscht.'); });
};
$('#point-form').onsubmit = e => { e.preventDefault(); run(async () => { const f = e.target.elements; const settings = { height: Number(f.height.value), heightMode: f.heightMode.value, heading: Number(f.heading.value), gimbal: Number(f.gimbal.value), capture: f.capture.value }; await api('point', { id: editPoint?.id, revision: editPoint?.revision, folder: editPoint?.folder || folder, name: f.name.value, notes: f.notes.value, lat: Number(f.lat.value), lng: Number(f.lng.value), settings }); $('#point-dialog').close(); await refresh(); toast('Panorama-Standort gespeichert. Noch keine ausführbare Flugmission.'); }, $('button[type=submit]', e.target)); };
$('#delete-point').onclick = async () => { if (await confirmDialog('Planungspunkt löschen?', `„${editPoint.name}“ wird endgültig entfernt. Dieser Schritt lässt sich nicht rückgängig machen.`, 'Endgültig löschen', true)) run(async () => { await api('point-delete', { id: editPoint.id, revision: editPoint.revision }); $('#point-dialog').close(); await refresh(); toast('Planungspunkt gelöscht.'); }); };
async function openBridge() {
 const dlg = $('#bridge-dialog'); if (!dlg.open) dlg.showModal();
 $('#bridge-files').innerHTML = '<p class="hint">Pakete werden geladen …</p>';
 const d = await api('bridge'); $('#bridge-url').textContent = `Archiv-Adresse: ${d.archiveURL}`;
 const label = { macos: 'macOS', windows: 'Windows', other: 'Paket' };
 $('#bridge-files').innerHTML = d.files.length ? d.files.map(f => `<div class="bridge-file">${icon('i-download')}<div><strong>${esc(f.name)}</strong><small>${esc(label[f.platform] || 'Paket')} · ${fmtBytes(Number(f.bytes))} · ${esc(fmtDate(f.modified))}</small><span class="mono">SHA-256 ${esc(f.sha256)}</span></div><a class="btn btn-primary btn-sm" href="api.php?action=bridge-file&name=${encodeURIComponent(f.name)}">${icon('i-download')}<span>Herunterladen</span></a></div>`).join('') : `<p class="notice">${icon('i-info')}<span>Noch kein App-Paket hinterlegt. Der Eigentümer legt gebaute Pakete (ZIP, DMG, EXE, MSI) im privaten Ordner „${esc(d.folder)}“ auf dem Server ab; sie erscheinen dann hier mit Prüfsumme.</span></p>`;
}
$('#bridge').onclick = () => run(openBridge);
$('#share-project').onclick = () => run(() => openShares()); $('#manage-shares').onclick = () => run(() => openShares());
$('#create-share').onclick = e => run(async () => { const target = $('#share-folder').value; if (!target) throw Error('Bitte zuerst ein Projekt auswählen.'); const d = await api('share', { folder: target, role: $('#share-role').value }); const u = new URL('./', location.href); u.hash = `share=${d.token}`; $('#share-link').value = u.href; $('#share-link-wrap').classList.remove('hidden'); $('#share-link').focus(); $('#share-link').select(); await loadShareList(); toast('Freigabe erstellt. Der Link wird nur hier angezeigt.'); }, e.currentTarget);
$('#copy-share').onclick = () => run(async () => { await navigator.clipboard.writeText($('#share-link').value); toast('Freigabelink kopiert.'); });
$('#share-list').onclick = async e => { const b = e.target.closest('[data-revoke]'); if (!b) return; if (await confirmDialog('Freigabe widerrufen?', 'Der Link wird sofort gesperrt, auch für bereits angemeldete Personen. Bereits heruntergeladene Dateien lassen sich nicht zurückrufen.', 'Widerrufen', true)) run(async () => { await api('revoke', { id: b.dataset.revoke }); await loadShareList(); toast('Freigabe widerrufen.'); }); };

/* Dialoge: Schließen über Kreuz, Abbrechen, Klick auf den Hintergrund; Prüfsumme kopieren */
document.addEventListener('click', e => {
 const close = e.target.closest('[data-close]'); if (close) { close.closest('dialog').close(); return; }
 const copy = e.target.closest('[data-copy]'); if (copy) run(async () => { await navigator.clipboard.writeText(copy.dataset.copy); toast('Prüfsumme kopiert.'); });
 if (e.target instanceof HTMLDialogElement && e.target.open) { const r = e.target.getBoundingClientRect(); if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) e.target.close(); }
});
$('#detail-dialog').addEventListener('close', () => { if (detailMap) { detailMap.remove(); detailMap = null; } selected = null; syncHash(); });

dmInitPermitMap();

/* ---------- Start ---------- */
run(async () => {
 const s = await api('session'); csrf = s.csrf;
 const token = new URLSearchParams(location.hash.slice(1)).get('share');
 if (token) {
  history.replaceState(null, '', location.pathname+location.search);
  try { const d = await api('share-login', { token }); csrf = d.csrf; history.replaceState(null, '', location.pathname+location.search); showLibrary(); await refresh(); dmApplyPermitView(); }
  catch (e) { $('#shell').classList.add('hidden'); $('#login').classList.remove('hidden'); $('#login-error').textContent = e.message; }
  return;
 }
 if (s.authenticated) { showLibrary(); await refresh(); applyHash(); dmApplyPermitView(); } else { $('#login').classList.remove('hidden'); $('#password').focus(); }
});

$('#project-reference').onclick=()=>{$('#settings').click();setTimeout(()=>{const f=$('#vector-folder');f.value=folder||'';f.closest('details').open=true;f.scrollIntoView({block:'center'});f.focus();},100);};
