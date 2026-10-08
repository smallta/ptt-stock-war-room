let detailDataCache = {};

document.addEventListener("DOMContentLoaded", () => {
    const now = new Date();
    document.getElementById('update-time').innerText = `最後更新時間：${now.toLocaleString()}`;

    // Direct JS data loading (zero-server mode)
    if (window.MARKET_DATA) {
        renderMarketOverview(window.MARKET_DATA);
        renderTimelineChart(window.MARKET_DATA.TimelineSentiment, window.MARKET_DATA.TAIEXIntradayTrend);
    }
    if (window.DETAIL_DATA) {
        detailDataCache = window.DETAIL_DATA;
    }
    if (window.HOT_STOCKS_DATA && window.HOT_STOCKS_DATA.length > 0) {
        renderActionableLeaderboards(window.MARKET_DATA ? window.MARKET_DATA.ActionableLeaderboards : null, window.HOT_STOCKS_DATA);
        renderScoreChart(window.HOT_STOCKS_DATA);
        renderCards(window.HOT_STOCKS_DATA);
        initFilterControls(window.HOT_STOCKS_DATA);
    } else {
        // Fallback for CSV if JS data not present
        Papa.parse("/hot_stocks_sentiment.csv", {
            download: true,
            header: true,
            dynamicTyping: true,
            skipEmptyLines: true,
            complete: function(results) {
                const data = results.data.filter(row => row && row.Stock);
                if(data.length > 0) {
                    renderActionableLeaderboards(window.MARKET_DATA ? window.MARKET_DATA.ActionableLeaderboards : null, data);
                    renderScoreChart(data);
                    renderCards(data);
                    initFilterControls(data);
                } else {
                    document.getElementById('cards-grid').innerHTML = '<p style="color:#94a3b8; text-align:center; padding:30px;">尚未載入資料，請確認爬蟲是否已執行。</p>';
                }
            }
        });
    }

    // Modal Close event
    document.getElementById('modal-close-btn').addEventListener('click', closeModal);
    document.getElementById('comments-modal').addEventListener('click', (e) => {
        if (e.target.id === 'comments-modal') closeModal();
    });
});

