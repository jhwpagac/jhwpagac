/**
 * Obsahový kalendár – Google Apps Script web app.
 * Dáta sú uložené v tejto Google Tabuľke (hárky „Klienti“ a „Prispevky“).
 *
 * ▶ DÔLEŽITÉ: zmeň heslo nižšie. Týmto heslom sa prihlasuješ ako správca.
 */
const HESLO = 'zmen-ma-123';

const SH_CLIENTS = 'Klienti';
const SH_POSTS = 'Prispevky';
const CLIENT_COLS = ['id', 'name', 'color', 'token'];
const POST_COLS = ['id', 'clientId', 'date', 'time', 'platforms', 'format', 'status', 'title', 'caption', 'links', 'notes'];

function doGet(e) {
  const t = HtmlService.createTemplateFromFile('Index');
  const token = String((e && e.parameter && e.parameter.k) || '').replace(/[^a-zA-Z0-9]/g, '').slice(0, 64);
  t.tokenJson = JSON.stringify(token);
  t.appUrlJson = JSON.stringify(ScriptApp.getService().getUrl()).replace(/</g, '\\u003c');
  return t.evaluate()
    .setTitle('Obsahový kalendár')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.DEFAULT);
}

// ---------- verejné funkcie volané zo stránky ----------

/** auth = {key: heslo} pre správcu alebo {token: kód klienta} pre majiteľa firmy */
function getData(auth) {
  ensureSheets_();
  const clients = readSheet_(SH_CLIENTS, CLIENT_COLS);
  const posts = readSheet_(SH_POSTS, POST_COLS).map(parsePost_);
  if (isAdmin_(auth)) return { admin: true, clients: clients, posts: posts };
  const token = auth && auth.token ? String(auth.token) : '';
  const client = token ? clients.find(function (c) { return c.token === token; }) : null;
  if (!client) throw new Error('NEPLATNY_ODKAZ');
  return {
    admin: false,
    clients: [{ id: client.id, name: client.name, color: client.color }],
    posts: posts.filter(function (p) { return p.clientId === client.id; })
      .map(function (p) { const c = Object.assign({}, p); delete c.notes; return c; })
  };
}

function checkLogin(key) { return key === HESLO; }

function savePost(key, post) {
  requireAdmin_(key);
  return withLock_(function () {
    const posts = readSheet_(SH_POSTS, POST_COLS).map(parsePost_);
    const clean = sanitizePost_(post);
    if (!clean.id) clean.id = 'p-' + Utilities.getUuid().slice(0, 8);
    const i = posts.findIndex(function (p) { return p.id === clean.id; });
    if (i >= 0) posts[i] = clean; else posts.push(clean);
    writeSheet_(SH_POSTS, POST_COLS, posts.map(serializePost_));
    return clean;
  });
}

function deletePost(key, id) {
  requireAdmin_(key);
  return withLock_(function () {
    const posts = readSheet_(SH_POSTS, POST_COLS).filter(function (p) { return p.id !== id; });
    writeSheet_(SH_POSTS, POST_COLS, posts);
    return true;
  });
}

/** Uloží zoznam klientov; klienti, ktorí v zozname chýbajú, sa zmažú aj s príspevkami. */
function saveClients(key, list) {
  requireAdmin_(key);
  return withLock_(function () {
    const old = readSheet_(SH_CLIENTS, CLIENT_COLS);
    const clients = (list || []).map(function (c) {
      const prev = old.find(function (o) { return o.id === c.id; });
      return {
        id: c.id || ('c-' + Utilities.getUuid().slice(0, 8)),
        name: String(c.name || 'Klient').slice(0, 80),
        color: /^#[0-9a-fA-F]{6}$/.test(c.color) ? c.color : '#4b5563',
        token: prev && prev.token ? prev.token : newToken_()
      };
    });
    writeSheet_(SH_CLIENTS, CLIENT_COLS, clients);
    const ids = clients.map(function (c) { return c.id; });
    const posts = readSheet_(SH_POSTS, POST_COLS).filter(function (p) { return ids.indexOf(p.clientId) >= 0; });
    writeSheet_(SH_POSTS, POST_COLS, posts);
    return clients;
  });
}

/** Vygeneruje klientovi nový odkaz (starý prestane fungovať). */
function resetClientLink(key, clientId) {
  requireAdmin_(key);
  return withLock_(function () {
    const clients = readSheet_(SH_CLIENTS, CLIENT_COLS);
    const c = clients.find(function (x) { return x.id === clientId; });
    if (c) c.token = newToken_();
    writeSheet_(SH_CLIENTS, CLIENT_COLS, clients);
    return clients;
  });
}

// ---------- pomocné ----------

function isAdmin_(auth) { return !!(auth && auth.key && auth.key === HESLO); }
function requireAdmin_(key) { if (key !== HESLO) throw new Error('NESPRAVNE_HESLO'); }
function newToken_() { return Utilities.getUuid().replace(/-/g, '').slice(0, 16); }
function withLock_(fn) {
  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try { return fn(); } finally { lock.releaseLock(); }
}

