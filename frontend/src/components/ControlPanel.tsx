import { useState } from 'react';
import { Play, Square, Trash2, Download, AlertCircle } from 'lucide-react';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Label } from './ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Input } from './ui/input';
import { AVAILABLE_SYMBOLS, TIMEFRAMES, REGRESSION_TYPES, DEFAULT_ROLLING_WINDOW } from '@/utils/constants';
import { toast } from 'sonner';

interface ControlPanelProps {
  isStreaming: boolean;
  onStartStream: () => void;
  onStopStream: () => void;
  onClearBuffer: () => void;
  onDownloadData: () => void;
  selectedSymbols: string[];
  onSymbolsChange: (symbols: string[]) => void;
  timeframe: string;
  onTimeframeChange: (tf: string) => void;
  rollingWindow: number;
  onRollingWindowChange: (window: number) => void;
  regressionType: string;
  onRegressionTypeChange: (type: string) => void;
  onRunADF: () => void;
}

export const ControlPanel = ({
  isStreaming,
  onStartStream,
  onStopStream,
  onClearBuffer,
  onDownloadData,
  selectedSymbols,
  onSymbolsChange,
  timeframe,
  onTimeframeChange,
  rollingWindow,
  onRollingWindowChange,
  regressionType,
  onRegressionTypeChange,
  onRunADF,
}: ControlPanelProps) => {
  const [tempWindow, setTempWindow] = useState(rollingWindow.toString());

  const handleWindowChange = (value: string) => {
    setTempWindow(value);
    const numValue = parseInt(value);
    if (!isNaN(numValue) && numValue > 0) {
      onRollingWindowChange(numValue);
    }
  };

  const handleSymbolToggle = (symbol: string) => {
    if (selectedSymbols.includes(symbol)) {
      // Always allow deselecting if more than one selected
      if (selectedSymbols.length > 1) {
        onSymbolsChange(selectedSymbols.filter(s => s !== symbol));
      } else {
        toast.error('At least one symbol must be selected');
      }
    } else {
      // Only allow ONE symbol at a time
      if (selectedSymbols.length < 1) {
        onSymbolsChange([...selectedSymbols, symbol]);
      } else {
        // Replace the current symbol with the new one
        onSymbolsChange([symbol]);
        toast.info(`Switched to ${symbol}`);
      }
    }
  };

  return (
    <div className="space-y-4">
      {/* Stream Controls */}
      <Card className="bg-gradient-card border-border/50 shadow-card">
        <CardHeader>
          <CardTitle className="text-lg">Stream Controls</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 gap-2">
            <Button
              onClick={onStartStream}
              disabled={isStreaming}
              className="w-full bg-primary hover:bg-primary/90"
            >
              <Play className="w-4 h-4 mr-2" />
              Start
            </Button>
            <Button
              onClick={onStopStream}
              disabled={!isStreaming}
              variant="destructive"
              className="w-full"
            >
              <Square className="w-4 h-4 mr-2" />
              Stop
            </Button>
          </div>
          
          <div className="grid grid-cols-2 gap-2">
            <Button
              onClick={onClearBuffer}
              variant="outline"
              className="w-full"
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Clear
            </Button>
            <Button
              onClick={onDownloadData}
              variant="outline"
              className="w-full"
            >
              <Download className="w-4 h-4 mr-2" />
              Export
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Symbol Selection */}
      <Card className="bg-gradient-card border-border/50 shadow-card">
        <CardHeader>
          <CardTitle className="text-lg">Symbols</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {AVAILABLE_SYMBOLS.map(symbol => (
              <button
                key={symbol}
                onClick={() => handleSymbolToggle(symbol)}
                className={`w-full px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  selectedSymbols.includes(symbol)
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-secondary hover:bg-secondary/80 text-secondary-foreground'
                }`}
              >
                {symbol}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Parameters */}
      <Card className="bg-gradient-card border-border/50 shadow-card">
        <CardHeader>
          <CardTitle className="text-lg">Parameters</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Timeframe</Label>
            <Select value={timeframe} onValueChange={onTimeframeChange}>
              <SelectTrigger className="w-full bg-input">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {TIMEFRAMES.map(tf => (
                  <SelectItem key={tf.value} value={tf.value}>
                    {tf.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Rolling Window</Label>
            <Input
              type="number"
              value={tempWindow}
              onChange={(e) => handleWindowChange(e.target.value)}
              className="bg-input font-mono"
              min="1"
            />
          </div>

          <div className="space-y-2">
            <Label>Regression Type</Label>
            <Select value={regressionType} onValueChange={onRegressionTypeChange}>
              <SelectTrigger className="w-full bg-input">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {REGRESSION_TYPES.map(type => (
                  <SelectItem key={type.value} value={type.value}>
                    {type.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <Button
            onClick={onRunADF}
            variant="outline"
            className="w-full"
          >
            <AlertCircle className="w-4 h-4 mr-2" />
            Run ADF Test
          </Button>
        </CardContent>
      </Card>
    </div>
  );
};