function renderMarketOverview(market) {
    if (market.MarketSummary) {
        document.getElementById('market-summary-text').innerText = market.MarketSummary;
    }
    if (market.TotalCommentsParsed !== undefined) {
        document.getElementById('scraped-info-badge').innerText = `📊 本次共即時解析：${market.TotalCommentsParsed.toLocaleString()} 則推文 (搜尋 20 頁)`;
    }
    if (market.PanicIndex !== undefined) {
        const pVal = market.PanicIndex;
        document.getElementById('panic-val').innerText = `${pVal} 分`;
        document.getElementById('panic-fill').style.width = `${pVal}%`;
    }
    if (market.RealInstitutionalStats) {
        const s = market.RealInstitutionalStats;
        const amts = s.Amounts || {};
        const f = amts.Foreign || { buy: '-', sell: '-', net: '-' };
        const t = amts.Trust || { buy: '-', sell: '-', net: '-' };
        const d = amts.Dealer || { buy: '-', sell: '-', net: '-', self_net: '-', hedge_net: '-' };
        const tot = amts.Total || { buy: '-', sell: '-', net: '-' };
        
        document.getElementById('foreign-sentiment').innerText = `${f.net} (買${f.buy}/賣${f.sell})`;
        document.getElementById('trust-sentiment').innerText = `${t.net} (買${t.buy}/賣${t.sell})`;
        
        const dealerEl = document.getElementById('dealer-sentiment');
        if (dealerEl) {
            dealerEl.innerText = `${d.net} (自行${d.self_net}/避險${d.hedge_net})`;
        }
        
        const totEl = document.getElementById('total-inst-sentiment');
        if (totEl) {
            totEl.innerText = `${tot.net} (買${tot.buy}/賣${tot.sell})`;
        }
        
        const fNetStr = s.ForeignTotalNet >= 0 ? `+${s.ForeignTotalNet.toLocaleString()}` : s.ForeignTotalNet.toLocaleString();
        const tNetStr = s.TrustTotalNet >= 0 ? `+${s.TrustTotalNet.toLocaleString()}` : s.TrustTotalNet.toLocaleString();
        const fTop = s.ForeignTopBuy ? s.ForeignTopBuy.map(x => `${x.name}(+${(x.net/1000).toFixed(1)}k張)`).join('、') : '';
        const tTop = s.TrustTopBuy ? s.TrustTopBuy.map(x => `${x.name}(+${(x.net/1000).toFixed(1)}k張)`).join('、') : '';
        
        const descEl = document.getElementById('inst-stats-desc');
        if (descEl) {
            descEl.innerHTML = `🔥 外資大買標的：<b>${fTop}</b> ｜ 投信大買標的：<b>${tTop}</b>`;
        }
    }
    if (market.TAIEXSummary && market.TAIEXSummary.TAIEX !== '-') {
        const t = market.TAIEXSummary;
        const isUp = String(t.Change).startsWith('+');
        const isDown = String(t.Change).startsWith('-');
        const icon = isUp ? '🔴' : (isDown ? '🟢' : '⚪');
        const colorClass = isUp ? 'up' : (isDown ? 'down' : '');
        const badgeEl = document.getElementById('taiex-badge');
        if (badgeEl) {
            badgeEl.className = `taiex-badge ${colorClass}`;
            badgeEl.innerHTML = `📈 今日加權指數：${t.TAIEX} 點 ${icon} ${t.Change} (${t.ChangePercent})`;
        }
    }
    if (market.MarginSummary) {
        const m = market.MarginSummary;
        const mBalEl = document.getElementById('margin-balance');
        const mDiffEl = document.getElementById('margin-diff');
        const mSharesEl = document.getElementById('margin-shares');
        const sSharesEl = document.getElementById('short-shares');
        
        if (mBalEl) mBalEl.innerText = m.MarginBalance || '-';
        if (mDiffEl) {
            mDiffEl.innerText = m.MarginDiff || '-';
            const isUp = String(m.MarginDiff).startsWith('+');
            mDiffEl.style.color = isUp ? '#f87171' : '#4ade80';
        }
        if (mSharesEl) {
            const val = m.MarginSharesDiff || 0;
            mSharesEl.innerText = val > 0 ? `+${val.toLocaleString()}張` : `${val.toLocaleString()}張`;
        }
        if (sSharesEl) {
            const val = m.ShortSharesDiff || 0;
            sSharesEl.innerText = val > 0 ? `+${val.toLocaleString()}張` : `${val.toLocaleString()}張`;
        }
    }
    if (market.AISummary) {
        const aiEl = document.getElementById('ai-summary-content');
        if (aiEl) {
            aiEl.innerText = market.AISummary;
        }
    }
    if (market.ThemeStats && market.ThemeStats.length > 0) {
        const grid = document.getElementById('theme-alerts-grid');
        const section = document.getElementById('theme-alerts-section');
        if (grid && section) {
            section.style.display = 'block';
            grid.innerHTML = '';
            market.ThemeStats.slice(0, 6).forEach(theme => {
                const isUp = String(theme.AvgChange).startsWith('+');
                const isDown = String(theme.AvgChange).startsWith('-');
                const badgeClass = isUp ? 'up' : (isDown ? 'down' : '');
                
                let cardType = 'hot';
                if (theme.Alert && (theme.Alert.includes('齊揚') || theme.Alert.includes('大漲') || theme.Alert.includes('強攻'))) cardType = 'surge';
                else if (theme.Alert && (theme.Alert.includes('重挫') || theme.Alert.includes('跳水'))) cardType = 'drop';
                
                const card = document.createElement('div');
                card.className = `theme-alert-card ${cardType}`;
                card.innerHTML = `
                    <div class="theme-card-top">
                        <span class="theme-title">${theme.Theme}</span>
                        <span class="theme-avg-badge ${badgeClass}">${theme.AvgChange}</span>
                    </div>
                    <div class="theme-tag-badge">${theme.Alert} ｜ 📈上漲 ${theme.UpCount}檔 ｜ 📉下跌 ${theme.DownCount}檔</div>
                    <div class="theme-constituents">
                        <b>焦點成分股：</b>${theme.TopStocks ? theme.TopStocks.join('、') : '-'}
                    </div>
                `;
                grid.appendChild(card);
            });
        }
    }
}