function sanitizePost_(p) {
  const links = (Array.isArray(p.links) ? p.links : []).filter(function (l) {
    return l && /^https?:\/\//i.test(String(l.url || ''));
  }).map(function (l) { return { label: String(l.label || '').slice(0, 120), url: String(l.url).slice(0, 2000) }; });
  return {
    id: p.id ? String(p.id) : '',
    clientId: String(p.clientId || ''),
    date: /^\d{4}-\d{2}-\d{2}$/.test(p.date) ? p.date : '',
    time: /^\d{2}:\d{2}$/.test(p.time) ? p.time : '',
    platforms: (Array.isArray(p.platforms) ? p.platforms : []).map(String),
    format: String(p.format || ''),
    status: String(p.status || 'napad'),
    title: String(p.title || '').slice(0, 200),
    caption: String(p.caption || '').slice(0, 5000),
    links: links,
    notes: String(p.notes || '').slice(0, 3000)
  };
}
function serializePost_(p) {
  return Object.assign({}, p, { platforms: (p.platforms || []).join(', '), links: JSON.stringify(p.links || []) });
}
function parsePost_(r) {
  let links = [];
  try { links = r.links ? JSON.parse(r.links) : []; } catch (e) { links = []; }
  return Object.assign({}, r, {
    platforms: r.platforms ? String(r.platforms).split(',').map(function (s) { return s.trim(); }).filter(String) : [],
    links: links
  });
}

function sheet_(name) { return SpreadsheetApp.getActiveSpreadsheet().getSheetByName(name); }

function readSheet_(name, cols) {
  const sh = sheet_(name);
  const last = sh.getLastRow();
  if (last < 2) return [];
  const tz = Session.getScriptTimeZone();
  return sh.getRange(2, 1, last - 1, cols.length).getValues()
    .filter(function (row) { return row[0] !== ''; })
    .map(function (row) {
      const o = {};
      cols.forEach(function (c, i) {
        let v = row[i];
        if (v instanceof Date) v = Utilities.formatDate(v, tz, c === 'time' ? 'HH:mm' : 'yyyy-MM-dd');
        o[c] = v === null || v === undefined ? '' : String(v);
      });
      return o;
    });
}

function writeSheet_(name, cols, objs) {
  const sh = sheet_(name);
  const last = sh.getLastRow();
  if (last > 1) sh.getRange(2, 1, last - 1, cols.length).clearContent();
  if (!objs.length) return;
  const rows = objs.map(function (o) { return cols.map(function (c) { return o[c] === undefined ? '' : String(o[c]); }); });
  sh.getRange(2, 1, rows.length, cols.length).setNumberFormat('@').setValues(rows);
}

/** Pri prvom spustení vytvorí hárky aj s ukážkovými dátami. */
function ensureSheets_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  if (ss.getSheetByName(SH_CLIENTS) && ss.getSheetByName(SH_POSTS)) return;
  [[SH_CLIENTS, CLIENT_COLS], [SH_POSTS, POST_COLS]].forEach(function (d) {
    let sh = ss.getSheetByName(d[0]);
    if (!sh) sh = ss.insertSheet(d[0]);
    sh.getRange(1, 1, 1, d[1].length).setValues([d[1]]).setFontWeight('bold');
    sh.setFrozenRows(1);
    sh.getRange(1, 1, 1000, d[1].length).setNumberFormat('@');
  });
  const today = new Date();
  const day = function (n) { const d = new Date(today); d.setDate(d.getDate() + n); return Utilities.formatDate(d, Session.getScriptTimeZone(), 'yyyy-MM-dd'); };
  writeSheet_(SH_CLIENTS, CLIENT_COLS, [
    { id: 'c-kaviaren', name: 'Kaviareň Zrnko (príklad)', color: '#c2410c', token: newToken_() },
    { id: 'c-fitko', name: 'FitBox Gym (príklad)', color: '#0e7490', token: newToken_() }
  ]);
  writeSheet_(SH_POSTS, POST_COLS, [
    { id: 'p1', clientId: 'c-kaviaren', date: day(1), time: '08:30', platforms: ['Instagram', 'Facebook'], format: 'Reel', status: 'schvalene', title: 'Nová zimná káva – škoricové latte', caption: 'Zima prišla aj do našej kaviarne ☕❄️\nOchutnajte novinku – škoricové latte s domácim sirupom.\n\n#kaviaren #zimnemenu', links: [{ label: 'Video – reel', url: 'https://drive.google.com/' }], notes: 'Hudba: trending audio z IG' },
    { id: 'p2', clientId: 'c-fitko', date: day(2), time: '18:00', platforms: ['Instagram', 'TikTok'], format: 'Reel', status: 'priprava', title: '3 cviky na chrbát s trénerom', caption: 'Bolí ťa chrbát z kancelárie? Skús tieto 3 cviky 💪', links: [{ label: 'Surové video', url: 'https://drive.google.com/' }], notes: 'Dostrihať, pridať titulky' },
    { id: 'p3', clientId: 'c-kaviaren', date: day(4), time: '12:00', platforms: ['Instagram'], format: 'Karusel', status: 'schvalenie', title: 'Ako pripravujeme espresso (5 krokov)', caption: 'Od zrnka po šálku ☕', links: [], notes: '' },
    { id: 'p4', clientId: 'c-fitko', date: day(-2), time: '17:00', platforms: ['Instagram'], format: 'Karusel', status: 'schvalene', title: 'Premena klientky Janky', caption: '3 mesiace, 1 cieľ 🔥', links: [], notes: '' }
  ].map(serializePost_));
}
