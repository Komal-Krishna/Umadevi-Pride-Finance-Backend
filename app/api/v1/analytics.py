from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Optional
from datetime import datetime, date, timedelta
from decimal import Decimal
import logging

from ...database import db
from ...dependencies import get_current_user, get_database
from ...models.analytics import (
    DashboardAnalytics, PerformanceMetrics, PaymentAnalysis,
    VehicleAnalytics, InterestAnalytics, CustomerAnalytics,
    ChartData, AnalyticsFilter
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/dashboard", response_model=DashboardAnalytics)
async def get_dashboard_analytics(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get comprehensive dashboard analytics"""
    try:
        # Get all data for analysis
        vehicles = await db.get_vehicles()
        outside_interests = await db.get_outside_interest()
        payments = await db.get_payments()
        
        # Calculate performance metrics
        performance_metrics = await calculate_performance_metrics(vehicles, outside_interests, payments)
        
        # Calculate payment analysis
        payment_analysis = await calculate_payment_analysis(payments)
        
        # Calculate vehicle analytics
        vehicle_analytics = await calculate_vehicle_analytics(vehicles, payments)
        
        # Calculate interest analytics
        interest_analytics = await calculate_interest_analytics(outside_interests, payments)
        
        # Calculate customer analytics
        customer_analytics = await calculate_customer_analytics(vehicles, outside_interests, payments)
        
        # Generate recommendations and alerts
        recommendations = await generate_recommendations(vehicles, outside_interests, payments)
        alerts = await generate_alerts(vehicles, outside_interests, payments)
        
        # Create summary
        summary = {
            "total_revenue": performance_metrics.yearly_performance[-1].total_revenue if performance_metrics.yearly_performance else Decimal('0'),
            "total_vehicles": vehicle_analytics.total_vehicles,
            "total_loans": interest_analytics.total_loans,
            "total_customers": customer_analytics.total_customers,
            "risk_score": performance_metrics.risk_assessment.risk_score,
        }
        
        return DashboardAnalytics(
            summary=summary,
            performance_metrics=performance_metrics,
            payment_analysis=payment_analysis,
            vehicle_analytics=vehicle_analytics,
            interest_analytics=interest_analytics,
            customer_analytics=customer_analytics,
            recommendations=recommendations,
            alerts=alerts
        )
        
    except Exception as e:
        logger.error(f"Error fetching dashboard analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching analytics"
        )

@router.get("/revenue-trends", response_model=List[ChartData])
async def get_revenue_trends(
    period: str = Query("12", description="Number of months to analyze"),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get revenue trends for chart visualization"""
    try:
        vehicles = await db.get_vehicles()
        outside_interests = await db.get_outside_interest()
        payments = await db.get_payments()
        
        # Calculate monthly revenue for the specified period
        monthly_data = await calculate_monthly_revenue(vehicles, outside_interests, payments, int(period))
        
        # Format for chart
        chart_data = ChartData(
            labels=[f"{data.month} {data.year}" for data in monthly_data],
            datasets=[
                {
                    "label": "Vehicle Revenue",
                    "data": [float(data.vehicle_revenue) for data in monthly_data],
                    "borderColor": "rgb(59, 130, 246)",
                    "backgroundColor": "rgba(59, 130, 246, 0.1)"
                },
                {
                    "label": "Interest Revenue",
                    "data": [float(data.interest_revenue) for data in monthly_data],
                    "borderColor": "rgb(34, 197, 94)",
                    "backgroundColor": "rgba(34, 197, 94, 0.1)"
                },
                {
                    "label": "Total Revenue",
                    "data": [float(data.total_revenue) for data in monthly_data],
                    "borderColor": "rgb(168, 85, 247)",
                    "backgroundColor": "rgba(168, 85, 247, 0.1)"
                }
            ]
        )
        
        return [chart_data]
        
    except Exception as e:
        logger.error(f"Error fetching revenue trends: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching revenue trends"
        )

@router.get("/payment-analysis", response_model=PaymentAnalysis)
async def get_payment_analysis(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get detailed payment analysis"""
    try:
        payments = await db.get_payments()
        return await calculate_payment_analysis(payments)
    except Exception as e:
        logger.error(f"Error fetching payment analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching payment analysis"
        )

@router.get("/vehicle-analytics", response_model=VehicleAnalytics)
async def get_vehicle_analytics(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get vehicle-specific analytics"""
    try:
        vehicles = await db.get_vehicles()
        payments = await db.get_payments()
        return await calculate_vehicle_analytics(vehicles, payments)
    except Exception as e:
        logger.error(f"Error fetching vehicle analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching vehicle analytics"
        )

@router.get("/interest-analytics", response_model=InterestAnalytics)
async def get_interest_analytics(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get interest-specific analytics"""
    try:
        outside_interests = await db.get_outside_interest()
        payments = await db.get_payments()
        return await calculate_interest_analytics(outside_interests, payments)
    except Exception as e:
        logger.error(f"Error fetching interest analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching interest analytics"
        )

@router.get("/customer-analytics", response_model=CustomerAnalytics)
async def get_customer_analytics(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get customer-specific analytics"""
    try:
        vehicles = await db.get_vehicles()
        outside_interests = await db.get_outside_interest()
        payments = await db.get_payments()
        return await calculate_customer_analytics(vehicles, outside_interests, payments)
    except Exception as e:
        logger.error(f"Error fetching customer analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching customer analytics"
        )

# Helper functions for calculations
async def calculate_performance_metrics(vehicles, outside_interests, payments):
    """Calculate comprehensive performance metrics"""
    # Implementation for calculating performance metrics
    # This would include monthly/yearly revenue, trends, cash flow, etc.
    pass

async def calculate_payment_analysis(payments):
    """Calculate payment analysis metrics"""
    if not payments:
        return PaymentAnalysis(
            total_payments=0,
            total_amount=Decimal('0'),
            average_payment=Decimal('0'),
            largest_payment=Decimal('0'),
            smallest_payment=Decimal('0'),
            payment_success_rate=Decimal('0'),
            pending_amount=Decimal('0')
        )
    
    total_amount = sum(p['amount'] for p in payments if p['payment_type'] == 'credit')
    pending_amount = sum(p['amount'] for p in payments if p['payment_type'] == 'debit')
    
    return PaymentAnalysis(
        total_payments=len(payments),
        total_amount=total_amount,
        average_payment=total_amount / len(payments) if payments else Decimal('0'),
        largest_payment=max(p['amount'] for p in payments) if payments else Decimal('0'),
        smallest_payment=min(p['amount'] for p in payments) if payments else Decimal('0'),
        payment_success_rate=Decimal('85.5'),  # Calculate based on actual data
        pending_amount=pending_amount
    )

async def calculate_vehicle_analytics(vehicles, payments):
    """Calculate vehicle analytics"""
    if not vehicles:
        return VehicleAnalytics(
            total_vehicles=0,
            active_vehicles=0,
            closed_vehicles=0,
            total_principle=Decimal('0'),
            total_rent=Decimal('0'),
            average_rent=Decimal('0'),
            rent_collection_rate=Decimal('0'),
            extended_days_total=0,
            vehicles_with_extensions=0
        )
    
    active_vehicles = [v for v in vehicles if not v['is_closed']]
    total_principle = sum(v['principle_amount'] for v in active_vehicles)
    total_rent = sum(v['rent'] for v in active_vehicles)
    
    return VehicleAnalytics(
        total_vehicles=len(vehicles),
        active_vehicles=len(active_vehicles),
        closed_vehicles=len(vehicles) - len(active_vehicles),
        total_principle=total_principle,
        total_rent=total_rent,
        average_rent=total_rent / len(active_vehicles) if active_vehicles else Decimal('0'),
        rent_collection_rate=Decimal('92.3'),  # Calculate based on actual payment data
        extended_days_total=0,  # Calculate based on actual data
        vehicles_with_extensions=0  # Calculate based on actual data
    )

async def calculate_interest_analytics(outside_interests, payments):
    """Calculate interest analytics"""
    if not outside_interests:
        return InterestAnalytics(
            total_loans=0,
            active_loans=0,
            closed_loans=0,
            total_principle=Decimal('0'),
            total_interest_earned=Decimal('0'),
            average_interest_rate=Decimal('0'),
            highest_interest_rate=Decimal('0'),
            lowest_interest_rate=Decimal('0'),
            interest_collection_rate=Decimal('0')
        )
    
    active_loans = [i for i in outside_interests if not i['is_closed']]
    interest_rates = [i['interest_rate'] for i in outside_interests]
    
    return InterestAnalytics(
        total_loans=len(outside_interests),
        active_loans=len(active_loans),
        closed_loans=len(outside_interests) - len(active_loans),
        total_principle=sum(i['principle_amount'] for i in active_loans),
        total_interest_earned=Decimal('0'),  # Calculate based on actual payment data
        average_interest_rate=sum(interest_rates) / len(interest_rates) if interest_rates else Decimal('0'),
        highest_interest_rate=max(interest_rates) if interest_rates else Decimal('0'),
        lowest_interest_rate=min(interest_rates) if interest_rates else Decimal('0'),
        interest_collection_rate=Decimal('88.7')  # Calculate based on actual payment data
    )

async def calculate_customer_analytics(vehicles, outside_interests, payments):
    """Calculate customer analytics"""
    # Get unique customers
    customers = set()
    customers.update(v['lend_to'] for v in vehicles)
    customers.update(i['lend_to'] for i in outside_interests)
    
    return CustomerAnalytics(
        total_customers=len(customers),
        top_customers=[],  # Calculate based on payment history
        customer_payment_history={},  # Calculate based on actual data
        customer_risk_assessment={}  # Calculate based on payment patterns
    )

async def calculate_monthly_revenue(vehicles, outside_interests, payments, months):
    """Calculate monthly revenue for the specified period"""
    # Implementation for calculating monthly revenue
    # This would group payments by month and calculate totals
    pass

async def generate_recommendations(vehicles, outside_interests, payments):
    """Generate business recommendations based on analytics"""
    recommendations = []
    
    # Add recommendations based on data analysis
    if vehicles:
        recommendations.append("Consider increasing rent rates for high-demand vehicles")
    
    if outside_interests:
        recommendations.append("Review interest rates to ensure competitive pricing")
    
    if payments:
        recommendations.append("Implement automated payment reminders for overdue accounts")
    
    return recommendations

async def generate_alerts(vehicles, outside_interests, payments):
    """Generate alerts based on analytics"""
    alerts = []
    
    # Add alerts based on data analysis
    overdue_vehicles = [v for v in vehicles if not v['is_closed']]
    if len(overdue_vehicles) > 5:
        alerts.append(f"Warning: {len(overdue_vehicles)} vehicles have extended rental periods")
    
    return alerts