function renderScoreChart(data) {
    const top10 = data.slice(0, 10);
    const labels = top10.map(d => d.Stock);
    const scores = top10.map(d => d.Score);
    
    const ctx = document.getElementById('scoreChart').getContext('2d');
    const gradient = ctx.createLinearGradient(0, 0, 0, 320);
    gradient.addColorStop(0, 'rgba(59, 130, 246, 0.85)');
    gradient.addColorStop(1, 'rgba(139, 92, 246, 0.85)');

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '綜合低估分數',
                data: scores,
                backgroundColor: gradient,
                borderRadius: 6,
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.9)',
                    titleFont: { size: 13, family: 'Inter' },
                    bodyFont: { size: 13, family: 'Inter' }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#94a3b8' }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#f8fafc', font: { weight: 'bold' } }
                }
            }
        }
    });
}

function renderTimelineChart(timelineData, taiexTrendData) {
    if (!timelineData) return;
    
    const labels = Object.keys(timelineData);
    const posData = labels.map(l => timelineData[l].Pos);
    const negData = labels.map(l => timelineData[l].Neg);
    
    const datasets = [
        {
            label: '鄉民看多氣氛 (左軸)',
            data: posData,
            borderColor: '#ef4444',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            fill: true,
            tension: 0.3,
            yAxisID: 'y'
        },
        {
            label: '鄉民看空氣氛 (左軸)',
            data: negData,
            borderColor: '#22c55e',
            backgroundColor: 'rgba(34, 197, 94, 0.1)',
            fill: true,
            tension: 0.3,
            yAxisID: 'y'
        }
    ];

    if (taiexTrendData) {
        const taiexVals = labels.map(l => taiexTrendData[l] || null);
        datasets.push({
            label: '大盤加權指數 (右軸點數)',
            data: taiexVals,
            borderColor: '#f59e0b',
            backgroundColor: 'rgba(245, 158, 11, 0.1)',
            borderDash: [5, 5],
            borderWidth: 2,
            fill: false,
            tension: 0.3,
            yAxisID: 'y1'
        });
    }
    
    const ctx = document.getElementById('timelineChart').getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#f8fafc' } },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.9)'
                }
            },
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    beginAtZero: true,
                    title: { display: true, text: '鄉民情緒 (則)', color: '#94a3b8' },
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#94a3b8' }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: { display: true, text: '大盤指數 (點)', color: '#f59e0b' },
                    grid: { drawOnChartArea: false },
                    ticks: { color: '#f59e0b' }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#f8fafc' }
                }
            }
        }
    });
}

