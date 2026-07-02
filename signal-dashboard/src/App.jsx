import { useState, useEffect } from 'react';
import Header from './components/Header';
import KPICards from './components/KPICards';
import EarlyDiscoveryTable from './components/EarlyDiscoveryTable';
import KeywordGraph from './components/KeywordGraph';
import MarketOverview from './components/MarketOverview';
import './App.css';

function App() {
  const [tableData, setTableData] = useState([]);
  const [keywordData, setKeywordData] = useState({});
  const [selectedStock, setSelectedStock] = useState(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [detailsData, setDetailsData] = useState({});
  const [marketData, setMarketData] = useState(null);

  const fetchData = () => {
    setLoading(true);
    Promise.all([
      fetch('/api/stocks').then(res => res.json()),
      fetch('/api/details').then(res => res.json()),
      fetch('/api/market').then(res => res.json())
    ]).then(([stocks, details, market]) => {
      setTableData(stocks);
      setDetailsData(details);
      setMarketData(market);
      setLoading(false);
    }).catch(err => {
      console.error("Failed to fetch data", err);
      setLoading(false);
    });
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await fetch('/api/crawl', { method: 'POST' });
      fetchData(); // Reload data after crawler finishes
    } catch (err) {
      console.error("Failed to run crawler", err);
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleRowClick = (stock) => {
    setSelectedStock(stock);
    setDrawerOpen(true);
  };

  const closeDrawer = () => {
    setDrawerOpen(false);
  };

  return (
    <div className="app-container">
      <Header onRefresh={handleRefresh} isRefreshing={isRefreshing} />
      
      <main className="main-content">
        <KPICards />
        
        <MarketOverview marketData={marketData} />
        
        <div className="grid-layout">
          <div className="col-span-8">
             {loading ? <div style={{textAlign:'center', padding:40}}>Loading AI Data...</div> : 
             <EarlyDiscoveryTable data={tableData} onRowClick={handleRowClick} />}
          </div>
          <div className="col-span-4" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            
            <div className="glass-card">
              <h3 style={{ marginBottom: 16 }}>AI Summary</h3>
              <div className="summary-panel">
                <p><strong>Market Insight:</strong> AI model detects increasing discussion volume in semiconductor sector, specifically focusing on advanced packaging capabilities.</p>
                <p><strong>Alert:</strong> Several stocks show high mentions but elevated negative sentiment.</p>
              </div>
            </div>

            <div className="glass-card" style={{ flex: 1 }}>
               <h3 style={{ marginBottom: 16 }}>Market Sentiment Network</h3>
               <p style={{fontSize: 12, color: 'var(--text-muted)'}}>Select a stock from the table to view its keyword distribution in the drawer.</p>
               {/* Global chart placeholder or overall market keyword graph could go here */}
               <div style={{height: 150, display:'flex', alignItems:'center', justifyContent:'center', border:'1px dashed var(--border-color)', borderRadius:8, marginTop: 16}}>
                 <span style={{color: 'var(--text-muted)'}}>Overall Topic Distribution</span>
               </div>
            </div>

          </div>
        </div>
      </main>

      {/* Drawer Overlay */}
      <div className={`drawer-overlay ${drawerOpen ? 'open' : ''}`} onClick={closeDrawer} />
      
      {/* Detail Drawer */}
      <div className={`drawer-panel ${drawerOpen ? 'open' : ''}`}>
        <div className="drawer-header">
          <h2>{selectedStock?.Stock} Details</h2>
          <button className="drawer-close" onClick={closeDrawer}>✕</button>
        </div>
        {selectedStock && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div className="glass-card" style={{ padding: 16 }}>
              <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>Hidden Score</div>
              <div style={{ fontSize: 24, color: 'var(--accent-green)', fontWeight: 'bold' }}>{selectedStock.Score}</div>
            </div>
            
            <div className="glass-card" style={{ padding: 16 }}>
              <h4 style={{ marginBottom: 12 }}>Keyword Distribution</h4>
              <KeywordGraph data={detailsData[selectedStock.Stock]?.Keywords} />
            </div>

            <div className="glass-card" style={{ padding: 16 }}>
              <h4 style={{ marginBottom: 12 }}>Recent Comments</h4>
              {detailsData[selectedStock.Stock]?.Comments?.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12, maxHeight: 300, overflowY: 'auto', paddingRight: 8 }}>
                  {detailsData[selectedStock.Stock].Comments.map((c, i) => (
                    <div key={i} style={{ background: 'rgba(255,255,255,0.03)', padding: 12, borderRadius: 8 }}>
                      <div style={{ color: 'var(--accent-cyan)', fontSize: 12, marginBottom: 4, fontWeight: 500 }}>{c.user}</div>
                      <div style={{ color: '#e2e8f0', fontSize: 13, lineHeight: 1.5 }}>{c.text}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>No recent comments collected.</div>
              )}
            </div>

            <div className="glass-card" style={{ padding: 16 }}>
              <h4 style={{ marginBottom: 12 }}>Metrics</h4>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <span style={{ color: 'var(--text-muted)' }}>Mentions</span>
                <span>{selectedStock.Mentions}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <span style={{ color: 'var(--text-muted)' }}>Unique Users</span>
                <span>{selectedStock.UniqueUsers}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <span style={{ color: 'var(--text-muted)' }}>P/E Ratio</span>
                <span>{selectedStock.PE}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <span style={{ color: 'var(--text-muted)' }}>Risk Factor</span>
                <span style={{ color: selectedStock.Risk !== '無' ? 'var(--accent-red)' : 'var(--accent-green)' }}>{selectedStock.Risk}</span>
              </div>
            </div>
            
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
