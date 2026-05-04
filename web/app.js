// Claude Dashboard — Dark Arcade renderer

const C = {
  blue:   '#6FA2D0',
  green:  '#7DC38D',
  orange: '#F55636',
  amber:  '#fbbf24',
  text:   '#e2e8f0',
  text2:  '#94a3b8',
  text3:  '#64748b',
  grid:   'rgba(255,255,255,0.06)',
  bg2:    '#232a3d',
};

Chart.defaults.color = C.text2;
Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "SF Pro Display", "Inter", sans-serif';
Chart.defaults.borderColor = C.grid;

const fmtUsd = (n) => '$' + (n || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
const fmtNum = (n) => (n || 0).toLocaleString();
const fmtAbbrev = (n) => {
  n = +n || 0;
  if (n >= 1e9) return (n / 1e9).toFixed(2) + 'B';
  if (n >= 1e6) return (n / 1e6).toFixed(2) + 'M';
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K';
  return Math.round(n).toString();
};
const fmtDur = (sec) => {
  sec = +sec || 0;
  if (sec < 60) return sec + 's';
  const m = Math.floor(sec / 60);
  if (m < 60) return m + 'm';
  const h = Math.floor(m / 60);
  const rm = m % 60;
  if (h < 24) return `${h}h ${rm}m`;
  const d = Math.floor(h / 24);
  return `${d}d ${h % 24}h`;
};
const shortProj = (p) => {
  if (!p) return '—';
  const last = p.split('/').filter(Boolean).slice(-2).join('/');
  return last || p;
};
const shortModel = (m) => {
  if (!m) return '—';
  return m.replace(/^claude-/, '').replace(/-\d{8}$/, '');
};
const fmtDateAgo = (iso) => {
  if (!iso) return '—';
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60)    return 'just now';
  if (diff < 3600)  return Math.floor(diff/60) + 'm ago';
  if (diff < 86400) return Math.floor(diff/3600) + 'h ago';
  if (diff < 86400 * 14) return Math.floor(diff/86400) + 'd ago';
  return d.toLocaleDateString();
};

const set = (selector, text) => {
  document.querySelectorAll(`[data-bind="${selector}"]`).forEach(el => { el.textContent = text; });
};

function gradient(ctx, area, from, to) {
  if (!area) return from;
  const g = ctx.createLinearGradient(0, area.top, 0, area.bottom);
  g.addColorStop(0, from);
  g.addColorStop(1, to);
  return g;
}

async function load() {
  let data;
  try {
    const r = await fetch('data.json?ts=' + Date.now());
    if (!r.ok) throw new Error('http ' + r.status);
    data = await r.json();
  } catch (e) {
    document.getElementById('meta').textContent = 'data.json missing — run python dashboard.py';
    return;
  }
  render(data);
}