function renderActionableLeaderboards(boards, allStocks) {
    const megaCaps = new Set(["2330", "2317", "2454", "2303", "2603", "2609", "2615", "2382", "3231", "2409", "3481", "0050", "0056", "00878", "00919", "00929", "00940"]);
    const parseNum = (v) => {
        if (v === undefined || v === null || v === '-') return 0;
        const n = Number(String(v).replace(/,/g, '').replace('%', '').replace('+', ''));
        return isNaN(n) ? 0 : n;
    };
    const extractCode = (s) => {
        if (s.Code) return String(s.Code);
        const m = String(s.Stock || '').match(/\((\d{4})\)/);
        return m ? m[1] : '';
    };

    let smartMoney = boards && boards.SmartMoney ? boards.SmartMoney : [];
    let retailTrap = boards && boards.RetailTrap ? boards.RetailTrap : [];
    let darkHorse = boards && boards.DarkHorse ? boards.DarkHorse : [];

    // Fallback computation from allStocks if boards not pre-computed
    if ((!smartMoney.length && !retailTrap.length && !darkHorse.length) && allStocks && allStocks.length) {
        allStocks.forEach(r => {
            const fn = parseNum(r.ForeignNet);
            const tn = parseNum(r.TrustNet);
            const totN = r.TotalNet !== '-' && r.TotalNet !== undefined ? parseNum(r.TotalNet) : (fn + tn);
            const md = parseNum(r.MarginDiff);
            const posR = parseNum(r.BullishRatio);
            const negR = parseNum(r.BearishRatio);
            const chgP = parseNum(r.ChangePercent);
            const code = extractCode(r);

            const item = {
                Stock: r.Stock,
                Price: r.Price,
                ChangePercent: r.ChangePercent,
                TotalNet: totN,
                MarginDiff: md,
                Mentions: r.Mentions,
                Score: r.Score
            };

            if ((totN > 100 || fn > 200 || tn > 50) && (md < 0 || negR >= posR)) {
                const tag = md < -50 ? '資減+法人買' : ((fn > 0 && tn > 0) ? '土洋同買' : '散戶看空+法人買');
                smartMoney.push({ ...item, Tag: tag, _sort: totN - md * 2 });
            }
            if ((totN < -200 || fn < -300) && (md > 50 || posR > negR)) {
                const tag = md > 100 ? '外資倒貨+融資接刀' : '法人大賣+散戶追高';
                retailTrap.push({ ...item, Tag: tag, _sort: md * 2 - totN });
            }
            if (!megaCaps.has(code) && r.Mentions >= 2 && (totN > 0 || chgP > 0)) {
                const tag = totN > 0 ? `聲量 ${r.Mentions} 則 · 法人+${totN.toLocaleString()}張` : `聲量 ${r.Mentions} 則 · 強勢 ${r.ChangePercent}`;
                darkHorse.push({ ...item, Tag: tag, _sort: r.Score + (totN > 200 ? 20 : 0) });
            }
        });
        smartMoney.sort((a, b) => b._sort - a._sort);
        retailTrap.sort((a, b) => b._sort - a._sort);
        darkHorse.sort((a, b) => b._sort - a._sort);
    }

    const renderList = (elId, items, type) => {
        const el = document.getElementById(elId);
        if (!el) return;
        if (!items || items.length === 0) {
            el.innerHTML = '<div class="lb-empty">今日尚無明顯符合此極端背離條件之個股</div>';
            return;
        }
        el.innerHTML = '';
        items.slice(0, 5).forEach((s, idx) => {
            const isUp = String(s.ChangePercent || '').startsWith('+');
            const isDown = String(s.ChangePercent || '').startsWith('-');
            const pClass = isUp ? 'up' : (isDown ? 'down' : '');
            const fmtSigned = (n) => (n > 0 ? `+${Number(n).toLocaleString()}` : Number(n).toLocaleString());

            let metaHtml = '';
            if (type === 'horse') {
                metaHtml = `<span class="lb-chip horse-chip">⚡ ${s.Tag || ''}</span>`;
            } else {
                const totClass = s.TotalNet > 0 ? 'net-buy' : (s.TotalNet < 0 ? 'net-sell' : '');
                const mdClass = s.MarginDiff > 0 ? 'net-buy' : (s.MarginDiff < 0 ? 'net-sell' : '');
                metaHtml = `
                    <span>法人 <b class="inst-chip ${totClass}">${fmtSigned(s.TotalNet)}張</b></span>
                    <span>融資 <b class="inst-chip ${mdClass}">${fmtSigned(s.MarginDiff)}張</b></span>
                    <span class="lb-tag">${s.Tag || ''}</span>
                `;
            }

            const row = document.createElement('div');
            row.className = 'lb-item';
            row.onclick = () => openCommentsModal(s.Stock);
            row.innerHTML = `
                <div class="lb-item-top">
                    <span class="lb-rank">${idx + 1}</span>
                    <span class="lb-stock-name">${s.Stock}</span>
                    <span class="lb-price ${pClass}">$${s.Price} (${s.ChangePercent})</span>
                </div>
                <div class="lb-item-meta">${metaHtml}</div>
            `;
            el.appendChild(row);
        });
    };

    renderList('board-smart-money', smartMoney, 'smart');
    renderList('board-retail-trap', retailTrap, 'trap');
    renderList('board-dark-horse', darkHorse, 'horse');
}

