import { Zap, TrendingUp, Eye, Target } from 'lucide-react';

export default function KPICards() {
  return (
    <div className="grid-layout">
      <div className="col-span-3 glass-card">
        <div className="kpi-label">
          <Zap size={16} color="var(--accent-orange)" />
          🔥 今日 AI 發現
        </div>
        <div className="kpi-value" style={{ color: 'var(--accent-orange)' }}>18</div>
      </div>
      <div className="col-span-3 glass-card">
        <div className="kpi-label">
          <Eye size={16} color="var(--accent-cyan)" />
          Hidden Signals
        </div>
        <div className="kpi-value">6</div>
      </div>
      <div className="col-span-3 glass-card">
        <div className="kpi-label">
          <TrendingUp size={16} color="var(--accent-green)" />
          Trend Spikes
        </div>
        <div className="kpi-value">3</div>
      </div>
      <div className="col-span-3 glass-card">
        <div className="kpi-label">
          <Target size={16} color="var(--accent-red)" />
          High Conviction
        </div>
        <div className="kpi-value">5</div>
      </div>
    </div>
  );
}
