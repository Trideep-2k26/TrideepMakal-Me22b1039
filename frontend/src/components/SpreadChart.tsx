import { useMemo } from 'react';
import Plot from 'react-plotly.js';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface DataPoint {
  ts: string;
  value: number;
}

interface SpreadChartProps {
  spread: DataPoint[];
  zscore: DataPoint[];
  pair: string;
}

export const SpreadChart = ({ spread, zscore, pair }: SpreadChartProps) => {
  // Calculate current values and trends
  const currentSpread = spread.length > 0 ? spread[spread.length - 1].value : 0;
  const currentZScore = zscore.length > 0 ? zscore[zscore.length - 1].value : 0;
  const prevZScore = zscore.length > 1 ? zscore[zscore.length - 2].value : currentZScore;
  const zScoreTrend = currentZScore > prevZScore;
  
  // Determine z-score status
  const getZScoreStatus = (z: number) => {
    if (Math.abs(z) > 2.5) return { label: 'Extreme', color: 'text-destructive' };
    if (Math.abs(z) > 2) return { label: 'High', color: 'text-yellow-500' };
    if (Math.abs(z) > 1) return { label: 'Medium', color: 'text-blue-400' };
    return { label: 'Normal', color: 'text-success' };
  };
  
  const zScoreStatus = getZScoreStatus(currentZScore);

  const chartData = useMemo(() => {
    return [
      {
        type: 'scatter' as const,
        mode: 'lines' as const,
        x: spread.map(d => d.ts),
        y: spread.map(d => d.value),
        name: 'Spread',
        line: { color: '#facc15', width: 2.5 }, // Binance yellow
        yaxis: 'y',
        fill: 'tozeroy',
        fillcolor: 'rgba(250, 204, 21, 0.1)',
        hovertemplate: '<b>Spread</b><br>%{y:.4f}<extra></extra>',
      },
      {
        type: 'scatter' as const,
        mode: 'lines' as const,
        x: zscore.map(d => d.ts),
        y: zscore.map(d => d.value),
        name: 'Z-Score',
        line: { color: '#8b5cf6', width: 2.5 }, // Purple
        yaxis: 'y2',
        hovertemplate: '<b>Z-Score</b><br>%{y:.2f}<extra></extra>',
      },
      // Z-score threshold zones
      {
        type: 'scatter' as const,
        mode: 'lines' as const,
        x: zscore.map(d => d.ts),
        y: Array(zscore.length).fill(2.5),
        name: 'Extreme Buy',
        line: { color: '#f6465d', width: 1, dash: 'dot' },
        yaxis: 'y2',
        showlegend: false,
        hoverinfo: 'skip',
      },
      {
        type: 'scatter' as const,
        mode: 'lines' as const,
        x: zscore.map(d => d.ts),
        y: Array(zscore.length).fill(2),
        name: 'Buy Signal',
        line: { color: '#f6465d', width: 1, dash: 'dash' },
        yaxis: 'y2',
        showlegend: false,
        hoverinfo: 'skip',
      },
      {
        type: 'scatter' as const,
        mode: 'lines' as const,
        x: zscore.map(d => d.ts),
        y: Array(zscore.length).fill(0),
        name: 'Mean',
        line: { color: '#64748b', width: 1 },
        yaxis: 'y2',
        showlegend: false,
        hoverinfo: 'skip',
      },
      {
        type: 'scatter' as const,
        mode: 'lines' as const,
        x: zscore.map(d => d.ts),
        y: Array(zscore.length).fill(-2),
        name: 'Sell Signal',
        line: { color: '#0ecb81', width: 1, dash: 'dash' },
        yaxis: 'y2',
        showlegend: false,
        hoverinfo: 'skip',
      },
      {
        type: 'scatter' as const,
        mode: 'lines' as const,
        x: zscore.map(d => d.ts),
        y: Array(zscore.length).fill(-2.5),
        name: 'Extreme Sell',
        line: { color: '#0ecb81', width: 1, dash: 'dot' },
        yaxis: 'y2',
        showlegend: false,
        hoverinfo: 'skip',
      },
    ];
  }, [spread, zscore]);

  const layout = {
    paper_bgcolor: '#0a0e1a',
    plot_bgcolor: '#0a0e1a',
    font: { color: '#e2e8f0', family: 'Inter, system-ui, sans-serif' },
    xaxis: {
      gridcolor: 'rgba(30, 35, 50, 0.4)',
      showgrid: true,
      type: 'date' as const,
      tickfont: { size: 11, color: '#94a3b8' },
      zeroline: false,
    },
    yaxis: {
      gridcolor: 'rgba(30, 35, 50, 0.4)',
      showgrid: true,
      title: {
        text: 'Spread',
        font: { size: 12, color: '#facc15' },
      },
      side: 'left' as const,
      tickfont: { size: 11, color: '#94a3b8' },
      zeroline: true,
      zerolinecolor: 'rgba(100, 116, 139, 0.3)',
    },
    yaxis2: {
      gridcolor: 'rgba(30, 35, 50, 0.2)',
      showgrid: false,
      title: {
        text: 'Z-Score',
        font: { size: 12, color: '#8b5cf6' },
      },
      overlaying: 'y' as const,
      side: 'right' as const,
      tickfont: { size: 11, color: '#94a3b8' },
      zeroline: true,
      zerolinecolor: 'rgba(100, 116, 139, 0.5)',
      zerolinewidth: 2,
    },
    margin: { l: 60, r: 60, t: 10, b: 40 },
    height: 420,
    hovermode: 'x unified' as const,
    dragmode: 'zoom' as const,
    legend: {
      x: 0.01,
      y: 0.99,
      bgcolor: 'rgba(10, 14, 26, 0.9)',
      bordercolor: 'rgba(148, 163, 184, 0.3)',
      borderwidth: 1,
      font: { size: 11, color: '#cbd5e1' },
    },
    hoverlabel: {
      bgcolor: '#1e293b',
      bordercolor: '#334155',
      font: { color: '#f1f5f9', size: 12 },
    },
    shapes: [
      // Highlight extreme zones
      {
        type: 'rect',
        xref: 'paper',
        yref: 'y2',
        x0: 0,
        x1: 1,
        y0: 2,
        y1: 3,
        fillcolor: 'rgba(246, 70, 93, 0.08)',
        line: { width: 0 },
        layer: 'below',
      },
      {
        type: 'rect',
        xref: 'paper',
        yref: 'y2',
        x0: 0,
        x1: 1,
        y0: -3,
        y1: -2,
        fillcolor: 'rgba(14, 203, 129, 0.08)',
        line: { width: 0 },
        layer: 'below',
      },
    ],
  };

  const config = {
    displayModeBar: true,
    displaylogo: false,
    responsive: true,
    modeBarButtonsToRemove: ['lasso2d', 'select2d', 'toImage'],
    scrollZoom: true,
  };

  return (
    <Card className="bg-gradient-card border-border/50 shadow-card">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Spread & Z-Score Analysis - {pair}</CardTitle>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <p className="text-xs text-muted-foreground">Current Spread</p>
              <p className="text-sm font-mono font-semibold text-yellow-500">
                {currentSpread.toFixed(4)}
              </p>
            </div>
            <div className="h-10 w-px bg-border"></div>
            <div className="text-right">
              <p className="text-xs text-muted-foreground">Z-Score</p>
              <div className="flex items-center gap-2">
                <p className={`text-sm font-mono font-bold ${zScoreStatus.color}`}>
                  {currentZScore.toFixed(2)}
                </p>
                {zScoreTrend ? (
                  <TrendingUp className="w-4 h-4 text-success" />
                ) : (
                  <TrendingDown className="w-4 h-4 text-destructive" />
                )}
              </div>
            </div>
            <Badge 
              variant={Math.abs(currentZScore) > 2 ? 'destructive' : 'secondary'}
              className="text-xs"
            >
              {zScoreStatus.label}
            </Badge>
          </div>
        </div>
        
        {/* Trading signals hint */}
        <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-success"></div>
            <span>Z &lt; -2: Mean Reversion (Buy)</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-destructive"></div>
            <span>Z &gt; +2: Mean Reversion (Sell)</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-slate-500"></div>
            <span>|Z| &lt; 1: Normal Range</span>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {spread.length > 0 && zscore.length > 0 ? (
          <Plot
            data={chartData}
            layout={layout}
            config={config}
            style={{ width: '100%' }}
            useResizeHandler
          />
        ) : (
          <div className="h-[420px] flex items-center justify-center text-muted-foreground bg-slate-950/50 rounded-lg">
            <div className="text-center">
              <p className="text-lg">No analytics data available</p>
              <p className="text-sm text-slate-500 mt-1">Start streaming in comparison mode</p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
