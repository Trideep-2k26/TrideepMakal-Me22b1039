"""
API routes for alert operations.
Endpoints: /alerts, /alerts/active, /alerts/{id}
"""
from fastapi import APIRouter, HTTPException, Body
from typing import List, Optional
from pydantic import BaseModel, Field

from utils import log
from core import alerts_engine

router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertCreate(BaseModel):
    """Request model for creating an alert."""
    metric: str = Field(..., description="Metric to monitor (zscore, spread, correlation, price)")
    pair: str = Field(..., description="Trading pair or single symbol")
    op: str = Field(..., alias="op", description="Comparison operator (>, <, >=, <=, ==)")
    value: float = Field(..., description="Threshold value")


class AlertResponse(BaseModel):
    """Response model for alert."""
    id: str
    metric: str
    pair: str
    operator: str
    value: float
    active: bool
    created_at: str
    triggered_at: Optional[str] = None
    trigger_count: int


@router.post("", response_model=AlertResponse)
async def create_alert(alert: AlertCreate = Body(...)):
    """
    Create a new alert rule.
    
    Args:
        alert: Alert configuration
        
    Returns:
        Created alert with ID
    """
    try:
        # Validate metric
        valid_metrics = ["zscore", "spread", "correlation", "price"]
        if alert.metric.lower() not in valid_metrics:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid metric. Must be one of: {valid_metrics}"
            )
        
        # Validate operator
        valid_operators = [">", "<", ">=", "<=", "=="]
        if alert.op not in valid_operators:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid operator. Must be one of: {valid_operators}"
            )
        
        # Create alert
        created_alert = alerts_engine.add_alert(
            metric=alert.metric,
            pair=alert.pair,
            operator=alert.op,
            value=alert.value
        )
        
        log.info(f"Created alert: {created_alert.id}")
        
        return AlertResponse(
            id=created_alert.id,
            metric=created_alert.metric,
            pair=created_alert.pair,
            operator=created_alert.operator,
            value=created_alert.value,
            active=created_alert.active,
            created_at=created_alert.created_at,
            triggered_at=created_alert.triggered_at,
            trigger_count=created_alert.trigger_count
        )
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error creating alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[AlertResponse])
async def get_alerts():
    """
    Get all alert rules.
    
    Returns:
        List of all alerts
    """
    try:
        alerts = alerts_engine.get_all_alerts()
        
        return [
            AlertResponse(
                id=a.id,
                metric=a.metric,
                pair=a.pair,
                operator=a.operator,
                value=a.value,
                active=a.active,
                created_at=a.created_at,
                triggered_at=a.triggered_at,
                trigger_count=a.trigger_count
            )
            for a in alerts
        ]
    
    except Exception as e:
        log.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active")
async def get_triggered_alerts(limit: Optional[int] = None):
    """
    Get triggered alert notifications.
    
    Args:
        limit: Maximum number of notifications to return
        
    Returns:
        List of triggered alert notifications
    """
    try:
        notifications = alerts_engine.get_triggered_alerts(limit)
        
        return [
            {
                "id": n.id,
                "alert_id": n.alert_id,
                "message": n.message,
                "metric": n.metric,
                "pair": n.pair,
                "actual_value": n.actual_value,
                "threshold_value": n.threshold_value,
                "ts": n.ts
            }
            for n in notifications
        ]
    
    except Exception as e:
        log.error(f"Error getting triggered alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: str):
    """
    Get a specific alert by ID.
    
    Args:
        alert_id: Alert ID
        
    Returns:
        Alert details
    """
    try:
        alert = alerts_engine.get_alert(alert_id)
        
        if not alert:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
        
        return AlertResponse(
            id=alert.id,
            metric=alert.metric,
            pair=alert.pair,
            operator=alert.operator,
            value=alert.value,
            active=alert.active,
            created_at=alert.created_at,
            triggered_at=alert.triggered_at,
            trigger_count=alert.trigger_count
        )
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{alert_id}")
async def delete_alert(alert_id: str):
    """
    Delete an alert rule.
    
    Args:
        alert_id: Alert ID to delete
        
    Returns:
        Success message
    """
    try:
        removed = alerts_engine.remove_alert(alert_id)
        
        if not removed:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
        
        return {"status": "ok", "message": f"Deleted alert {alert_id}"}
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error deleting alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear")
async def clear_triggered_alerts():
    """
    Clear triggered alerts history.
    
    Returns:
        Success message
    """
    try:
        alerts_engine.clear_triggered_alerts()
        return {"status": "ok", "message": "Cleared triggered alerts"}
    
    except Exception as e:
        log.error(f"Error clearing triggered alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))
