export default function EarlyDiscoveryTable({ data, onRowClick }) {
  return (
    <div className="glass-card" style={{ padding: 0, overflow: 'hidden' }}>
      <div style={{ padding: '20px 20px 10px 20px', borderBottom: '1px solid var(--border-color)' }}>
        <h3 style={{ fontSize: 16 }}>Early Discovery</h3>
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Stock</th>
              <th>Mentions</th>
              <th>Unique Users</th>
              <th>Hidden Score</th>
              <th>Trend Score</th>
              <th>Risk</th>
              <th>Sentiment</th>
            </tr>
          </thead>
          <tbody>
            {data.map((row, idx) => (
              <tr key={idx} onClick={() => onRowClick(row)}>
                <td style={{ fontWeight: 600, color: '#fff' }}>{row.Stock}</td>
                <td>{row.Mentions}</td>
                <td>{row.UniqueUsers}</td>
                <td>
                  <span style={{ color: row.Score > 70 ? 'var(--accent-green)' : '#fff' }}>
                    {row.Score}
                  </span>
                </td>
                <td>{Math.floor(Math.random() * 40 + 50)}</td>
                <td>
                  <span className={`badge ${row.Risk === '偏負面' ? 'badge-red' : 'badge-green'}`}>
                    {row.Risk || '無'}
                  </span>
                </td>
                <td>
                  <span className={`badge ${row.Score > 60 ? 'badge-cyan' : 'badge-orange'}`}>
                    {row.Score > 60 ? 'Bullish' : 'Neutral'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