function renderCards(data) {
    const grid = document.getElementById('cards-grid');
    grid.innerHTML = '';

    const countBadge = document.getElementById('filtered-count-badge');
    if (countBadge) {
        countBadge.innerText = `符合條件：${data.length} 檔 (顯示前 ${Math.min(data.length, 48)} 檔)`;
    }

    if (data.length === 0) {
        grid.innerHTML = '<div style="grid-column: 1 / -1; color:#94a3b8; text-align:center; padding:40px; background:rgba(30,41,59,0.45); border-radius:14px; border:1px dashed rgba(255,255,255,0.1);">🔍 在此策略或篩選條件下暫無符合的標的，請點擊上方「🔥 全部熱門標的」或切換其他策略按鈕。</div>';
        return;
    }

    data.slice(0, 48).forEach(stock => {
        let riskHtml = '';
        if (stock.Risk && stock.Risk !== '無') {
            riskHtml = `<div class="risk-badge">⚠️ ${stock.Risk}</div>`;
        }

        let targetHtml = '';
        if (stock.AvgTargetPrice && stock.AvgTargetPrice !== '-') {
            targetHtml = `<div class="target-price-box">🎯 鄉民喊價平均：$${stock.AvgTargetPrice} 元</div>`;
        }

        let eventsHtml = '';
        if (stock.Events) {
            const evs = String(stock.Events).split(',').map(e => e.trim()).filter(Boolean);
            if (evs.length > 0) {
                eventsHtml = `<div class="event-tags-row">${evs.map(e => `<span class="event-tag">📌 ${e}</span>`).join('')}</div>`;
            }
        }

        let keywordsHtml = '';
        if (stock.TopKeywords) {
            const kws = String(stock.TopKeywords).split(',').map(k => k.trim()).filter(Boolean);
            if (kws.length > 0) {
                keywordsHtml = `<div class="keywords-row">${kws.map(k => `<span class="kw-chip">#${k}</span>`).join('')}</div>`;
            }
        }

        let priceChangeHtml = '';
        if (stock.Price && stock.Price !== '-') {
            const chg = String(stock.Change || '0');
            const isUp = chg.startsWith('+');
            const isDown = chg.startsWith('-');
            const colorClass = isUp ? 'up' : (isDown ? 'down' : 'flat');
            const icon = isUp ? '🔴' : (isDown ? '🟢' : '⚪');
            priceChangeHtml = `
                <div class="price-change-box ${colorClass}">
                    <span>收盤價 $${stock.Price}</span>
                    <span>${icon} ${stock.Change} (${stock.ChangePercent})</span>
                </div>
            `;
        }

        let instBuySellHtml = '';
        if (stock.ForeignNet !== undefined && stock.ForeignNet !== '-') {
            const fNet = Number(stock.ForeignNet);
            const tNet = Number(stock.TrustNet);
            const totNet = Number(stock.TotalNet);
            const fClass = fNet > 0 ? 'net-buy' : (fNet < 0 ? 'net-sell' : '');
            const tClass = tNet > 0 ? 'net-buy' : (tNet < 0 ? 'net-sell' : '');
            const totClass = totNet > 0 ? 'net-buy' : (totNet < 0 ? 'net-sell' : '');
            
            const formatStr = (num) => (num > 0 ? `+${num.toLocaleString()}` : num.toLocaleString());
            instBuySellHtml = `
                <div class="inst-buy-sell-box">
                    <span>🏛️ 三大法人買賣張數：</span>
                    <span>外資 <span class="inst-chip ${fClass}">${formatStr(fNet)}</span> | 投信 <span class="inst-chip ${tClass}">${formatStr(tNet)}</span> | 合計 <span class="inst-chip ${totClass}">${formatStr(totNet)}</span></span>
                </div>
            `;
        }

        let chipSignalHtml = '';
        if (stock.ChipSignal) {
            let badgeClass = 'chip-signal-badge';
            if (stock.ChipSignal.includes('🟢') || stock.ChipSignal.includes('💎') || stock.ChipSignal.includes('🔥')) badgeClass += ' bullish';
            else if (stock.ChipSignal.includes('🔴') || stock.ChipSignal.includes('❄️')) badgeClass += ' bearish';
            else if (stock.ChipSignal.includes('⚠️')) badgeClass += ' warning';
            chipSignalHtml = `<div class="${badgeClass}">${stock.ChipSignal}</div>`;
        }

        let marginHtml = '';
        if (stock.MarginDiff !== undefined && stock.MarginDiff !== '-') {
            const md = Number(stock.MarginDiff);
            const sd = Number(stock.ShortDiff);
            const mdClass = md > 0 ? 'net-buy' : (md < 0 ? 'net-sell' : '');
            const sdClass = sd > 0 ? 'net-buy' : (sd < 0 ? 'net-sell' : '');
            const formatStr = (num) => (num > 0 ? `+${num.toLocaleString()}` : num.toLocaleString());
            marginHtml = `
                <div class="inst-buy-sell-box" style="margin-top: 6px;">
                    <span>💳 融資/融券增減：</span>
                    <span>資 <span class="inst-chip ${mdClass}">${formatStr(md)}張</span> | 券 <span class="inst-chip ${sdClass}">${formatStr(sd)}張</span></span>
                </div>
            `;
        }

        let sentBarHtml = '';
        if (stock.BullishRatio && stock.BearishRatio) {
            const pos = parseInt(stock.BullishRatio) || 0;
            const neg = parseInt(stock.BearishRatio) || 0;
            const sarc = parseInt(stock.SarcasmRatio) || 0;
            sentBarHtml = `
                <div style="font-size:0.75rem; color:#94a3b8; display:flex; justify-content:space-between; margin-bottom:4px; margin-top:8px;">
                    <span style="color:#f87171;">多 ${pos}%</span><span style="color:#c4b5fd;">反串 ${sarc}%</span><span style="color:#4ade80;">空 ${neg}%</span>
                </div>
                <div class="sentiment-bar-wrapper">
                    <div class="sent-bar-pos" style="width: ${pos}%;"></div>
                    <div class="sent-bar-sarcasm" style="width: ${sarc}%;"></div>
                    <div class="sent-bar-neg" style="width: ${neg}%;"></div>
                </div>
            `;
        }

        const card = document.createElement('div');
        card.className = 'stock-card';
        card.onclick = () => openCommentsModal(stock.Stock);
        card.innerHTML = `
            <div class="card-header">
                <div class="stock-name">${stock.Stock}</div>
                <div class="score-badge">分數 ${stock.Score}</div>
            </div>
            ${chipSignalHtml}
            ${priceChangeHtml}
            ${instBuySellHtml}
            ${marginHtml}
            ${sentBarHtml}
            ${eventsHtml}
            ${targetHtml}
            ${riskHtml}
            <div class="metrics-grid">
                <div class="metric">
                    <div class="metric-label">提及次數</div>
                    <div class="metric-value">${stock.Mentions}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">發言帳號數</div>
                    <div class="metric-value">${stock.UniqueUsers}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">ID集中度</div>
                    <div class="metric-value">${stock.Concentration}</div>
                </div>
            </div>
            <div class="fundamentals">
                <div class="fun-chip">PE: ${stock.PE}</div>
                <div class="fun-chip">PB: ${stock.PB}</div>
                <div class="fun-chip highlight">殖利率: ${stock.Yield}%</div>
            </div>
            ${keywordsHtml}
            <div class="view-comments-btn">💬 點擊查看鄉民推文摘錄 (${stock.Mentions} 則)</div>
        `;
        grid.appendChild(card);
    });
}