function render(d) {
  const gen = new Date(d.generated_at);
  document.getElementById('meta').textContent =
    `${d.totals.event_count.toLocaleString()} events · ${d.totals.session_count} sessions · refreshed ${fmtDateAgo(d.generated_at)}`;

  // --- Hero tiles (mode-aware) ---
  const sp = d.spend_tiles;
  const billing = d.billing || { mode: 'api', subscription_usd_per_month: 0 };
  const isSub = billing.mode === 'subscription';
  const subFee = +billing.subscription_usd_per_month || 0;
  const daily = d.daily || [];
  const todayRow = daily[daily.length - 1];
  const yest = daily[daily.length - 2];

  if (isSub) {
    // Subscription mode: hero shows what the plan saves vs API rates
    const valueToday  = sp.today;
    const valueWeek   = sp.week;
    const valueMonth  = sp.month;
    const ratio       = subFee > 0 ? (valueMonth / (subFee * (new Date().getDate() / 30))) : 0;
    // simpler ROI: value-this-month divided by what fraction of monthly fee is "earned" so far
    const elapsedFrac = Math.max(new Date().getDate() / 30, 0.05);
    const feeBurned   = subFee * elapsedFrac;
    const roi         = feeBurned > 0 ? (valueMonth / feeBurned) : 0;

    set('hero.title', 'API-equivalent value (subscription mode)');
    set('hero.hint',  `your plan: ${fmtUsd(subFee)}/mo flat — these tiles show what the same usage would have cost on pay-as-you-go API`);

    set('tile.today.label', '💎 API value today');
    set('spend.today.usd',  fmtUsd(valueToday));
    if (todayRow && yest && yest.cost > 0) {
      const pct = (todayRow.cost - yest.cost) / yest.cost * 100;
      const arrow = pct >= 0 ? '↑' : '↓';
      document.querySelectorAll('[data-bind="spend.today.delta"]').forEach(el => {
        el.textContent = `${arrow} ${Math.abs(pct).toFixed(0)}% vs yesterday`;
      });
    } else {
      set('spend.today.delta', '—');
    }

    set('tile.week.label', '📅 API value · last 7d');
    set('spend.week.usd',  fmtUsd(valueWeek));
    set('spend.week.sub',  `avg ${fmtUsd(valueWeek / 7)}/day`);

    set('tile.month.label', '🗓 API value · this month');
    set('spend.month.usd',  fmtUsd(valueMonth));
    set('spend.month.sub',  `you actually pay ${fmtUsd(subFee)}/mo flat`);

    set('tile.fourth.label', '🏆 ROI vs subscription');
    set('spend.projected.usd', `${roi.toFixed(0)}×`);
    set('spend.projected.sub', `${fmtUsd(valueMonth)} of value for ${fmtUsd(feeBurned)} of plan fee elapsed`);

    document.getElementById('billing-banner').innerHTML = `
      <div class="banner info" style="margin-top:12px">
        Subscription mode is on. You're on the <strong>${fmtUsd(subFee)}/month</strong> plan,
        so your real spend is flat. The "API value" tiles show what the same token volume would cost
        a pay-as-you-go user — fun, not real spend. Toggle in <code>config.json</code>.
      </div>`;

    // Relabel sections that still say "Cost" / "Most expensive" — they're all API-equivalent in sub mode
    setTimeout(() => {
      const swaps = [
        [/Daily spend/i,         'Daily API value'],
        [/Cost by model family/i,'API value by model family'],
        [/Cost by model \(full\)/i,'API value by model (full)'],
        [/Cost by project/i,     'API value by project'],
        [/Most expensive sessions/i, 'Highest API-value sessions'],
        [/Most expensive day/i,  'Highest API-value day'],
      ];
      // Walk only text nodes so we don't clobber nested .emoji spans
      const swapTextNodes = (root) => {
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
        let n; while ((n = walker.nextNode())) {
          for (const [re, to] of swaps) if (re.test(n.nodeValue)) {
            n.nodeValue = n.nodeValue.replace(re, to);
          }
        }
      };
      document.querySelectorAll('h3, .label, th').forEach(swapTextNodes);
    }, 0);
  } else {
    set('hero.title', 'Spend');
    set('hero.hint', '');
    set('tile.today.label', '💰 Spend today');
    set('tile.week.label',  '📅 Last 7 days');
    set('tile.month.label', '🗓 This month');
    set('tile.fourth.label','🔥 Projected month');
    set('spend.today.usd',     fmtUsd(sp.today));
    set('spend.week.usd',      fmtUsd(sp.week));
    set('spend.month.usd',     fmtUsd(sp.month));
    set('spend.projected.usd', fmtUsd(sp.projected_month));
    if (todayRow && yest && yest.cost > 0) {
      const pct = (todayRow.cost - yest.cost) / yest.cost * 100;
      const arrow = pct >= 0 ? '↑' : '↓';
      const cls = pct >= 0 ? 'up' : 'down';
      document.querySelectorAll('[data-bind="spend.today.delta"]').forEach(el => {
        el.textContent = `${arrow} ${Math.abs(pct).toFixed(0)}% vs yesterday`;
        el.classList.add(cls);
      });
    } else {
      set('spend.today.delta', '—');
    }
    set('spend.week.sub',  `avg ${fmtUsd(sp.week / 7)}/day`);
    set('spend.month.sub', `${fmtNum(sp.tokens_today_in + sp.tokens_today_out + sp.cache_read_today)} tokens today`);
    set('spend.projected.sub', "at today's burn rate");
    document.getElementById('billing-banner').innerHTML = '';
  }

  // --- Daily spend chart ---
  {
    const ctx = document.getElementById('chart-daily').getContext('2d');
    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: daily.map(x => x.date.slice(5)),
        datasets: [{
          label: 'USD',
          data: daily.map(x => x.cost),
          backgroundColor: (c) => gradient(c.chart.ctx, c.chart.chartArea, C.blue, C.green),
          borderRadius: 3,
          maxBarThickness: 10,
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: {
          callbacks: { label: (c) => fmtUsd(c.parsed.y) },
        }},
        scales: {
          x: { grid: { color: C.grid }, ticks: { autoSkip: true, maxTicksLimit: 10, color: C.text3 } },
          y: { grid: { color: C.grid }, ticks: { color: C.text3, callback: v => '$' + v } },
        },
      },
    });
  }

  // --- Cost by family donut ---
  {
    const fam = d.cost_by_family || {};
    const labels = ['opus', 'sonnet', 'haiku', 'other'].filter(k => fam[k]);
    const colors = { opus: C.green, sonnet: C.blue, haiku: C.orange, other: '#888' };
    const ctx = document.getElementById('chart-family').getContext('2d');
    new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels,
        datasets: [{
          data: labels.map(k => fam[k]),
          backgroundColor: labels.map(k => colors[k]),
          borderColor: '#1a1f2e',
          borderWidth: 2,
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false, cutout: '64%',
        plugins: {
          legend: { position: 'bottom', labels: { color: C.text2, padding: 14, boxWidth: 10 } },
          tooltip: { callbacks: { label: (c) => `${c.label}: ${fmtUsd(c.parsed)}` }},
        },
      },
    });
    const kv = document.getElementById('family-kv');
    const total = Object.values(fam).reduce((a, b) => a + b, 0) || 1;
    kv.innerHTML = labels.map(k =>
      `<div class="k">${k}</div><div class="v">${fmtUsd(fam[k])} · ${(fam[k]/total*100).toFixed(0)}%</div>`
    ).join('');
  }

  // --- Token breakdown today ---
  {
    const ctx = document.getElementById('chart-tokens-today').getContext('2d');
    const labels = ['Input', 'Output', 'Cache read', 'Cache write'];
    const values = [sp.tokens_today_in, sp.tokens_today_out, sp.cache_read_today, sp.cache_create_today];
    const colors = [C.blue, C.green, '#a78bfa', C.orange];
    new Chart(ctx, {
      type: 'bar',
      data: { labels, datasets: [{ data: values, backgroundColor: colors, borderRadius: 4 }] },
      options: {
        indexAxis: 'y', responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => fmtNum(c.parsed.x) }}},
        scales: {
          x: { grid: { color: C.grid }, ticks: { color: C.text3, callback: v => fmtAbbrev(v) } },
          y: { grid: { display: false }, ticks: { color: C.text } },
        },
      },
    });
    const t = d.totals;
    document.getElementById('tokens-kv').innerHTML = `
      <div class="k">Lifetime input</div><div class="v">${fmtAbbrev(t.input_tokens)}</div>
      <div class="k">Lifetime output</div><div class="v">${fmtAbbrev(t.output_tokens)}</div>
      <div class="k">Lifetime cache read</div><div class="v">${fmtAbbrev(t.cache_read_tokens)}</div>
      <div class="k">Lifetime cache write</div><div class="v">${fmtAbbrev(t.cache_create_tokens)}</div>
    `;
  }

  // --- Cost by full model name ---
  {
    const ul = document.getElementById('cost-by-model');
    const entries = Object.entries(d.cost_by_model || {}).sort((a,b) => b[1] - a[1]);
    const max = entries.length ? entries[0][1] : 1;
    ul.innerHTML = entries.map(([m, v]) => {
      const w = Math.max(2, Math.round(v / max * 100));
      return `<li><span class="name">${shortModel(m)}<span class="bar" style="width:${w}%"></span></span><span class="v">${fmtUsd(v)}</span></li>`;
    }).join('') || '<li><span class="name">no data</span></li>';
  }

  // --- Records strip ---
  const rec = d.records || {};
  if (rec.most_expensive_day) {
    set('rec.exp_day.cost', fmtUsd(rec.most_expensive_day.cost));
    set('rec.exp_day.date', rec.most_expensive_day.date);
  }
  if (rec.most_active_day) {
    set('rec.act_day.msgs', fmtNum(rec.most_active_day.messages) + ' msgs');
    set('rec.act_day.date', rec.most_active_day.date);
  }
  if (rec.longest_session) {
    set('rec.long_sess.dur',  fmtDur(rec.longest_session.duration_seconds));
    set('rec.long_sess.proj', shortProj(rec.longest_session.project));
  }

  // --- Heatmap ---
  {
    const grid = d.activity_heatmap || [];
    const max = Math.max(1, ...grid.flat());
    const days = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
    const host = document.getElementById('heatmap');
    let html = '<div class="h-label"></div>';
    for (let h = 0; h < 24; h++) html += `<div class="h-label" style="text-align:center">${h % 6 === 0 ? h : ''}</div>`;
    grid.forEach((row, i) => {
      html += `<div class="h-label">${days[i]}</div>`;
      row.forEach(v => {
        const pct = v / max;
        let bg = '#1a1f2e';
        if (pct > 0)    bg = `rgba(111,162,208,${0.18 + pct*0.25})`;
        if (pct > 0.35) bg = `rgba(125,195,141,${0.4 + pct*0.4})`;
        if (pct > 0.75) bg = '#F55636';
        html += `<div class="cell" style="background:${bg}" title="${days[i]} ${'00'+0}: ${v}"></div>`;
      });
    });
    host.innerHTML = html;
  }

  // --- Cost by project ---
  {
    const ul = document.getElementById('cost-by-project');
    const arr = (d.cost_by_project || []).slice(0, 12);
    const max = arr.length ? arr[0].cost : 1;
    ul.innerHTML = arr.map(p => {
      const w = Math.max(2, Math.round(p.cost / max * 100));
      return `<li><span class="name">${shortProj(p.project)}<span class="bar" style="width:${w}%"></span></span><span class="v">${fmtUsd(p.cost)}</span></li>`;
    }).join('') || '<li><span class="name">no data</span></li>';
  }

  // --- Tool usage chart ---
  {
    const tools = Object.entries(d.tool_counts || {}).slice(0, 12);
    const ctx = document.getElementById('chart-tools').getContext('2d');
    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: tools.map(t => t[0]),
        datasets: [{
          data: tools.map(t => t[1]),
          backgroundColor: (c) => gradient(c.chart.ctx, c.chart.chartArea, C.blue, C.green),
          borderRadius: 3,
          maxBarThickness: 14,
        }],
      },
      options: {
        indexAxis: 'y', responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => fmtNum(c.parsed.x) }}},
        scales: {
          x: { grid: { color: C.grid }, ticks: { color: C.text3, callback: v => fmtAbbrev(v) } },
          y: { grid: { display: false }, ticks: { color: C.text } },
        },
      },
    });
  }

  // --- Sub-agents ---
  {
    const ul = document.getElementById('subagents');
    const entries = Object.entries(d.subagent_counts || {}).sort((a,b) => b[1] - a[1]);
    const max = entries.length ? entries[0][1] : 1;
    ul.innerHTML = entries.map(([k, v]) => {
      const w = Math.max(2, Math.round(v / max * 100));
      return `<li><span class="name">${k}<span class="bar" style="width:${w}%;background:linear-gradient(90deg,${C.green},${C.orange})"></span></span><span class="v">${fmtNum(v)}</span></li>`;
    }).join('') || '<li><span class="name">no sub-agents seen</span></li>';
  }

  // --- Skills ---
  {
    const ul = document.getElementById('skills');
    const entries = Object.entries(d.skill_counts || {}).sort((a,b) => b[1] - a[1]);
    if (!entries.length) {
      ul.innerHTML = '<li><span class="name" style="color:var(--text-3)">No Skill-tool invocations recorded yet.</span></li>';
    } else {
      const max = entries[0][1];
      ul.innerHTML = entries.map(([k, v]) => {
        const w = Math.max(2, Math.round(v / max * 100));
        return `<li><span class="name">${k}<span class="bar" style="width:${w}%"></span></span><span class="v">${fmtNum(v)}</span></li>`;
      }).join('');
    }
  }

  // --- Recent sessions ---
  {
    const tb = document.querySelector('#recent-sessions tbody');
    tb.innerHTML = (d.recent_sessions || []).map(s => `
      <tr>
        <td class="dim">${fmtDateAgo(s.last_ts)}</td>
        <td class="proj" title="${s.project}">${shortProj(s.project)}</td>
        <td>${shortModel(s.model_top)}</td>
        <td>${fmtNum(s.messages)}</td>
        <td>${fmtNum(s.tools)}</td>
        <td>${fmtAbbrev((s.tokens_in||0) + (s.tokens_out||0))}</td>
        <td class="cost">${fmtUsd(s.cost)}</td>
        <td class="dim">${fmtDur(s.duration_seconds)}</td>
      </tr>`).join('');
  }

  // --- Leaderboards ---
  {
    const tb1 = document.querySelector('#board-expensive tbody');
    tb1.innerHTML = (d.most_expensive_sessions || []).map(s => `
      <tr>
        <td class="proj" title="${s.project}">${shortProj(s.project)}</td>
        <td>${shortModel(s.model_top)}</td>
        <td>${fmtNum(s.messages)}</td>
        <td class="cost">${fmtUsd(s.cost)}</td>
      </tr>`).join('');

    const tb2 = document.querySelector('#board-longest tbody');
    tb2.innerHTML = (d.longest_sessions || []).map(s => `
      <tr>
        <td class="proj" title="${s.project}">${shortProj(s.project)}</td>
        <td>${shortModel(s.model_top)}</td>
        <td>${fmtNum(s.messages)}</td>
        <td class="dim">${fmtDur(s.duration_seconds)}</td>
      </tr>`).join('');
  }

  // --- Errors ---
  {
    set('errors.count', fmtNum((d.errors || {}).count || 0));
    const ul = document.getElementById('errors-by-tool');
    const entries = Object.entries((d.errors || {}).by_tool || {});
    if (!entries.length) {
      ul.innerHTML = '<li><span class="name" style="color:var(--text-3)">no per-tool error data</span></li>';
    } else {
      const max = entries[0][1];
      ul.innerHTML = entries.map(([k, v]) => {
        const w = Math.max(2, Math.round(v / max * 100));
        return `<li><span class="name">${k}<span class="bar" style="width:${w}%;background:linear-gradient(90deg,${C.orange},${C.amber})"></span></span><span class="v">${fmtNum(v)}</span></li>`;
      }).join('');
    }
  }

  // --- Prompt stats ---
  {
    const p = d.prompt_stats || {};
    document.getElementById('prompt-kv').innerHTML = `
      <div class="k">Prompts sent</div><div class="v">${fmtNum(p.count)}</div>
      <div class="k">Avg length</div><div class="v">${fmtNum(Math.round(p.avg_chars || 0))} chars</div>
      <div class="k">Longest</div><div class="v">${fmtNum(p.longest_chars || 0)} chars</div>
    `;
  }

  // --- Context distribution ---
  {
    const c = d.context_distribution || {};
    document.getElementById('context-kv').innerHTML = `
      <div class="k">Median session input</div><div class="v">${fmtAbbrev(c.p50)}</div>
      <div class="k">90th percentile</div><div class="v">${fmtAbbrev(c.p90)}</div>
      <div class="k">Largest single session</div><div class="v">${fmtAbbrev(c.max)}</div>
    `;
  }

  // --- Admin API panel ---
  {
    const host = document.getElementById('admin-content');
    if (d.admin_error) {
      host.innerHTML = `<div class="banner">Admin API error: ${d.admin_error}</div>`;
    } else if (!d.admin) {
      host.innerHTML = `<div class="banner info">
        Add an Anthropic Admin API key to <code>config.json</code> to see org-wide spend and a "Claude Code vs direct API" split.
        Get one at <a href="https://console.anthropic.com/settings/admin-keys" target="_blank">console.anthropic.com → Settings → Admin Keys</a>.
      </div>`;
    } else {
      const a = d.admin;
      const apiTotal = a.total_cost || 0;
      const codeTotal = (d.totals || {}).cost || 0;
      const directApi = Math.max(apiTotal - codeTotal, 0);
      host.innerHTML = `
        <div class="grid two">
          <div class="card">
            <h3>📊 Admin API daily cost (${a.window_days}d)</h3>
            <div class="chart-host h-md"><canvas id="chart-admin-daily"></canvas></div>
          </div>
          <div class="card">
            <h3>⚖️ Claude Code vs direct API</h3>
            <div class="chart-host h-md"><canvas id="chart-codevsapi"></canvas></div>
            <div class="kv">
              <div class="k">Org total (admin)</div><div class="v">${fmtUsd(apiTotal)}</div>
              <div class="k">Local Claude Code</div><div class="v">${fmtUsd(codeTotal)}</div>
              <div class="k">Direct API (delta)</div><div class="v">${fmtUsd(directApi)}</div>
            </div>
          </div>
        </div>
        <div class="grid two" style="margin-top:16px">
          <div class="card"><h3>🔑 Top API keys (tokens)</h3><ul class="bar-list" id="admin-keys"></ul></div>
          <div class="card"><h3>🏢 By workspace</h3><ul class="bar-list" id="admin-workspaces"></ul></div>
        </div>
      `;

      const dctx = document.getElementById('chart-admin-daily').getContext('2d');
      new Chart(dctx, {
        type: 'line',
        data: {
          labels: a.daily_cost.map(r => r.date.slice(5)),
          datasets: [{
            data: a.daily_cost.map(r => r.cost),
            borderColor: C.blue, backgroundColor: 'rgba(111,162,208,0.15)', fill: true, tension: 0.3,
            pointRadius: 0,
          }],
        },
        options: { responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => fmtUsd(c.parsed.y) }}},
          scales: { x: { grid: { color: C.grid }, ticks: { color: C.text3, maxTicksLimit: 8 } },
                    y: { grid: { color: C.grid }, ticks: { color: C.text3, callback: v => '$' + v }}},
        },
      });

      const cctx = document.getElementById('chart-codevsapi').getContext('2d');
      new Chart(cctx, {
        type: 'doughnut',
        data: { labels: ['Claude Code', 'Direct API'],
                datasets: [{ data: [codeTotal, directApi], backgroundColor: [C.green, C.orange], borderColor: '#1a1f2e', borderWidth: 2 }] },
        options: { responsive: true, maintainAspectRatio: false, cutout: '64%',
                   plugins: { legend: { position: 'bottom', labels: { color: C.text2, padding: 14, boxWidth: 10 } },
                              tooltip: { callbacks: { label: c => `${c.label}: ${fmtUsd(c.parsed)}` }}}},
      });

      const fillBar = (id, obj, fmt) => {
        const ul = document.getElementById(id);
        const entries = Object.entries(obj || {}).sort((a,b) => b[1] - a[1]).slice(0, 10);
        if (!entries.length) { ul.innerHTML = '<li><span class="name" style="color:var(--text-3)">no data</span></li>'; return; }
        const max = entries[0][1];
        ul.innerHTML = entries.map(([k, v]) => {
          const w = Math.max(2, Math.round(v / max * 100));
          return `<li><span class="name">${k}<span class="bar" style="width:${w}%"></span></span><span class="v">${fmt(v)}</span></li>`;
        }).join('');
      };
      fillBar('admin-keys', a.by_api_key, fmtAbbrev);
      fillBar('admin-workspaces', a.by_workspace, fmtUsd);
    }
  }
}

load();
