import { useState } from 'react';
import { Bell, Plus, Trash2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Label } from './ui/label';
import { toast } from 'sonner';

interface Alert {
  id: string;
  metric: string;
  pair: string;
  operator: string;
  value: number;
  active: boolean;
}

interface AlertsPanelProps {
  onAddAlert: (alert: Omit<Alert, 'id' | 'active'>) => void;
}

export const AlertsPanel = ({ onAddAlert }: AlertsPanelProps) => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [metric, setMetric] = useState('zscore');
  const [pair, setPair] = useState('BTCUSDT-ETHUSDT');
  const [operator, setOperator] = useState('>');
  const [value, setValue] = useState('2');

  const handleAddAlert = () => {
    const numValue = parseFloat(value);
    if (isNaN(numValue)) {
      toast.error('Invalid value');
      return;
    }

    const newAlert: Alert = {
      id: `alert-${Date.now()}`,
      metric,
      pair,
      operator,
      value: numValue,
      active: true,
    };

    setAlerts([...alerts, newAlert]);
    onAddAlert({ metric, pair, operator, value: numValue });
    toast.success('Alert created');
  };

  const handleRemoveAlert = (id: string) => {
    setAlerts(alerts.filter(a => a.id !== id));
    toast.info('Alert removed');
  };

  return (
    <Card className="bg-gradient-card border-border/50 shadow-card">
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <Bell className="w-5 h-5" />
          Alerts
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Create Alert Form */}
        <div className="space-y-3 p-3 rounded-lg bg-secondary/30 border border-border/50">
          <div className="space-y-2">
            <Label className="text-xs">Metric</Label>
            <Select value={metric} onValueChange={setMetric}>
              <SelectTrigger className="h-8 bg-input">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="zscore">Z-Score</SelectItem>
                <SelectItem value="spread">Spread</SelectItem>
                <SelectItem value="correlation">Correlation</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label className="text-xs">Pair</Label>
            <Input
              value={pair}
              onChange={(e) => setPair(e.target.value)}
              className="h-8 bg-input text-sm"
              placeholder="BTCUSDT-ETHUSDT"
            />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-2">
              <Label className="text-xs">Operator</Label>
              <Select value={operator} onValueChange={setOperator}>
                <SelectTrigger className="h-8 bg-input">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value=">">{'>'}</SelectItem>
                  <SelectItem value="<">{'<'}</SelectItem>
                  <SelectItem value=">=">{'≥'}</SelectItem>
                  <SelectItem value="<=">{'≤'}</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label className="text-xs">Value</Label>
              <Input
                type="number"
                value={value}
                onChange={(e) => setValue(e.target.value)}
                className="h-8 bg-input text-sm font-mono"
                step="0.1"
              />
            </div>
          </div>

          <Button
            onClick={handleAddAlert}
            size="sm"
            className="w-full bg-primary hover:bg-primary/90"
          >
            <Plus className="w-4 h-4 mr-2" />
            Add Alert
          </Button>
        </div>

        {/* Active Alerts List */}
        <div className="space-y-2">
          {alerts.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">
              No active alerts
            </p>
          ) : (
            alerts.map(alert => (
              <div
                key={alert.id}
                className="flex items-center justify-between p-2 rounded-md bg-secondary/50 text-sm"
              >
                <div className="flex-1">
                  <p className="font-medium">
                    {alert.metric} {alert.operator} {alert.value}
                  </p>
                  <p className="text-xs text-muted-foreground">{alert.pair}</p>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleRemoveAlert(alert.id)}
                  className="h-8 w-8 p-0"
                >
                  <Trash2 className="w-4 h-4 text-destructive" />
                </Button>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
};
