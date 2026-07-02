document.addEventListener("DOMContentLoaded", () => {
    const now = new Date();
    document.getElementById('update-time').innerText = `最後更新時間：${now.toLocaleString()}`;

    Papa.parse("../hot_stocks_sentiment.csv", {
        download: true,
        header: true,
        dynamicTyping: true,
        complete: function(results) {
            const data = results.data.filter(row => row.Stock);
            if(data.length > 0) {
                renderChart(data);
                renderCards(data);
            } else {
                document.getElementById('cards-grid').innerHTML = '<p>尚未載入資料，請先執行爬蟲程式。</p>';
            }
        }
    });
});

function renderChart(data) {
    const top10 = data.slice(0, 10);
    const labels = top10.map(d => d.Stock);
    const scores = top10.map(d => d.Score);
    
    const ctx = document.getElementById('scoreChart').getContext('2d');
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, 'rgba(59, 130, 246, 0.8)');
    gradient.addColorStop(1, 'rgba(139, 92, 246, 0.8)');

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '綜合低估分數',
                data: scores,
                backgroundColor: gradient,
                borderRadius: 8,
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
                    titleFont: { size: 14, family: 'Inter' },
                    bodyFont: { size: 14, family: 'Inter' },
                    padding: 12,
                    cornerRadius: 8
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255, 255, 255, 0.05)', drawBorder: false },
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

function renderCards(data) {
    const grid = document.getElementById('cards-grid');
    grid.innerHTML = '';

    data.slice(0, 20).forEach(stock => {
        let riskHtml = '';
        if (stock.Risk && stock.Risk !== '無') {
            riskHtml = `<div class="risk-badge">⚠️ ${stock.Risk}</div>`;
        }

        const card = document.createElement('div');
        card.className = 'stock-card';
        card.innerHTML = `
            <div class="card-header">
                <div class="stock-name">${stock.Stock}</div>
                <div class="score-badge">分數 ${stock.Score}</div>
            </div>
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
        `;
        grid.appendChild(card);
    });
}
