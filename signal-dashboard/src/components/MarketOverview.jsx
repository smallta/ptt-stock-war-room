import React from 'react';

export default function MarketOverview({ marketData }) {
  if (!marketData) return null;

  const { FearGreedIndex, SectorRotation, TotalCommentsParsed, MarketSummary } = marketData;

  // Determine sentiment color and label
  let sentimentColor = '#fbbf24'; // neutral yellow
  let sentimentLabel = '中立震盪';
  if (FearGreedIndex >= 70) {
    sentimentColor = '#22c55e'; // green greed
    sentimentLabel = '極度貪婪';
  } else if (FearGreedIndex <= 30) {
    sentimentColor = '#ef4444'; // red fear
    sentimentLabel = '極度恐懼';
  } else if (FearGreedIndex >= 55) {
    sentimentColor = '#84cc16';
    sentimentLabel = '偏向樂觀';
  } else if (FearGreedIndex <= 45) {
    sentimentColor = '#f97316';
    sentimentLabel = '偏向悲觀';
  }

  // Calculate max mentions for the bar chart scaling
  const maxSectorMentions = SectorRotation && SectorRotation.length > 0 
    ? Math.max(...SectorRotation.map(s => s.Mentions)) 
    : 1;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', marginBottom: '24px' }}>
      
      {/* AI Market Summary */}
      {MarketSummary && (
        <div className="glass-card" style={{ padding: '20px', display: 'flex', alignItems: 'center', gap: '16px', background: 'linear-gradient(90deg, rgba(30,58,138,0.5) 0%, rgba(15,23,42,0.8) 100%)', borderLeft: '4px solid #38bdf8' }}>
          <div style={{ fontSize: '24px' }}>🤖</div>
          <div>
            <div style={{ fontSize: '14px', color: '#38bdf8', fontWeight: 'bold', marginBottom: '4px' }}>AI 盤後速報</div>
            <div style={{ fontSize: '16px', color: '#f8fafc', lineHeight: '1.5' }}>{MarketSummary}</div>
          </div>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '24px' }}>
        
        {/* Fear & Greed Index */}
        <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '24px' }}>
          <h3 style={{ alignSelf: 'flex-start', marginBottom: 16 }}>恐懼與貪婪指數</h3>
        
        {/* Gauge visualization (simple SVG arc) */}
        <div style={{ position: 'relative', width: '200px', height: '100px', overflow: 'hidden' }}>
          <div style={{
            position: 'absolute', top: 0, left: 0, width: '200px', height: '200px',
            borderRadius: '50%', border: '20px solid rgba(255,255,255,0.05)',
            borderBottomColor: 'transparent', borderLeftColor: 'transparent',
            transform: 'rotate(-45deg)'
          }}></div>
          <div style={{
            position: 'absolute', top: 0, left: 0, width: '200px', height: '200px',
            borderRadius: '50%', border: '20px solid transparent',
            borderTopColor: sentimentColor, borderRightColor: sentimentColor,
            transform: `rotate(${ -45 + (FearGreedIndex / 100) * 180 }deg)`,
            transition: 'transform 1s ease-out'
          }}></div>
          <div style={{ position: 'absolute', bottom: 0, left: 0, width: '100%', textAlign: 'center' }}>
            <span style={{ fontSize: '36px', fontWeight: 'bold', color: sentimentColor }}>{FearGreedIndex}</span>
          </div>
        </div>
        
        <div style={{ marginTop: 12, fontSize: '18px', fontWeight: 600, color: sentimentColor }}>
          {sentimentLabel}
        </div>
        <div style={{ marginTop: 8, fontSize: '12px', color: 'var(--text-muted)' }}>
          基於 {TotalCommentsParsed} 則即時推文計算
        </div>
      </div>

      {/* Sector Rotation Heatmap */}
      <div className="glass-card" style={{ padding: '24px' }}>
        <h3 style={{ marginBottom: 16 }}>族群輪動熱力圖 (Top 5)</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {SectorRotation && SectorRotation.map((sector, idx) => {
            const widthPct = Math.max((sector.Mentions / maxSectorMentions) * 100, 5);
            return (
              <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                <div style={{ width: '120px', fontSize: '14px', fontWeight: 500 }}>
                  {sector.Sector}
                </div>
                <div style={{ flex: 1, height: '28px', background: 'rgba(255,255,255,0.05)', borderRadius: '4px', position: 'relative', overflow: 'hidden' }}>
                  <div style={{
                    position: 'absolute', top: 0, left: 0, height: '100%', width: `${widthPct}%`,
                    background: 'linear-gradient(90deg, rgba(6,182,212,0.8) 0%, rgba(56,189,248,0.8) 100%)',
                    borderRadius: '4px', transition: 'width 1s ease-out'
                  }}></div>
                  <div style={{ position: 'absolute', top: 0, left: 0, height: '100%', display: 'flex', alignItems: 'center', paddingLeft: '12px', fontSize: '12px', color: '#fff' }}>
                    {sector.Mentions} 次提及
                  </div>
                </div>
                <div style={{ width: '180px', fontSize: '12px', color: 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  領頭：{sector.TopStocks.join(', ')}
                </div>
              </div>
            );
          })}
          {(!SectorRotation || SectorRotation.length === 0) && (
            <div style={{ color: 'var(--text-muted)' }}>目前無族群資料。</div>
          )}
        </div>
      </div>

      </div>
    </div>
  );
}
