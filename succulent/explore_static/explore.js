/* succulent explore dashboard.
 *
 * Every value comes from devices, so it is only ever inserted as text
 * (textContent), never as HTML. No external libraries are used.
 */
(function () {
  'use strict';

  var app = document.getElementById('app');
  var content = document.getElementById('content');
  var errorBox = document.getElementById('error');
  var subtitle = document.getElementById('subtitle');
  var live = document.getElementById('live');
  var liveDot = document.getElementById('live-dot');
  var liveText = document.getElementById('live-text');
  var rangesBox = document.getElementById('ranges');
  var autoButton = document.getElementById('auto');
  var autoText = document.getElementById('auto-text');

  var config = {
    format: app.dataset.format,
    refresh: parseInt(app.dataset.refresh, 10) || 0,
    gallery: app.dataset.gallery === 'true',
    api: app.dataset.api,
    images: app.dataset.images,
    login: app.dataset.login
  };

  var RANGE_LABELS = { '1h': '1 h', '24h': '24 h', '7d': '7 d', '30d': '30 d', all: 'All' };
  var SVG = 'http://www.w3.org/2000/svg';

  var state = {
    range: readStored('range') || '24h',
    auto: readStored('auto') !== 'false',
    timer: null,
    loading: false,
    lastData: null,
    fetchedAt: 0
  };

  // ------------------------------------------------------------------
  // Helpers
  // ------------------------------------------------------------------

  function readStored(key) {
    try { return window.localStorage.getItem('succulent-explore-' + key); } catch (e) { return null; }
  }

  function store(key, value) {
    try { window.localStorage.setItem('succulent-explore-' + key, value); } catch (e) { /* ignore */ }
  }

  /* Create an element. `text` is always set as plain text. */
  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  function svgEl(tag, attrs) {
    var node = document.createElementNS(SVG, tag);
    Object.keys(attrs || {}).forEach(function (key) { node.setAttribute(key, attrs[key]); });
    return node;
  }

  function append(parent) {
    for (var i = 1; i < arguments.length; i++) {
      if (arguments[i]) parent.appendChild(arguments[i]);
    }
    return parent;
  }

  function isNumber(v) { return typeof v === 'number' && isFinite(v); }

  function fmt(v) {
    if (v === null || v === undefined || v === '') return '—';
    if (!isNumber(v)) {
      var n = Number(v);
      if (typeof v === 'string' && v.trim() !== '' && isFinite(n)) v = n; else return String(v);
    }
    if (Math.abs(v) >= 100) return String(Math.round(v));
    return String(Number(v.toFixed(2)));
  }

  /* Number of decimals used by a column (0–2), from its raw values. */
  function decimalsOf(values) {
    var most = 0;
    values.forEach(function (v) {
      var n = toNumber(v);
      if (n === null || Math.abs(n) >= 100) return;
      var text = String(Number(n.toFixed(2)));
      var dot = text.indexOf('.');
      if (dot >= 0) most = Math.max(most, text.length - dot - 1);
    });
    return Math.min(most, 2);
  }

  /* Format a value with the column's number of decimals. */
  function fmtCol(v, column) {
    var n = toNumber(v);
    if (n === null || !column || column.decimals === undefined) return fmt(v);
    return Math.abs(n) >= 100 ? String(Math.round(n)) : n.toFixed(column.decimals);
  }

  /* Round chart limits to 4 or 5 evenly spaced intervals with round values. */
  function niceScale(lo, hi) {
    var span = hi - lo || Math.abs(hi) || 1;
    var power = Math.pow(10, Math.floor(Math.log10(span / 5)));
    var steps = [1, 2, 2.5, 5];
    for (var k = 0; k < 3; k++, power *= 10) {
      for (var i = 0; i < steps.length; i++) {
        var step = steps[i] * power;
        var low = Math.floor(lo / step + 1e-9) * step;
        for (var n = 4; n <= 5; n++) {
          if (low + n * step >= hi - 1e-9) return { lo: low, hi: low + n * step, step: step, n: n };
        }
      }
    }
    return { lo: lo, hi: hi, step: span / 4, n: 4 };
  }

  /* Format a tick value with as many decimals as the step needs. */
  function tick(v, step) {
    var text = String(Number(step.toPrecision(6)));
    var digits = text.indexOf('e-') >= 0 ? Number(text.split('e-')[1]) + 2
      : (text.indexOf('.') >= 0 ? text.length - text.indexOf('.') - 1 : 0);
    return String(Number(v.toFixed(Math.min(digits, 8))));
  }

  function toNumber(v) {
    if (isNumber(v)) return v;
    if (typeof v === 'string' && v.trim() !== '' && isFinite(Number(v))) return Number(v);
    return null;
  }

  function parseTime(text) {
    if (!text) return null;
    var d = new Date(String(text).replace(' ', 'T'));
    return isNaN(d.getTime()) ? null : d;
  }

  function pad(n) { return String(n).padStart(2, '0'); }

  function clock(d) { return pad(d.getHours()) + ':' + pad(d.getMinutes()); }

  function shortDate(d) { return pad(d.getDate()) + '.' + pad(d.getMonth() + 1) + '.'; }

  function duration(seconds) {
    if (!isNumber(seconds)) return '—';
    seconds = Math.max(0, Math.round(seconds));
    if (seconds < 60) return seconds + ' s';
    if (seconds < 3600) return Math.round(seconds / 60) + ' min';
    if (seconds < 86400) return (Math.round(seconds / 360) / 10) + ' h';
    return (Math.round(seconds / 8640) / 10) + ' d';
  }

  function bytes(n) {
    if (n < 1024) return n + ' B';
    if (n < 1024 * 1024) return Math.round(n / 1024) + ' kB';
    if (n < 1024 * 1024 * 1024) return (Math.round(n / 1024 / 102.4) / 10) + ' MB';
    return (Math.round(n / 1024 / 1024 / 102.4) / 10) + ' GB';
  }

  function showError(message) {
    errorBox.textContent = message;
    errorBox.hidden = !message;
  }

  /* Seconds since `time` (server clock), advanced by the time since the fetch. */
  function ageSeconds(time, serverTime) {
    var t = parseTime(time), s = parseTime(serverTime);
    if (!t || !s) return null;
    return (s - t) / 1000 + (Date.now() - state.fetchedAt) / 1000;
  }

  // ------------------------------------------------------------------
  // Loading
  // ------------------------------------------------------------------

  function load() {
    if (state.loading) return;
    state.loading = true;
    var url = config.gallery ? config.images : config.api + '?range=' + encodeURIComponent(state.range);
    fetch(url, { headers: { Accept: 'application/json' }, credentials: 'same-origin', cache: 'no-store' })
      .then(function (response) {
        if (response.status === 401) { window.location.href = config.login; return null; }
        return response.json().then(function (body) {
          if (!response.ok) throw new Error(body && body.message ? body.message : 'Request failed (' + response.status + ').');
          return body;
        });
      })
      .then(function (data) {
        if (!data) return;
        state.fetchedAt = Date.now();
        state.lastData = data;
        showError('');
        if (config.gallery) renderGallery(data); else renderDashboard(data);
      })
      .catch(function (err) {
        showError('Could not load the data: ' + err.message + ' Retrying' + (state.auto && config.refresh ? ' automatically.' : ' when you refresh.'));
      })
      .then(function () { state.loading = false; });
  }

  function schedule() {
    if (state.timer) window.clearInterval(state.timer);
    state.timer = null;
    if (state.auto && config.refresh > 0) {
      state.timer = window.setInterval(function () {
        if (!document.hidden) load();
      }, config.refresh * 1000);
    }
    autoButton.setAttribute('aria-pressed', state.auto ? 'true' : 'false');
    autoText.textContent = state.auto ? 'Auto-refresh · ' + duration(config.refresh) : 'Auto-refresh paused';
  }

  function setupControls() {
    if (config.refresh > 0) {
      autoButton.hidden = false;
      autoButton.addEventListener('click', function () {
        state.auto = !state.auto;
        store('auto', String(state.auto));
        schedule();
        if (state.auto) load();
      });
      schedule();
    }
    document.addEventListener('visibilitychange', function () {
      if (!document.hidden && state.auto && config.refresh > 0) load();
    });
    // Keep the "last measurement ... ago" text current between fetches
    window.setInterval(updateLive, 1000);
  }

  function renderRanges(ranges) {
    rangesBox.textContent = '';
    rangesBox.hidden = !ranges.length;
    ranges.forEach(function (key) {
      var button = el('button', null, RANGE_LABELS[key] || key);
      button.type = 'button';
      button.setAttribute('aria-pressed', key === state.range ? 'true' : 'false');
      button.addEventListener('click', function () {
        if (state.range === key) return;
        state.range = key;
        store('range', key);
        renderRanges(ranges);
        load();
      });
      rangesBox.appendChild(button);
    });
  }

  function updateLive() {
    var data = state.lastData;
    if (!data) return;
    var time = config.gallery ? (data.images[0] && data.images[0].time) : data.last_time;
    var label = config.gallery ? 'Last image ' : 'Last measurement ';
    live.hidden = false;
    if (!time) {
      liveDot.className = 'dot none';
      liveText.textContent = data.count ? (data.count + ' measurements, no timestamps') : (config.gallery ? 'No images yet' : 'No measurements yet');
      return;
    }
    var age = ageSeconds(time, data.server_time);
    var expected = isNumber(data.interval) ? data.interval : null;
    var stale = expected ? age > Math.max(expected * 3, 60) : age > 3600;
    liveDot.className = 'dot' + (stale ? ' stale' : '');
    liveText.textContent = label + duration(age) + ' ago';
  }

  // ------------------------------------------------------------------
  // Dashboard
  // ------------------------------------------------------------------

  function status(column) {
    var value = toNumber(column.last);
    var hasMin = isNumber(column.min), hasMax = isNumber(column.max);
    if (column.last === null || column.last === undefined || column.last === '') return { text: 'No reading', tone: 'muted' };
    if (!column.numeric || value === null) return { text: 'Latest', tone: 'muted' };
    if (!hasMin && !hasMax) return { text: 'No limits', tone: 'muted' };
    if (hasMax && value > column.max) return { text: 'Above max', tone: 'bad' };
    if (hasMin && value < column.min) return { text: 'Below min', tone: 'bad' };
    if (hasMin && hasMax) {
      var span = column.max - column.min;
      if (value > column.max - span * 0.1) return { text: 'Near max', tone: 'warn' };
      if (value < column.min + span * 0.1) return { text: 'Near min', tone: 'warn' };
    }
    return { text: 'In range', tone: 'ok' };
  }

  function renderCard(column) {
    var s = status(column);
    var card = el('div', 'card kpi');
    var head = append(el('div', 'kpi-head'), el('span', 'name', column.name), el('span', 'pill ' + (s.tone === 'ok' ? '' : s.tone), s.text));
    var value = el('div', 'value' + (s.tone === 'bad' ? ' bad' : '') + (column.numeric ? '' : ' text'), fmtCol(column.last, column));

    var note;
    var hasBounds = isNumber(column.min) || isNumber(column.max);
    if (column.last === null && column.last_valid !== null) {
      var t = parseTime(column.last_valid_time);
      note = 'Missing in the last measurement · previous ' + fmtCol(column.last_valid, column) + (t ? ' at ' + clock(t) : '');
    } else if (!column.numeric) {
      note = 'Text values';
    } else if (hasBounds) {
      note = 'Limits from configuration.yml';
    } else {
      note = 'No min/max set in configuration.yml';
    }
    append(card, head, value, el('p', 'note', note));

    var number = toNumber(column.last);
    if (isNumber(column.min) && isNumber(column.max) && number !== null && column.max > column.min) {
      var pos = Math.min(100, Math.max(0, (number - column.min) / (column.max - column.min) * 100));
      var marker = el('div', 'marker ' + (s.tone === 'ok' ? '' : s.tone));
      marker.style.left = pos.toFixed(1) + '%';
      append(card, append(el('div', 'range'),
        append(el('div', 'track'), marker),
        append(el('div', 'range-labels'), el('span', null, 'min ' + fmt(column.min)), el('span', null, 'max ' + fmt(column.max)))));
    }
    return card;
  }

  function renderQuality(data) {
    var missing = data.columns.reduce(function (sum, c) { return sum + c.missing; }, 0);
    var outside = data.columns.reduce(function (sum, c) { return sum + c.outside; }, 0);
    var rangeText = data.timestamp ? ' (' + (RANGE_LABELS[data.range] || data.range) + ')' : '';
    var items = [
      ['Measurements' + rangeText, String(data.count)],
      ['Missing values', data.cells ? (Math.round(missing / data.cells * 1000) / 10) + ' %' : '—'],
      ['Outside min/max', String(outside)],
      ['Typical interval', duration(data.interval)]
    ];
    var box = el('section', 'quality');
    box.setAttribute('aria-label', 'Data quality');
    items.forEach(function (item) {
      append(box, append(el('div', 'stat'), el('span', 'stat-label', item[0]), el('span', 'stat-value', item[1])));
    });
    return box;
  }

  function xLabel(x, data) {
    if (!data.timestamp) return '#' + x;
    var d = parseTime(x);
    if (!d) return '';
    return data.range === '1h' || data.range === '24h' ? clock(d) : shortDate(d) + ' ' + clock(d);
  }

  function renderChart(column, data) {
    var values = data.series.values[column.name] || [];
    var present = values.filter(isNumber);
    var card = el('div', 'card chart');
    var outsideText = column.outside ? ' · ' + column.outside + ' outside' : '';
    var bounds = [];
    if (isNumber(column.min)) bounds.push('min ' + fmt(column.min));
    if (isNumber(column.max)) bounds.push('max ' + fmt(column.max));
    append(card, append(el('div', 'chart-head'),
      el('h3', null, column.name),
      el('span', null, (bounds.length ? bounds.join(' · ') : 'no min/max') + outsideText)));

    if (!present.length) {
      append(card, el('p', 'note', 'No numeric values in this range.'));
      return card;
    }

    var dataLo = Math.min.apply(null, present.concat(isNumber(column.min) ? [column.min] : []));
    var dataHi = Math.max.apply(null, present.concat(isNumber(column.max) ? [column.max] : []));
    var padding = (dataHi - dataLo) * 0.08 || Math.max(Math.abs(dataHi) * 0.1, 1);
    // Do not go below zero for values that are never negative (e.g. light)
    var scale = niceScale(dataLo >= 0 ? Math.max(0, dataLo - padding) : dataLo - padding, dataHi + padding);
    var lo = scale.lo, hi = scale.hi;
    var n = values.length;
    var x = function (i) { return n > 1 ? i / (n - 1) * 1000 : 500; };
    var y = function (v) { return (1 - (v - lo) / (hi - lo)) * 300; };

    var d = '', pen = false;
    values.forEach(function (v, i) {
      if (!isNumber(v)) { pen = false; return; }
      d += (pen ? ' L' : ' M') + x(i).toFixed(1) + ' ' + y(v).toFixed(1);
      if (!pen && (i === n - 1 || !isNumber(values[i + 1]))) {
        // A single point between gaps: draw a short tick so it is visible
        d += ' L' + (x(i) + 0.1).toFixed(1) + ' ' + y(v).toFixed(1);
      }
      pen = true;
    });

    var plot = el('div', 'plot');
    var svg = svgEl('svg', { viewBox: '0 0 1000 300', preserveAspectRatio: 'none', role: 'img', 'aria-label': column.name + ' over the selected range' });
    var grid = '';
    for (var g = 0; g <= scale.n; g++) grid += 'M0 ' + (g * 300 / scale.n) + ' L1000 ' + (g * 300 / scale.n) + ' ';
    svg.appendChild(svgEl('path', { d: grid.trim(), fill: 'none', 'stroke-width': '1', 'vector-effect': 'non-scaling-stroke', 'class': 'grid-line' }));
    var boundPath = '';
    if (isNumber(column.max)) boundPath += 'M0 ' + y(column.max).toFixed(1) + ' L1000 ' + y(column.max).toFixed(1) + ' ';
    if (isNumber(column.min)) boundPath += 'M0 ' + y(column.min).toFixed(1) + ' L1000 ' + y(column.min).toFixed(1);
    if (boundPath) svg.appendChild(svgEl('path', { d: boundPath.trim(), fill: 'none', 'stroke-width': '1.5', 'vector-effect': 'non-scaling-stroke', 'class': 'bound-line' }));
    svg.appendChild(svgEl('path', { d: d.trim(), fill: 'none', 'stroke-width': '2', 'stroke-linejoin': 'round', 'stroke-linecap': 'round', 'vector-effect': 'non-scaling-stroke', 'class': 'series' }));
    plot.appendChild(svg);

    [['max', column.max], ['min', column.min]].forEach(function (b) {
      if (!isNumber(b[1])) return;
      var label = el('span', 'bound-label ' + b[0], b[0] + ' ' + fmt(b[1]));
      label.style.top = (y(b[1]) / 3).toFixed(1) + '%';
      plot.appendChild(label);
    });

    values.forEach(function (v, i) {
      if (!isNumber(v)) return;
      var out = (isNumber(column.max) && v > column.max) || (isNumber(column.min) && v < column.min);
      if (!out) return;
      var dot = el('span', 'outlier');
      dot.style.left = (x(i) / 10).toFixed(2) + '%';
      dot.style.top = (y(v) / 3).toFixed(2) + '%';
      dot.title = column.name + ' ' + fmtCol(v, column) + ' · ' + xLabel(data.series.x[i], data);
      plot.appendChild(dot);
    });

    var ticks = el('div', 'ticks');
    for (var t = scale.n; t >= 0; t--) ticks.appendChild(el('span', null, tick(lo + t * scale.step, scale.step)));
    append(card, append(el('div', 'plot-row'), ticks, plot));

    var labels = el('div', 'x-labels');
    var xs = data.series.x;
    [0, 0.25, 0.5, 0.75, 1].forEach(function (f) {
      labels.appendChild(el('span', null, xs.length ? xLabel(xs[Math.round(f * (xs.length - 1))], data) : ''));
    });
    card.appendChild(labels);
    if (data.bucket > 1) card.appendChild(el('p', 'note', 'Averaged over ' + data.bucket + ' measurements per point.'));
    return card;
  }

  function renderTable(data) {
    var byName = {};
    data.columns.forEach(function (c) { byName[c.name] = c; });
    var card = el('section', 'card table-card');
    card.setAttribute('aria-label', 'Latest measurements');
    var note = append(el('span', null, data.table.rows.length + ' of ' + data.count + ' · newest first · '), el('span', 'red', 'red'), document.createTextNode(' = outside min/max'));
    append(card, append(el('div', 'table-head'), el('h2', null, 'Latest measurements'), note));

    var table = el('table');
    var headRow = el('tr');
    data.table.columns.forEach(function (name) {
      var th = el('th', null, name);
      th.scope = 'col';
      headRow.appendChild(th);
    });
    append(table, append(el('thead'), headRow));
    var body = el('tbody');
    data.table.rows.forEach(function (row) {
      var tr = el('tr');
      data.table.columns.forEach(function (name) {
        var v = row[name];
        var td = el('td', null, name === 'timestamp' ? fmt(v) : fmtCol(v, byName[name]));
        if (name === 'timestamp') td.className = 'time';
        else if (v === null || v === undefined || v === '') td.className = 'missing';
        else {
          var c = byName[name], num = toNumber(v);
          if (c && num !== null && ((isNumber(c.max) && num > c.max) || (isNumber(c.min) && num < c.min))) td.className = 'bad';
        }
        tr.appendChild(td);
      });
      body.appendChild(tr);
    });
    table.appendChild(body);
    card.appendChild(append(el('div', 'scroll'), table));
    return card;
  }

  function renderDashboard(data) {
    subtitle.textContent = 'format ' + data.format + ' · ' + data.columns.length + ' columns · timestamp ' + (data.timestamp ? 'on' : 'off');
    data.columns.forEach(function (c) {
      if (!c.numeric) return;
      c.decimals = decimalsOf(data.table.rows.map(function (r) { return r[c.name]; }).concat([c.last, c.last_valid]));
    });
    renderRanges(data.ranges);
    updateLive();

    var fragment = document.createDocumentFragment();
    if (!data.count) {
      var empty = el('p', 'empty');
      append(empty, document.createTextNode(data.range !== 'all' && data.timestamp
        ? 'No measurements in this range. Choose a longer range, or send data to '
        : 'No measurements yet. Send data to '), el('code', null, 'POST /measure'), document.createTextNode('.'));
      fragment.appendChild(empty);
      content.replaceChildren(fragment);
      return;
    }

    var cards = el('section', 'cards');
    cards.setAttribute('aria-label', 'Latest values');
    data.columns.forEach(function (c) { cards.appendChild(renderCard(c)); });
    fragment.appendChild(cards);
    fragment.appendChild(renderQuality(data));

    var numeric = data.columns.filter(function (c) { return c.numeric; });
    if (numeric.length) {
      var charts = el('section', 'charts');
      charts.setAttribute('aria-label', 'Charts');
      numeric.forEach(function (c) { charts.appendChild(renderChart(c, data)); });
      fragment.appendChild(charts);
    }
    fragment.appendChild(renderTable(data));
    content.replaceChildren(fragment);
  }

  // ------------------------------------------------------------------
  // Gallery
  // ------------------------------------------------------------------

  function renderGallery(data) {
    subtitle.textContent = 'format image · ' + data.allowed_extensions.join(', ');

    var fragment = document.createDocumentFragment();
    var interval = null;
    if (data.images.length > 1) {
      var times = data.images.map(function (f) { return parseTime(f.time); }).filter(Boolean);
      var diffs = [];
      for (var i = 1; i < times.length; i++) diffs.push((times[i - 1] - times[i]) / 1000);
      diffs.sort(function (a, b) { return a - b; });
      interval = diffs.length ? diffs[Math.floor(diffs.length / 2)] : null;
    }
    data.interval = interval;
    updateLive();

    var stats = el('section', 'quality');
    stats.setAttribute('aria-label', 'Upload summary');
    [['Images (24 h)', String(data.count_24h)], ['Images in total', String(data.count)],
     ['Typical interval', duration(interval)], ['Storage used', bytes(data.bytes)]].forEach(function (item) {
      append(stats, append(el('div', 'stat'), el('span', 'stat-label', item[0]), el('span', 'stat-value', item[1])));
    });
    fragment.appendChild(stats);

    if (!data.images.length) {
      var empty = el('p', 'empty');
      append(empty, document.createTextNode('No images yet. Upload one to '), el('code', null, 'POST /measure'), document.createTextNode('.'));
      fragment.appendChild(empty);
      content.replaceChildren(fragment);
      return;
    }

    var latest = data.images[0];
    var image = el('img');
    image.src = latest.url;
    image.alt = 'Latest image, ' + latest.name;
    var latestCard = append(el('div', 'card latest-image'), image,
      append(el('div', 'caption'), el('span', 'file', latest.name), el('span', 'meta', latest.time + ' · ' + bytes(latest.size))));
    var info = append(el('div', 'card latest-info'), el('h2', null, 'Latest image'),
      el('p', null, 'Uploaded ' + latest.time + '.'));
    var accepted = el('p');
    append(accepted, document.createTextNode('Accepted types: '), el('code', null, data.allowed_extensions.join(', ')));
    info.appendChild(accepted);
    fragment.appendChild(append(el('section', 'latest'), latestCard, info));

    var rest = data.images.slice(1);
    if (rest.length) {
      var section = el('section', 'section');
      section.setAttribute('aria-label', 'Earlier images');
      append(section, append(el('div', 'section-head'), el('h2', null, 'Earlier images'), el('span', null, rest.length + ' · newest first')));
      var tiles = el('div', 'tiles');
      rest.forEach(function (file) {
        var tile = el('a', 'card tile');
        tile.href = file.url;
        tile.target = '_blank';
        tile.rel = 'noopener';
        var img = el('img');
        img.src = file.url;
        img.alt = file.name;
        img.loading = 'lazy';
        var t = parseTime(file.time);
        append(tile, img, append(el('div', 'tile-meta'),
          el('span', 'file', t ? shortDate(t) + ' ' + clock(t) : file.time), el('span', 'meta', bytes(file.size))));
        tiles.appendChild(tile);
      });
      section.appendChild(tiles);
      fragment.appendChild(section);
    }
    content.replaceChildren(fragment);
  }

  setupControls();
  load();
})();
