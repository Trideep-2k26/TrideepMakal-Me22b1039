import { memo } from 'react';
import { TrendingUp, TrendingDown, Activity } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { formatNumber } from '@/utils/formatters';

interface StatsCardProps {
  title: string;
  value: number;
  change?: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
}

const StatsCardComponent = ({ 
  title, 
  value, 
  change, 
  prefix = '', 
  suffix = '',
  decimals = 4 
}: StatsCardProps) => {
  const isPositive = change !== undefined ? change > 0 : false;
  const isNegative = change !== undefined ? change < 0 : false;
  
  // Get status based on title and value
  const getStatus = () => {
    if (title === 'Z-Score') {
      const absZ = Math.abs(value);
      if (absZ > 2.5) return { text: 'Extreme', color: 'text-destructive', bg: 'bg-destructive/10' };
      if (absZ > 2) return { text: 'High', color: 'text-yellow-500', bg: 'bg-yellow-500/10' };
      if (absZ > 1) return { text: 'Medium', color: 'text-blue-400', bg: 'bg-blue-400/10' };
      return { text: 'Normal', color: 'text-success', bg: 'bg-success/10' };
    }
    if (title === 'Correlation') {
      const absCorr = Math.abs(value);
      if (absCorr > 0.9) return { text: 'Very Strong', color: 'text-success', bg: 'bg-success/10' };
      if (absCorr > 0.7) return { text: 'Strong', color: 'text-blue-400', bg: 'bg-blue-400/10' };
      if (absCorr > 0.5) return { text: 'Moderate', color: 'text-yellow-500', bg: 'bg-yellow-500/10' };
      return { text: 'Weak', color: 'text-destructive', bg: 'bg-destructive/10' };
    }
    if (title === 'ADF p-value') {
      if (value < 0.01) return { text: 'Strong Stationary', color: 'text-success', bg: 'bg-success/10' };
      if (value < 0.05) return { text: 'Stationary', color: 'text-blue-400', bg: 'bg-blue-400/10' };
      if (value < 0.1) return { text: 'Weak Stationary', color: 'text-yellow-500', bg: 'bg-yellow-500/10' };
      return { text: 'Non-Stationary', color: 'text-destructive', bg: 'bg-destructive/10' };
    }
    return null;
  };
  
  const status = getStatus();
  
  return (
    <Card className="bg-gradient-card border-border/50 shadow-card hover:border-primary/30 transition-colors">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            {title}
          </CardTitle>
          {status && (
            <span className={`text-xs px-2 py-0.5 rounded ${status.bg} ${status.color} font-medium`}>
              {status.text}
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex items-baseline justify-between">
          <span className={`text-2xl font-bold font-mono ${
            status ? status.color : ''
          }`}>
            {prefix}{formatNumber(value, decimals)}{suffix}
          </span>
          
          {change !== undefined && (
            <div className={`flex items-center gap-1 text-sm font-medium ${
              isPositive ? 'text-success' : isNegative ? 'text-destructive' : 'text-muted-foreground'
            }`}>
              {isPositive ? (
                <TrendingUp className="w-4 h-4" />
              ) : isNegative ? (
                <TrendingDown className="w-4 h-4" />
              ) : (
                <Activity className="w-4 h-4" />
              )}
              <span className="font-mono">{Math.abs(change).toFixed(2)}%</span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

// Memoize with custom comparison - only re-render if value changes significantly
export const StatsCard = memo(StatsCardComponent, (prevProps, nextProps) => {
  // Check if title changed
  if (prevProps.title !== nextProps.title) return false;
  
  // Check if value changed significantly (more than 0.0001)
  const valueThreshold = 0.0001;
  if (Math.abs(prevProps.value - nextProps.value) > valueThreshold) return false;
  
  // Check if change percentage changed significantly
  if (prevProps.change !== undefined && nextProps.change !== undefined) {
    if (Math.abs(prevProps.change - nextProps.change) > 0.01) return false;
  }
  
  // Check if other props changed
  if (prevProps.prefix !== nextProps.prefix || 
      prevProps.suffix !== nextProps.suffix || 
      prevProps.decimals !== nextProps.decimals) {
    return false;
  }
  
  // Props are equal enough - skip re-render
  return true;
});
