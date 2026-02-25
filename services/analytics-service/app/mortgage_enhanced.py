# MORTGAGE READINESS ENHANCED - Integration with Invoice Service

# This file contains the enhanced mortgage readiness report that integrates
# invoice data to provide a more comprehensive income picture for self-employed

from typing import Optional, Dict, Any
from datetime import datetime, date, timedelta
from decimal import Decimal
import httpx
from fastapi import HTTPException

class MortgageReadinessEnhanced:
    """Enhanced mortgage readiness report with invoice integration"""
    
    def __init__(self, auth_token: str):
        self.auth_token = auth_token
        self.transactions_service_url = "http://transactions-service:80"
        self.invoice_service_url = "http://invoice-service:80"
    
    async def get_comprehensive_income_report(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive income data from both transactions and invoices"""
        
        # Get transaction-based income
        transaction_income = await self._get_transaction_income(user_id)
        
        # Get invoice-based income for self-employed
        invoice_income = await self._get_invoice_income(user_id)
        
        # Combine and analyze
        return self._combine_income_sources(transaction_income, invoice_income)
    
    async def _get_transaction_income(self, user_id: str) -> Dict[str, Any]:
        """Get traditional transaction-based income"""
        try:
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {self.auth_token}"}
                response = await client.get(
                    f"{self.transactions_service_url}/transactions",
                    headers=headers,
                    timeout=10.0
                )
                response.raise_for_status()
                transactions = response.json()
                
                # Analyze income transactions
                twelve_months_ago = date.today() - timedelta(days=365)
                monthly_income = {}
                total_income = 0
                
                for t in transactions:
                    if t.get('amount', 0) > 0 and t.get('type') == 'income':
                        transaction_date = datetime.fromisoformat(t['date']).date()
                        if transaction_date >= twelve_months_ago:
                            month = transaction_date.strftime("%Y-%m")
                            if month not in monthly_income:
                                monthly_income[month] = 0
                            monthly_income[month] += t['amount']
                            total_income += t['amount']
                
                return {
                    'source': 'transactions',
                    'monthly_income': monthly_income,
                    'total_income': total_income,
                    'average_monthly': total_income / 12 if total_income > 0 else 0
                }
        except Exception as e:
            return {'source': 'transactions', 'error': str(e), 'monthly_income': {}, 'total_income': 0}
    
    async def _get_invoice_income(self, user_id: str) -> Dict[str, Any]:
        """Get invoice-based income for self-employed users"""
        try:
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {self.auth_token}"}
                
                # Get invoice summary for last 12 months
                twelve_months_ago = date.today() - timedelta(days=365)
                response = await client.get(
                    f"{self.invoice_service_url}/reports/summary",
                    headers=headers,
                    params={
                        'start_date': twelve_months_ago.isoformat(),
                        'end_date': date.today().isoformat()
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    summary = response.json()
                    
                    # Get detailed invoices
                    invoices_response = await client.get(
                        f"{self.invoice_service_url}/invoices",
                        headers=headers,
                        params={
                            'start_date': twelve_months_ago.isoformat(),
                            'end_date': date.today().isoformat(),
                            'limit': 1000
                        },
                        timeout=10.0
                    )
                    
                    invoices = invoices_response.json() if invoices_response.status_code == 200 else []
                    
                    # Analyze invoice income by month
                    monthly_invoice_income = {}
                    total_invoice_income = 0
                    invoice_count = 0
                    
                    for invoice in invoices:
                        if invoice.get('status') in ['paid', 'partially_paid', 'sent']:
                            invoice_date = datetime.fromisoformat(invoice['invoice_date']).date()
                            month = invoice_date.strftime("%Y-%m")
                            amount = float(invoice.get('total_amount', 0))
                            
                            if month not in monthly_invoice_income:
                                monthly_invoice_income[month] = 0
                            monthly_invoice_income[month] += amount
                            total_invoice_income += amount
                            invoice_count += 1
                    
                    return {
                        'source': 'invoices',
                        'monthly_income': monthly_invoice_income,
                        'total_income': total_invoice_income,
                        'average_monthly': total_invoice_income / 12 if total_invoice_income > 0 else 0,
                        'invoice_count': invoice_count,
                        'average_invoice_value': total_invoice_income / invoice_count if invoice_count > 0 else 0,
                        'professional_details': {
                            'total_billed': summary.get('total_billed', 0),
                            'total_collected': summary.get('total_collected', 0),
                            'outstanding_amount': summary.get('outstanding_amount', 0)
                        }
                    }
                else:
                    return {'source': 'invoices', 'monthly_income': {}, 'total_income': 0, 'invoice_count': 0}
                
        except Exception as e:
            return {'source': 'invoices', 'error': str(e), 'monthly_income': {}, 'total_income': 0}
    
    def _combine_income_sources(self, transaction_income: Dict, invoice_income: Dict) -> Dict[str, Any]:
        """Combine transaction and invoice income for comprehensive view"""
        
        # Merge monthly data
        combined_monthly = {}
        all_months = set(transaction_income.get('monthly_income', {}).keys()) | \
                     set(invoice_income.get('monthly_income', {}).keys())
        
        for month in all_months:
            transaction_amount = transaction_income.get('monthly_income', {}).get(month, 0)
            invoice_amount = invoice_income.get('monthly_income', {}).get(month, 0)
            
            combined_monthly[month] = {
                'transaction_income': transaction_amount,
                'invoice_income': invoice_amount,
                'total_income': transaction_amount + invoice_amount
            }
        
        total_combined_income = transaction_income.get('total_income', 0) + invoice_income.get('total_income', 0)
        average_monthly_combined = total_combined_income / 12 if total_combined_income > 0 else 0
        
        # Professional credentials for self-employed
        is_self_employed = invoice_income.get('invoice_count', 0) > 0
        
        return {
            'period': '12 months',
            'is_self_employed': is_self_employed,
            'combined_income': {
                'monthly_breakdown': combined_monthly,
                'total_income': total_combined_income,
                'average_monthly': average_monthly_combined
            },
            'income_sources': {
                'traditional_income': {
                    'total': transaction_income.get('total_income', 0),
                    'monthly_average': transaction_income.get('average_monthly', 0)
                },
                'professional_income': {
                    'total': invoice_income.get('total_income', 0),
                    'monthly_average': invoice_income.get('average_monthly', 0),
                    'invoice_count': invoice_income.get('invoice_count', 0),
                    'average_invoice_value': invoice_income.get('average_invoice_value', 0)
                }
            },
            'mortgage_readiness_score': self._calculate_mortgage_readiness_score(
                total_combined_income, 
                is_self_employed, 
                invoice_income
            ),
            'recommendations': self._generate_mortgage_recommendations(
                total_combined_income, 
                is_self_employed, 
                invoice_income
            )
        }
    
    def _calculate_mortgage_readiness_score(self, total_income: float, is_self_employed: bool, invoice_data: Dict) -> Dict[str, Any]:
        """Calculate mortgage readiness score based on income stability"""
        
        base_score = 0
        factors = []
        
        # Income level scoring
        if total_income >= 50000:  # £50k+
            base_score += 30
            factors.append("Strong annual income (£50k+)")
        elif total_income >= 30000:  # £30k+
            base_score += 20
            factors.append("Good annual income (£30k+)")
        elif total_income >= 18000:  # £18k+
            base_score += 10
            factors.append("Moderate income (£18k+)")
        
        # Consistency scoring for self-employed
        if is_self_employed:
            invoice_count = invoice_data.get('invoice_count', 0)
            if invoice_count >= 24:  # 2+ invoices per month
                base_score += 25
                factors.append("Consistent professional invoicing (2+ per month)")
            elif invoice_count >= 12:  # 1+ invoice per month
                base_score += 15
                factors.append("Regular professional invoicing")
            elif invoice_count >= 6:
                base_score += 5
                factors.append("Some professional invoicing history")
            
            # Professional income stability
            professional_income = invoice_data.get('total_income', 0)
            if professional_income > total_income * 0.8:  # 80%+ from invoices
                base_score += 20
                factors.append("Strong self-employed income documentation")
            elif professional_income > total_income * 0.5:  # 50%+ from invoices
                base_score += 10
                factors.append("Good self-employed income documentation")
        else:
            base_score += 15
            factors.append("Traditional employment income")
        
        # Outstanding invoices consideration
        if is_self_employed:
            outstanding = invoice_data.get('professional_details', {}).get('outstanding_amount', 0)
            if outstanding > 5000:
                base_score -= 5
                factors.append("High outstanding invoices may affect cashflow")
        
        # Cap the score at 100
        final_score = min(base_score, 100)
        
        if final_score >= 80:
            rating = "Excellent"
        elif final_score >= 60:
            rating = "Good"
        elif final_score >= 40:
            rating = "Fair"
        else:
            rating = "Needs Improvement"
        
        return {
            'score': final_score,
            'rating': rating,
            'factors': factors
        }
    
    def _generate_mortgage_recommendations(self, total_income: float, is_self_employed: bool, invoice_data: Dict) -> List[str]:
        """Generate personalized mortgage application recommendations"""
        
        recommendations = []
        
        if is_self_employed:
            recommendations.extend([
                "✅ Generate comprehensive invoice history report for mortgage application",
                "📊 Include 12-24 months of professional invoicing records",
                "💼 Highlight consistent client relationships and recurring income"
            ])
            
            if invoice_data.get('invoice_count', 0) < 12:
                recommendations.append("⚠️ Consider building more consistent invoicing history (aim for 12+ invoices per year)")
            
            outstanding = invoice_data.get('professional_details', {}).get('outstanding_amount', 0)
            if outstanding > 3000:
                recommendations.append("⚠️ Follow up on outstanding invoices to improve cash flow position")
        
        if total_income < 30000:
            recommendations.append("💡 Consider increasing income or reducing expenses before mortgage application")
        
        recommendations.extend([
            "📋 Prepare SA302 tax calculation from HMRC",
            "🏦 Maintain 3-6 months of business/personal bank statements",
            "📝 Consider working with mortgage broker experienced with self-employed clients",
            "💰 Aim to build deposit of 10-25% of property value"
        ])
        
        return recommendations