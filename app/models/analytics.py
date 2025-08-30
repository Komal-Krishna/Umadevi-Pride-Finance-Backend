from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import date, datetime
from decimal import Decimal

# Analytics Models for Financial Analysis

class MonthlyRevenue(BaseModel):
    month: str
    year: int
    vehicle_revenue: Decimal
    interest_revenue: Decimal
    total_revenue: Decimal
    payment_count: int

class YearlyRevenue(BaseModel):
    year: int
    total_revenue: Decimal
    vehicle_revenue: Decimal
    interest_revenue: Decimal
    growth_rate: Optional[Decimal]
    payment_count: int

class RevenueTrend(BaseModel):
    period: str
    revenue: Decimal
    change_percentage: Optional[Decimal]
    trend: str  # 'up', 'down', 'stable'

class PaymentAnalysis(BaseModel):
    total_payments: int
    total_amount: Decimal
    average_payment: Decimal
    largest_payment: Decimal
    smallest_payment: Decimal
    payment_success_rate: Decimal
    pending_amount: Decimal

class VehicleAnalytics(BaseModel):
    total_vehicles: int
    active_vehicles: int
    closed_vehicles: int
    total_principle: Decimal
    total_rent: Decimal
    average_rent: Decimal
    rent_collection_rate: Decimal
    extended_days_total: int
    vehicles_with_extensions: int

class InterestAnalytics(BaseModel):
    total_loans: int
    active_loans: int
    closed_loans: int
    total_principle: Decimal
    total_interest_earned: Decimal
    average_interest_rate: Decimal
    highest_interest_rate: Decimal
    lowest_interest_rate: Decimal
    interest_collection_rate: Decimal

class CustomerAnalytics(BaseModel):
    total_customers: int
    top_customers: List[Dict[str, Any]]
    customer_payment_history: Dict[str, Any]
    customer_risk_assessment: Dict[str, str]

class CashFlowAnalysis(BaseModel):
    period: str
    cash_in: Decimal
    cash_out: Decimal
    net_cash_flow: Decimal
    opening_balance: Decimal
    closing_balance: Decimal

class ProfitabilityMetrics(BaseModel):
    gross_profit_margin: Decimal
    net_profit_margin: Decimal
    return_on_investment: Decimal
    debt_to_equity_ratio: Decimal
    interest_coverage_ratio: Decimal

class RiskAnalysis(BaseModel):
    overdue_payments: int
    overdue_amount: Decimal
    risk_score: Decimal
    high_risk_customers: List[str]
    risk_factors: List[str]

class PerformanceMetrics(BaseModel):
    monthly_performance: List[MonthlyRevenue]
    yearly_performance: List[YearlyRevenue]
    revenue_trends: List[RevenueTrend]
    cash_flow: List[CashFlowAnalysis]
    profitability: ProfitabilityMetrics
    risk_assessment: RiskAnalysis

class DashboardAnalytics(BaseModel):
    summary: Dict[str, Any]
    performance_metrics: PerformanceMetrics
    payment_analysis: PaymentAnalysis
    vehicle_analytics: VehicleAnalytics
    interest_analytics: InterestAnalytics
    customer_analytics: CustomerAnalytics
    recommendations: List[str]
    alerts: List[str]

class ChartData(BaseModel):
    labels: List[str]
    datasets: List[Dict[str, Any]]

class AnalyticsFilter(BaseModel):
    start_date: Optional[date]
    end_date: Optional[date]
    source_type: Optional[str]
    customer_name: Optional[str]
    payment_status: Optional[str]
    group_by: str = 'month'  # month, quarter, year, customer
