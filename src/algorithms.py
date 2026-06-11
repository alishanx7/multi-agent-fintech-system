def calculate_dscr(net_operating_income, total_debt_service):
    if total_debt_service <= 0:
        return 999.0
    return round(net_operating_income / total_debt_service, 2)

def evaluate_financial_risk(net_operating_income, total_debt_service, monthly_revenue):
    dscr = calculate_dscr(net_operating_income, total_debt_service)
    if dscr >= 1.5 and monthly_revenue >= 10000:
        risk_tier = 'LOW RISK'
        rec = 'Approved for automatic priority processing line.'
    elif 1.15 <= dscr < 1.5:
        risk_tier = 'MEDIUM RISK'
        rec = 'Conditional approval: Forward to compliance agent lookup table.'
    else:
        risk_tier = 'HIGH RISK'
        rec = 'Requires manual human intervention checklist override.'
    return {
        'calculated_dscr': dscr,
        'monthly_revenue': round(monthly_revenue, 2),
        'risk_tier': risk_tier,
        'underwriter_recommendation': rec
    }
