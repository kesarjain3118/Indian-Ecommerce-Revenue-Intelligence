"""
Cohort Analysis - Customer Retention Tracking
Analyzes retention rates by monthly cohorts
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

print("=" * 60)
print("COHORT ANALYSIS - RETENTION TRACKING")
print("=" * 60)

# Load data
print("\n1. Loading data...")
customers = pd.read_csv('data/customers.csv')
orders = pd.read_csv('data/orders.csv')

# Convert dates
customers['signup_date'] = pd.to_datetime(customers['signup_date'])
orders['order_date'] = pd.to_datetime(orders['order_date'])

# Filter delivered orders only
delivered_orders = orders[orders['order_status'] == 'Delivered'].copy()

print(f"   ✓ Customers: {len(customers):,}")
print(f"   ✓ Delivered Orders: {len(delivered_orders):,}")

# Create cohort data
print("\n2. Creating cohort structure...")

# Get cohort month (signup month)
customers['cohort_month'] = customers['signup_date'].dt.to_period('M')

# Merge customers with orders
cohort_data = delivered_orders.merge(customers[['customer_id', 'cohort_month']], 
                                      on='customer_id', how='left')

# Get order month
cohort_data['order_month'] = cohort_data['order_date'].dt.to_period('M')

# Calculate cohort index (months since signup)
cohort_data['cohort_index'] = (cohort_data['order_month'] - cohort_data['cohort_month']).apply(lambda x: x.n)

print("   ✓ Cohort structure created")

# Build cohort table
print("\n3. Calculating retention rates...")

# Cohort counts
cohort_counts = cohort_data.groupby(['cohort_month', 'cohort_index'])['customer_id'].nunique().reset_index()
cohort_counts = cohort_counts.pivot(index='cohort_month', columns='cohort_index', values='customer_id')

# Get cohort sizes (month 0 = signup month)
cohort_sizes = cohort_counts.iloc[:, 0]

# Calculate retention rates
retention_rates = cohort_counts.divide(cohort_sizes, axis=0) * 100

# Fill NaN with 0
retention_rates = retention_rates.fillna(0)

print(f"\n   Cohort Summary:")
print(f"   • Total cohorts: {len(retention_rates)}")
print(f"   • Date range: {retention_rates.index[0]} to {retention_rates.index[-1]}")
print(f"   • Tracking period: {retention_rates.columns[-1]} months")

# Calculate average retention by month
avg_retention_by_month = retention_rates.mean(axis=0)

print(f"\n   Average Retention Rates:")
print(f"   ┌────────────────────────────┐")
print(f"   │ Month │ Retention Rate    │")
print(f"   ├────────────────────────────┤")
for idx in range(min(7, len(avg_retention_by_month))):
    print(f"   │  {idx:2d}   │     {avg_retention_by_month.iloc[idx]:5.1f}%       │")
print(f"   └────────────────────────────┘")

# Save results
print("\n4. Saving results...")

# Prepare output
retention_output = retention_rates.reset_index()
retention_output['cohort_month'] = retention_output['cohort_month'].astype(str)
retention_output.to_csv('outputs/cohort_retention.csv', index=False)

# Also save cohort sizes
cohort_summary = pd.DataFrame({
    'cohort_month': cohort_sizes.index.astype(str),
    'cohort_size': cohort_sizes.values,
    'month_1_retention': retention_rates.get(1, 0),
    'month_3_retention': retention_rates.get(3, 0) if 3 in retention_rates.columns else 0,
    'month_6_retention': retention_rates.get(6, 0) if 6 in retention_rates.columns else 0
})
cohort_summary.to_csv('outputs/cohort_summary.csv', index=False)

print("   ✓ Saved to outputs/cohort_retention.csv")
print("   ✓ Saved to outputs/cohort_summary.csv")

# Create visualizations
print("\n5. Creating visualizations...")

# 1. Retention Heatmap
fig, ax = plt.subplots(figsize=(14, 10))

# Limit to last 18 cohorts for readability
display_cohorts = retention_rates.iloc[-18:, :13]  # Last 18 cohorts, first 13 months

sns.heatmap(display_cohorts, annot=True, fmt='.0f', cmap='RdYlGn', 
            vmin=0, vmax=100, center=50,
            cbar_kws={'label': 'Retention Rate (%)'},
            linewidths=0.5, ax=ax)

ax.set_title('Cohort Retention Heatmap\n(% of customers who made a purchase)', 
             fontsize=14, fontweight='bold', pad=15)
ax.set_xlabel('Months Since Signup', fontsize=12, fontweight='bold')
ax.set_ylabel('Cohort (Signup Month)', fontsize=12, fontweight='bold')

# Format y-axis labels
yticklabels = [str(label) for label in display_cohorts.index]
ax.set_yticklabels(yticklabels, rotation=0)

plt.tight_layout()
plt.savefig('outputs/charts/cohort_heatmap.png', dpi=300, bbox_inches='tight')
print("   ✓ cohort_heatmap.png")
plt.close()

# 2. Retention Curves
fig, ax = plt.subplots(figsize=(12, 7))

# Plot retention curves for selected cohorts
cohorts_to_plot = retention_rates.iloc[-12:] if len(retention_rates) >= 12 else retention_rates

for idx, cohort in cohorts_to_plot.iterrows():
    ax.plot(cohort.index, cohort.values, marker='o', label=str(idx), alpha=0.7)

ax.set_title('Retention Curves by Cohort', fontsize=14, fontweight='bold')
ax.set_xlabel('Months Since Signup', fontsize=12, fontweight='bold')
ax.set_ylabel('Retention Rate (%)', fontsize=12, fontweight='bold')
ax.legend(title='Cohort Month', bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
ax.grid(alpha=0.3)
ax.set_ylim(0, 105)

plt.tight_layout()
plt.savefig('outputs/charts/cohort_curves.png', dpi=300, bbox_inches='tight')
print("   ✓ cohort_curves.png")
plt.close()

# 3. Cohort Sizes
fig, ax = plt.subplots(figsize=(14, 6))

cohort_sizes_df = pd.DataFrame({
    'month': cohort_sizes.index.astype(str),
    'size': cohort_sizes.values
})

# Plot last 24 cohorts
display_size = cohort_sizes_df.iloc[-24:] if len(cohort_sizes_df) >= 24 else cohort_sizes_df

ax.bar(range(len(display_size)), display_size['size'], color='steelblue', edgecolor='black')
ax.set_xticks(range(len(display_size)))
ax.set_xticklabels(display_size['month'], rotation=45, ha='right')
ax.set_title('Cohort Sizes by Month', fontsize=14, fontweight='bold')
ax.set_xlabel('Cohort Month', fontsize=12, fontweight='bold')
ax.set_ylabel('Number of New Customers', fontsize=12, fontweight='bold')
ax.grid(alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig('outputs/charts/cohort_sizes.png', dpi=300, bbox_inches='tight')
print("   ✓ cohort_sizes.png")
plt.close()

# 4. Average Retention Trend
fig, ax = plt.subplots(figsize=(12, 7))

months = avg_retention_by_month.index
values = avg_retention_by_month.values

ax.plot(months, values, marker='o', linewidth=2.5, markersize=8, color='darkgreen')
ax.fill_between(months, 0, values, alpha=0.3, color='green')

ax.set_title('Average Retention Rate by Month After Signup', fontsize=14, fontweight='bold')
ax.set_xlabel('Months Since Signup', fontsize=12, fontweight='bold')
ax.set_ylabel('Average Retention Rate (%)', fontsize=12, fontweight='bold')
ax.grid(alpha=0.3)
ax.set_ylim(0, 105)

# Add value labels
for i, (month, value) in enumerate(zip(months[:10], values[:10])):
    ax.text(month, value + 2, f'{value:.1f}%', ha='center', fontsize=9)

plt.tight_layout()
plt.savefig('outputs/charts/cohort_avg_retention.png', dpi=300, bbox_inches='tight')
print("   ✓ cohort_avg_retention.png")
plt.close()

# Key Insights
print("\n" + "=" * 60)
print("KEY INSIGHTS")
print("=" * 60)

# Month 1 retention
month_1_avg = avg_retention_by_month.iloc[1] if len(avg_retention_by_month) > 1 else 0
print(f"\n📊 MONTH 1 RETENTION: {month_1_avg:.1f}%")
print(f"   • {month_1_avg:.1f}% of customers make a second purchase")

# Month 3 retention
if len(avg_retention_by_month) > 3:
    month_3_avg = avg_retention_by_month.iloc[3]
    print(f"\n📊 MONTH 3 RETENTION: {month_3_avg:.1f}%")

# Month 6 retention
if len(avg_retention_by_month) > 6:
    month_6_avg = avg_retention_by_month.iloc[6]
    print(f"\n📊 MONTH 6 RETENTION: {month_6_avg:.1f}%")

# Best cohort
best_cohort_idx = cohort_sizes.idxmax()
best_cohort_size = cohort_sizes.max()
print(f"\n🏆 LARGEST COHORT: {best_cohort_idx}")
print(f"   • {int(best_cohort_size)} new customers")

# Recent cohort performance
recent_cohorts = retention_rates.iloc[-3:]
if len(recent_cohorts) > 0:
    recent_month_1 = recent_cohorts[1].mean() if 1 in recent_cohorts.columns else 0
    print(f"\n📈 RECENT COHORTS (Last 3 months)")
    print(f"   • Average Month-1 retention: {recent_month_1:.1f}%")

print("\n" + "=" * 60)
print("✅ COHORT ANALYSIS COMPLETE")
print("=" * 60)
print("\nOutputs saved:")
print("  📄 outputs/cohort_retention.csv")
print("  📄 outputs/cohort_summary.csv")
print("  📊 outputs/charts/cohort_heatmap.png")
print("  📊 outputs/charts/cohort_curves.png")
print("  📊 outputs/charts/cohort_sizes.png")
print("  📊 outputs/charts/cohort_avg_retention.png")
print("=" * 60)
