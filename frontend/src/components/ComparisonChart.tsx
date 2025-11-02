import { useMemo, useState } from 'react';
import Plot from 'react-plotly.js';
import type { Data } from 'plotly.js';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { AssetLogo } from './AssetLogo';
import { cn } from '@/lib/utils';
import { formatPrice, formatSignedPercent } from '@/utils/formatters';
import { getAssetMeta } from '@/utils/assets';

interface PriceData {
  ts: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface ComparisonChartProps {
  data1: PriceData[];
  data2: PriceData[];
  symbol1: string;
  symbol2: string;
  spread?: Array<{ ts: string; value: number }>;
  zscore?: Array<{ ts: string; value: number }>;
}

export const ComparisonChart = ({
  data1,
  data2,
  symbol1,
  symbol2,
  spread = [],
  zscore = [],
}: ComparisonChartProps) => {
  const [showSpread, setShowSpread] = useState(true);

  const meta1 = getAssetMeta(symbol1);
  const meta2 = getAssetMeta(symbol2);

  const summary1 = useMemo(() => {
    if (!data1 || data1.length === 0) return { price: 0, changePercent: 0 };
    const closes = data1.map(d => d.close);
    const price = closes[closes.length - 1];
    const open = closes[0];
    const change = price - open;
    const changePercent = open !== 0 ? (change / open) * 100 : 0;
    return { price, changePercent };
  }, [data1]);

  const summary2 = useMemo(() => {
    if (!data2 || data2.length === 0) return { price: 0, changePercent: 0 };
    const closes = data2.map(d => d.close);
    const price = closes[closes.length - 1];
    const open = closes[0];
    const change = price - open;
    const changePercent = open !== 0 ? (change / open) * 100 : 0;
    return { price, changePercent };
  }, [data2]);

  // Normalize prices to percentage change for comparison
  const normalizedData1 = useMemo(() => {
    if (data1.length === 0) return [];
    const base = data1[0].close;
    return data1.map(d => ({
      ...d,
      close: ((d.close - base) / base) * 100,
      open: ((d.open - base) / base) * 100,
      high: ((d.high - base) / base) * 100,
      low: ((d.low - base) / base) * 100,
    }));
  }, [data1]);

  const normalizedData2 = useMemo(() => {
    if (data2.length === 0) return [];
    const base = data2[0].close;
    return data2.map(d => ({
      ...d,
      close: ((d.close - base) / base) * 100,
      open: ((d.open - base) / base) * 100,
      high: ((d.high - base) / base) * 100,
      low: ((d.low - base) / base) * 100,
    }));
  }, [data2]);

  const chartData = useMemo(() => {
    const traces: Data[] = [];

    if (normalizedData1.length > 0) {
      traces.push({
        type: 'scatter' as const,
        mode: 'lines' as const,
        x: normalizedData1.map(d => d.ts),
        y: normalizedData1.map(d => d.close),
        name: symbol1,
        line: { color: '#3b82f6', width: 2 },
        hovertemplate: `${symbol1}<br>%{y:.2f}%<extra></extra>`,
      });
    }

    if (normalizedData2.length > 0) {
      traces.push({
        type: 'scatter' as const,
        mode: 'lines' as const,
        x: normalizedData2.map(d => d.ts),
        y: normalizedData2.map(d => d.close),
        name: symbol2,
        line: { color: '#f97316', width: 2 },
        hovertemplate: `${symbol2}<br>%{y:.2f}%<extra></extra>`,
      });
    }

    if (showSpread && spread.length > 0) {
      traces.push({
        type: 'scatter' as const,
        mode: 'lines' as const,
        x: spread.map(d => d.ts),
        y: spread.map(d => d.value),
        name: 'Spread',
        line: { color: '#8b5cf6', width: 1.5, dash: 'dot' },
        yaxis: 'y2',
        hovertemplate: 'Spread<br>%{y:.2f}<extra></extra>',
      });
    }

    if (!showSpread && zscore.length > 0) {
      traces.push({
        type: 'scatter' as const,
        mode: 'lines' as const,
        x: zscore.map(d => d.ts),
        y: zscore.map(d => d.value),
        name: 'Z-Score',
        line: { color: '#10b981', width: 1.5 },
        yaxis: 'y2',
        hovertemplate: 'Z-Score<br>%{y:.2f}<extra></extra>',
      });
    }

    return traces;
  }, [normalizedData1, normalizedData2, spread, zscore, symbol1, symbol2, showSpread]);

  const layout = {
    paper_bgcolor: 'hsl(222, 47%, 7%)',
    plot_bgcolor: 'hsl(220, 26%, 10%)',
    font: { color: 'hsl(214, 32%, 91%)' },
    xaxis: {
      gridcolor: 'hsl(220, 20%, 20%)',
      showgrid: true,
      type: 'date' as const,
      zeroline: false,
      ticksuffix: ' ',
    },
    yaxis: {
      gridcolor: 'hsl(220, 20%, 20%)',
      showgrid: true,
      zeroline: true,
      zerolinecolor: 'hsl(220, 20%, 30%)',
      ticksuffix: '%',
      title: 'Price Change (%)',
    },
    yaxis2: {
      overlaying: 'y' as const,
      side: 'right' as const,
      showgrid: false,
      title: showSpread ? 'Spread' : 'Z-Score',
      titlefont: { color: showSpread ? '#8b5cf6' : '#10b981' },
      tickfont: { color: showSpread ? '#8b5cf6' : '#10b981' },
    },
    margin: { l: 60, r: 60, t: 12, b: 40 },
    height: 420,
    hovermode: 'x unified' as const,
    dragmode: 'pan' as const,
    legend: {
      orientation: 'h' as const,
      x: 0,
      y: 1.1,
      bgcolor: 'rgba(0,0,0,0.3)',
    },
  };

  const config = {
    displayModeBar: true,
    displaylogo: false,
    responsive: true,
    modeBarButtonsToRemove: ['lasso2d', 'select2d'],
  };

  return (
    <Card className="bg-gradient-card border-border/50 shadow-card overflow-hidden">
      <CardHeader className="space-y-4 bg-slate-900/40 border-b border-border/40">
        <CardTitle className="text-lg">Comparison Chart</CardTitle>
        <div className="grid grid-cols-2 gap-4">
          <div className="flex items-center gap-3 p-3 rounded-lg border border-blue-500/30 bg-blue-500/5">
            <AssetLogo symbol={symbol1} size="md" />
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold">{meta1.name}</span>
                <Badge variant="secondary" className="text-xs">{meta1.ticker}</Badge>
              </div>
              <div className="text-lg font-bold text-foreground">
                {data1.length > 0 ? `$${formatPrice(summary1.price)}` : '--'}
              </div>
              <div className={cn(
                'text-xs font-medium',
                summary1.changePercent >= 0 ? 'text-emerald-400' : 'text-rose-400'
              )}>
                {data1.length > 0 ? formatSignedPercent(summary1.changePercent) : '--'}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3 p-3 rounded-lg border border-orange-500/30 bg-orange-500/5">
            <AssetLogo symbol={symbol2} size="md" />
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold">{meta2.name}</span>
                <Badge variant="secondary" className="text-xs">{meta2.ticker}</Badge>
              </div>
              <div className="text-lg font-bold text-foreground">
                {data2.length > 0 ? `$${formatPrice(summary2.price)}` : '--'}
              </div>
              <div className={cn(
                'text-xs font-medium',
                summary2.changePercent >= 0 ? 'text-emerald-400' : 'text-rose-400'
              )}>
                {data2.length > 0 ? formatSignedPercent(summary2.changePercent) : '--'}
              </div>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            className={cn(
              'px-3 py-1.5 text-xs font-medium rounded-md transition-colors',
              showSpread
                ? 'bg-purple-600/80 text-white'
                : 'bg-slate-800 text-muted-foreground hover:text-foreground'
            )}
            onClick={() => setShowSpread(true)}
          >
            Show Spread
          </button>
          <button
            className={cn(
              'px-3 py-1.5 text-xs font-medium rounded-md transition-colors',
              !showSpread
                ? 'bg-emerald-600/80 text-white'
                : 'bg-slate-800 text-muted-foreground hover:text-foreground'
            )}
            onClick={() => setShowSpread(false)}
          >
            Show Z-Score
          </button>
        </div>
      </CardHeader>

      <CardContent className="pt-6">
        {data1.length > 0 || data2.length > 0 ? (
          <Plot data={chartData} layout={layout} config={config} style={{ width: '100%' }} />
        ) : (
          <div className="h-[420px] flex items-center justify-center text-muted-foreground">
            No comparison data available
          </div>
        )}
      </CardContent>
    </Card>
  );
};
