import { Bell, Search, Settings, User, RefreshCw } from 'lucide-react';

export default function Header({ onRefresh, isRefreshing }) {
  return (
    <header className="dashboard-header">
      <div className="header-brand">
        <div style={{ width: 32, height: 32, background: 'var(--accent-cyan)', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <span style={{ color: '#000', fontWeight: 'bold' }}>AI</span>
        </div>
        <h1>Investment Intelligence</h1>
      </div>
      <div className="header-actions">
        <div className="search-bar" style={{ display: 'flex', alignItems: 'center', background: 'rgba(255,255,255,0.05)', padding: '6px 12px', borderRadius: 20, border: '1px solid var(--border-color)' }}>
          <Search size={16} color="var(--text-muted)" style={{ marginRight: 8 }} />
          <input type="text" placeholder="Search stocks, topics..." style={{ background: 'transparent', border: 'none', color: '#fff', outline: 'none', width: 200 }} />
        </div>
        <button className="icon-btn" onClick={onRefresh} disabled={isRefreshing} title="Trigger AI Crawler" style={{ width: isRefreshing ? 'auto' : 36, padding: isRefreshing ? '0 12px' : 0, borderRadius: isRefreshing ? 20 : '50%' }}>
          {isRefreshing ? <span style={{fontSize: 12, fontWeight: 500}}>Running...</span> : <RefreshCw size={18} />}
        </button>
        <button className="icon-btn">
          <Bell size={18} />
        </button>
        <button className="icon-btn">
          <Settings size={18} />
        </button>
        <button className="icon-btn">
          <User size={18} />
        </button>
      </div>
    </header>
  );
}
