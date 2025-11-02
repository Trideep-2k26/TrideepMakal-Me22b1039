"""
Alerts engine for monitoring trading conditions and triggering notifications.
Supports user-defined alert rules based on metrics and thresholds.
"""
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from uuid import uuid4

from utils import log
from core.analytics import analytics_engine


@dataclass
class Alert:
    """Alert rule definition."""
    id: str = field(default_factory=lambda: str(uuid4()))
    metric: str = ""  # zscore, spread, correlation, price
    pair: str = ""    # BTCUSDT-ETHUSDT or single symbol
    operator: str = "" # >, <, >=, <=, ==
    value: float = 0.0
    active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    triggered_at: Optional[str] = None
    trigger_count: int = 0


@dataclass
class AlertNotification:
    """Alert trigger notification."""
    id: str
    alert_id: str
    message: str
    metric: str
    pair: str
    actual_value: float
    threshold_value: float
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AlertsEngine:
    """
    Manages alert rules and monitors conditions.
    
    Features:
    - User-defined alert rules
    - Real-time condition monitoring
    - Alert history and notifications
    - Callback system for alert triggers
    """
    
    def __init__(self):
        """Initialize alerts engine."""
        self.alerts: Dict[str, Alert] = {}
        self.triggered_alerts: List[AlertNotification] = []
        self.callbacks: List[Callable] = []
        self.monitoring_task: Optional[asyncio.Task] = None
        self.is_monitoring = False
        
        log.info("Alerts Engine initialized")
    
    def add_alert(
        self,
        metric: str,
        pair: str,
        operator: str,
        value: float
    ) -> Alert:
        """
        Add a new alert rule.
        
        Args:
            metric: Metric to monitor (zscore, spread, correlation, price)
            pair: Trading pair or single symbol
            operator: Comparison operator (>, <, >=, <=, ==)
            value: Threshold value
            
        Returns:
            Created Alert object
        """
        alert = Alert(
            metric=metric.lower(),
            pair=pair.upper(),
            operator=operator,
            value=value
        )
        
        self.alerts[alert.id] = alert
        log.info(f"Added alert {alert.id}: {metric} {operator} {value} for {pair}")
        
        return alert
    
    def remove_alert(self, alert_id: str) -> bool:
        """
        Remove an alert rule.
        
        Args:
            alert_id: Alert ID to remove
            
        Returns:
            True if removed, False if not found
        """
        if alert_id in self.alerts:
            del self.alerts[alert_id]
            log.info(f"Removed alert {alert_id}")
            return True
        return False
    
    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Get alert by ID."""
        return self.alerts.get(alert_id)
    
    def get_all_alerts(self) -> List[Alert]:
        """Get all alert rules."""
        return list(self.alerts.values())
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alert rules."""
        return [a for a in self.alerts.values() if a.active]
    
    def get_triggered_alerts(self, limit: Optional[int] = None) -> List[AlertNotification]:
        """
        Get triggered alert notifications.
        
        Args:
            limit: Maximum number of notifications to return (most recent)
            
        Returns:
            List of alert notifications
        """
        if limit:
            return self.triggered_alerts[-limit:]
        return self.triggered_alerts
    
    def clear_triggered_alerts(self):
        """Clear triggered alerts history."""
        self.triggered_alerts.clear()
        log.info("Cleared triggered alerts history")
    
    def register_callback(self, callback: Callable):
        """
        Register a callback function to be called when an alert triggers.
        
        Args:
            callback: Async function that takes AlertNotification as argument
        """
        self.callbacks.append(callback)
    
    async def check_alert(self, alert: Alert) -> Optional[AlertNotification]:
        """
        Check if an alert condition is met.
        
        Args:
            alert: Alert to check
            
        Returns:
            AlertNotification if triggered, None otherwise
        """
        try:
            # Get current value for the metric
            actual_value = await self._get_metric_value(alert.metric, alert.pair)
            
            if actual_value is None:
                return None
            
            # Check condition
            triggered = self._evaluate_condition(
                actual_value,
                alert.operator,
                alert.value
            )
            
            if triggered:
                # Create notification
                notification = AlertNotification(
                    id=str(uuid4()),
                    alert_id=alert.id,
                    message=f"{alert.metric} {alert.operator} {alert.value} for {alert.pair}",
                    metric=alert.metric,
                    pair=alert.pair,
                    actual_value=actual_value,
                    threshold_value=alert.value
                )
                
                # Update alert
                alert.triggered_at = notification.ts
                alert.trigger_count += 1
                
                log.info(f"Alert triggered: {notification.message} (actual: {actual_value})")
                
                return notification
        
        except Exception as e:
            log.error(f"Error checking alert {alert.id}: {e}")
        
        return None
    
    async def _get_metric_value(self, metric: str, pair: str) -> Optional[float]:
        """Get current value for a metric."""
        from core.data_manager import data_manager
        
        metric = metric.lower()
        
        try:
            if metric == "price":
                # Single symbol price
                return data_manager.get_latest_price(pair)
            
            elif metric in ["zscore", "spread", "correlation"]:
                # Pair metrics - compute analytics
                analytics = analytics_engine.compute_pair_analytics(
                    pair=pair,
                    timeframe="1m",
                    window=60,
                    regression="OLS"
                )
                
                if not analytics:
                    return None
                
                if metric == "zscore" and analytics.get("zscore"):
                    values = analytics["zscore"]
                    return values[-1]["value"] if values else None
                
                elif metric == "spread" and analytics.get("spread"):
                    values = analytics["spread"]
                    return values[-1]["value"] if values else None
                
                elif metric == "correlation" and analytics.get("rolling_corr"):
                    values = analytics["rolling_corr"]
                    return values[-1]["value"] if values else None
        
        except Exception as e:
            log.error(f"Error getting metric value for {metric} @ {pair}: {e}")
        
        return None
    
    def _evaluate_condition(self, actual: float, operator: str, threshold: float) -> bool:
        """Evaluate alert condition."""
        if operator == ">":
            return actual > threshold
        elif operator == "<":
            return actual < threshold
        elif operator == ">=":
            return actual >= threshold
        elif operator == "<=":
            return actual <= threshold
        elif operator == "==":
            return abs(actual - threshold) < 1e-6
        else:
            return False
    
    async def monitor_alerts(self, interval: float = 0.5):
        """
        Background task to monitor all alerts.
        
        Args:
            interval: Check interval in seconds (default 500ms)
        """
        self.is_monitoring = True
        log.info(f"Started alert monitoring (interval: {interval}s)")
        
        while self.is_monitoring:
            try:
                # Check all active alerts
                active_alerts = self.get_active_alerts()
                
                for alert in active_alerts:
                    notification = await self.check_alert(alert)
                    
                    if notification:
                        # Store notification
                        self.triggered_alerts.append(notification)
                        
                        # Call registered callbacks
                        for callback in self.callbacks:
                            try:
                                await callback(notification)
                            except Exception as e:
                                log.error(f"Error in alert callback: {e}")
                
                await asyncio.sleep(interval)
            
            except asyncio.CancelledError:
                log.info("Alert monitoring cancelled")
                break
            except Exception as e:
                log.error(f"Error in alert monitoring loop: {e}")
                await asyncio.sleep(interval)
    
    async def start_monitoring(self, interval: float = 0.5):
        """Start the alert monitoring background task."""
        if self.monitoring_task and not self.monitoring_task.done():
            log.warning("Alert monitoring already running")
            return
        
        self.monitoring_task = asyncio.create_task(self.monitor_alerts(interval))
    
    async def stop_monitoring(self):
        """Stop the alert monitoring background task."""
        self.is_monitoring = False
        
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        log.info("Stopped alert monitoring")


# Global alerts engine instance
alerts_engine = AlertsEngine()