let stockHistoryChartInstance = null;

function initFilterControls(allData) {
    const searchInput = document.getElementById('stock-search-input');
    const sectorSelect = document.getElementById('sector-filter-select');
    const sortSelect = document.getElementById('sort-by-select');
    const tabBtns = document.querySelectorAll('.signal-tab-btn');
    if (!searchInput || !sectorSelect) return;

    const megaCaps = new Set(["2330", "2317", "2454", "2303", "2603", "2609", "2615", "2382", "3231", "2409", "3481", "0050", "0056", "00878", "00919", "00929", "00940"]);
    let currentSignal = 'ALL';

    const parseNum = (v, fallback = 0) => {
        if (v === undefined || v === null || v === '-') return fallback;
        const n = Number(String(v).replace(/,/g, '').replace('%', '').replace('+', ''));
        return isNaN(n) ? fallback : n;
    };
    const extractCode = (s) => {
        if (s.Code) return String(s.Code);
        const m = String(s.Stock || '').match(/\((\d{4})\)/);
        return m ? m[1] : '';
    };

    // Populate sector dropdown
    const sectors = Array.from(new Set(allData.map(d => d.Sector).filter(Boolean)));
    sectorSelect.innerHTML = '<option value="ALL">🌐 全部產業類別</option>';
    sectors.forEach(s => {
        const opt = document.createElement('option');
        opt.value = s;
        opt.innerText = s;
        sectorSelect.appendChild(opt);
    });

    const applyFilter = () => {
        const query = searchInput.value.trim().toLowerCase();
        const selectedSector = sectorSelect.value;
        const sortBy = sortSelect ? sortSelect.value : 'score_desc';

        let filtered = allData.filter(d => {
            const matchesQuery = !query || d.Stock.toLowerCase().includes(query) || (d.Code && String(d.Code).includes(query));
            const matchesSector = (selectedSector === 'ALL') || (d.Sector === selectedSector);
            if (!matchesQuery || !matchesSector) return false;

            if (currentSignal === 'ALL') return true;

            const fn = parseNum(d.ForeignNet);
            const tn = parseNum(d.TrustNet);
            const totN = d.TotalNet !== '-' && d.TotalNet !== undefined ? parseNum(d.TotalNet) : (fn + tn);
            const md = parseNum(d.MarginDiff);
            const posR = parseNum(d.BullishRatio);
            const negR = parseNum(d.BearishRatio);
            const chgP = parseNum(d.ChangePercent);
            const code = extractCode(d);
            const sig = String(d.ChipSignal || '');

            if (currentSignal === 'SMART_MONEY') {
                return ((totN > 50 || fn > 100 || tn > 30) && (md <= 0 || negR >= posR)) || sig.includes('💎') || sig.includes('🔥');
            }
            if (currentSignal === 'CONTRARIAN') {
                return (negR >= posR && (totN > 0 || chgP > 0)) || sig.includes('🟢');
            }
            if (currentSignal === 'RETAIL_TRAP') {
                return ((totN < -100 || fn < -200) && (md > 30 || posR > negR)) || sig.includes('💣') || sig.includes('🔴') || sig.includes('⚠️');
            }
            if (currentSignal === 'DARK_HORSE') {
                return !megaCaps.has(code) && d.Mentions >= 2 && (totN > 0 || chgP > 0);
            }
            return true;
        });

        // Apply multi-dimension sorting
        filtered.sort((a, b) => {
            if (sortBy === 'total_inst_desc') return parseNum(b.TotalNet, -999999) - parseNum(a.TotalNet, -999999);
            if (sortBy === 'foreign_desc') return parseNum(b.ForeignNet, -999999) - parseNum(a.ForeignNet, -999999);
            if (sortBy === 'trust_desc') return parseNum(b.TrustNet, -999999) - parseNum(a.TrustNet, -999999);
            if (sortBy === 'margin_asc') return parseNum(a.MarginDiff, 999999) - parseNum(b.MarginDiff, 999999);
            if (sortBy === 'margin_desc') return parseNum(b.MarginDiff, -999999) - parseNum(a.MarginDiff, -999999);
            if (sortBy === 'chg_desc') return parseNum(b.ChangePercent, -999) - parseNum(a.ChangePercent, -999);
            if (sortBy === 'chg_asc') return parseNum(a.ChangePercent, 999) - parseNum(b.ChangePercent, 999);
            return (b.Score || 0) - (a.Score || 0);
        });

        renderCards(filtered);
    };

    searchInput.addEventListener('input', applyFilter);
    sectorSelect.addEventListener('change', applyFilter);
    if (sortSelect) sortSelect.addEventListener('change', applyFilter);

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentSignal = btn.getAttribute('data-signal') || 'ALL';
            applyFilter();
        });
    });
}

