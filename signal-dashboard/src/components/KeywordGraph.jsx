import { Radar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend
);

export default function KeywordGraph({ data }) {
  if (!data || Object.keys(data).length === 0) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '200px', color: 'var(--text-muted)' }}>
        No keyword data available
      </div>
    );
  }

  // Sort keywords by frequency and take top 6
  const sortedKeywords = Object.entries(data)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6);

  const labels = sortedKeywords.map(item => item[0]);
  const frequencies = sortedKeywords.map(item => item[1]);

  const chartData = {
    labels: labels,
    datasets: [
      {
        label: 'Keyword Frequency',
        data: frequencies,
        backgroundColor: 'rgba(6, 182, 212, 0.2)', // Accent cyan with opacity
        borderColor: 'rgba(6, 182, 212, 1)',
        borderWidth: 2,
        pointBackgroundColor: 'rgba(6, 182, 212, 1)',
        pointBorderColor: '#fff',
        pointHoverBackgroundColor: '#fff',
        pointHoverBorderColor: 'rgba(6, 182, 212, 1)',
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      r: {
        angleLines: { color: 'rgba(255, 255, 255, 0.1)' },
        grid: { color: 'rgba(255, 255, 255, 0.1)' },
        pointLabels: {
          color: '#e2e8f0',
          font: { size: 12, family: 'Inter' }
        },
        ticks: { display: false, stepSize: 1 },
      },
    },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: 'rgba(16, 26, 46, 0.9)',
        titleColor: '#fff',
        bodyColor: '#cbd5e1',
        borderColor: 'rgba(65, 84, 126, 0.6)',
        borderWidth: 1,
      }
    },
  };

  return (
    <div style={{ height: '250px', width: '100%', padding: '10px' }}>
      <Radar data={chartData} options={options} />
    </div>
  );
}