function openCommentsModal(stockName) {
    const modal = document.getElementById('comments-modal');
    document.getElementById('modal-stock-name').innerText = `💬 ${stockName} - 鄉民討論摘錄與趨勢`;
    
    // Render 7-day History Chart if HISTORY_DATA exists
    const historyBox = document.getElementById('stock-history-box');
    if (window.HISTORY_DATA && historyBox) {
        const historyObj = window.HISTORY_DATA;
        const dates = Object.keys(historyObj).sort();
        if (dates.length > 0) {
            const scores = dates.map(d => (historyObj[d][stockName] ? historyObj[d][stockName].Score : null));
            const mentions = dates.map(d => (historyObj[d][stockName] ? historyObj[d][stockName].Mentions : 0));
            
            historyBox.style.display = 'block';
            const ctx = document.getElementById('stockHistoryChart').getContext('2d');
            if (stockHistoryChartInstance) {
                stockHistoryChartInstance.destroy();
            }
            stockHistoryChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: dates,
                    datasets: [
                        {
                            label: '綜合熱度分數',
                            data: scores,
                            borderColor: '#8b5cf6',
                            backgroundColor: 'rgba(139, 92, 246, 0.1)',
                            fill: true,
                            tension: 0.3
                        },
                        {
                            label: '討論聲量(則)',
                            data: mentions,
                            borderColor: '#3b82f6',
                            borderDash: [4, 4],
                            fill: false,
                            tension: 0.3
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { labels: { color: '#cbd5e1' } } },
                    scales: {
                        y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                        x: { ticks: { color: '#cbd5e1' }, grid: { display: false } }
                    }
                }
            });
        } else {
            historyBox.style.display = 'none';
        }
    }

    const listContainer = document.getElementById('modal-comments-list');
    listContainer.innerHTML = '';

    const detail = detailDataCache[stockName];
    if (detail && detail.Comments && detail.Comments.length > 0) {
        detail.Comments.forEach(c => {
            const item = document.createElement('div');
            item.className = 'comment-item';
            item.innerHTML = `
                <div class="comment-user">👤 ${c.user} <span style="font-size:0.75rem; color:#64748b; font-weight:normal;">(${c.time || '即時'})</span></div>
                <div class="comment-text">${c.text}</div>
            `;
            listContainer.appendChild(item);
        });
    } else {
        listContainer.innerHTML = '<p style="color:#94a3b8; text-align:center; padding:20px;">尚無具體文字摘錄。</p>';
    }

    modal.classList.add('active');
}

function closeModal() {
    document.getElementById('comments-modal').classList.remove('active');
}
