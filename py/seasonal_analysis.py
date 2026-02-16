"""
Seasonal Analysis - Identifying Trends and Patterns
Analyzes revenue and order patterns by time period
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

plt.style.use('seaborn-v0_8-darkgrid')

print("=" * 60)
print("SEASONAL ANALYSIS - TRENDS & PATTERNS")
print("=" * 60)

# Load data
print("\n1. Loading data...")
orders = pd.read_csv('data/orders.csv')
order_items = pd.read_csv('data/order_items.csv')

orders['order_date'] = pd.to_datetime(orders['order_date'])

# Calculate revenue
order_revenue = order_items.groupby('order_id')['revenue'].sum().reset_index()
orders_with_revenue = orders.merge(order_revenue, on='order_id', how='left')
delivered = orders_with_revenue[orders_with_revenue['order_status'] == 'Delivered'].copy()

# Extract time features
delivered['year'] = delivered['order_date'].dt.year
delivered['month'] = delivered['order_date'].dt.month
delivered['year_month'] = delivered['order_date'].dt.to_period('M')
delivered['day_of_week'] = delivered['order_date'].dt.day_name()
delivered['quarter'] = delivered['order_date'].dt.quarter

print(f"   ✓ Delivered Orders: {len(delivered):,}")
print(f"   • Date Range: {delivered['order_date'].min().date()} to {delivered['order_date'].max().date()}")

# Monthly analysis
print("\n2. Analyzing monthly trends...")
monthly = delivered.groupby('year_month').agg({
    'order_id': 'count',
    'revenue': 'sum'
}).reset_index()
monthly.columns = ['month', 'orders', 'revenue']
monthly['month_str'] = monthly['month'].astype(str)

print(f"\n   Monthly Revenue (Last 12 months):")
print("   " + "-" * 60)
for idx, row in monthly.tail(12).iterrows():
    print(f"   {row['month']}: {int(row['orders']):4d} orders, ₹{row['revenue']:10,.0f}")
print("   " + "-" * 60)

# Year-over-year comparison
yearly = delivered.groupby('year').agg({
    'order_id': 'count',
    'revenue': 'sum'
}).reset_index()
yearly.columns = ['year', 'orders', 'total_revenue']
yearly['avg_order_value'] = yearly['total_revenue'] / yearly['orders']

print(f"\n   Year-over-Year Comparison:")
print("   " + "-" * 60)
for idx, row in yearly.iterrows():
    print(f"   {int(row['year'])}: {int(row['orders']):,} orders, ₹{row['total_revenue']:,.0f} revenue")
print("   " + "-" * 60)

# Day of week analysis
print("\n3. Analyzing day-of-week patterns...")
day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
dow = delivered.groupby('day_of_week').agg({
    'order_id': 'count',
    'revenue': 'sum'
}).reindex(day_order)
dow['avg_order_value'] = dow['revenue'] / dow['order_id']

print(f"\n   Orders by Day of Week:")
print("   " + "-" * 60)
for day, row in dow.iterrows():
    print(f"   {day:10s}: {int(row['order_id']):4d} orders ({row['order_id']/len(delivered)*100:4.1f}%)")
print("   " + "-" * 60)

# Save results
print("\n4. Saving results...")
seasonal_output = pd.DataFrame({
    'period_type': ['monthly'] * len(monthly) + ['yearly'] * len(yearly) + ['day_of_week'] * len(dow),
    'period': list(monthly['month_str']) + [str(y) for y in yearly['year']] + list(dow.index),
    'orders': list(monthly['orders']) + list(yearly['orders']) + list(dow['order_id']),
    'revenue': list(monthly['revenue']) + list(yearly['total_revenue']) + list(dow['revenue'])
})
seasonal_output.to_csv('outputs/seasonal_trends.csv', index=False)
print("   ✓ Saved to outputs/seasonal_trends.csv")

# Visualizations
print("\n5. Creating visualizations...")

# 1. Monthly Revenue Trend
fig, axes = plt.subplots(2, 1, figsize=(14, 10))

axes[0].plot(range(len(monthly)), monthly['revenue']/1e6, marker='o', linewidth=2, markersize=6, color='darkblue')
axes[0].fill_between(range(len(monthly)), 0, monthly['revenue']/1e6, alpha=0.3, color='blue')
axes[0].set_xticks(range(len(monthly)))
axes[0].set_xticklabels(monthly['month_str'], rotation=45, ha='right')
axes[0].set_title('Monthly Revenue Trend', fontsize=14, fontweight='bold')
axes[0].set_ylabel('Revenue (₹ Millions)', fontweight='bold')
axes[0].grid(alpha=0.3)

axes[1].bar(range(len(monthly)), monthly['orders'], color='steelblue', edgecolor='black')
axes[1].set_xticks(range(len(monthly)))
axes[1].set_xticklabels(monthly['month_str'], rotation=45, ha='right')
axes[1].set_title('Monthly Order Count', fontsize=14, fontweight='bold')
axes[1].set_ylabel('Number of Orders', fontweight='bold')
axes[1].grid(alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig('outputs/charts/seasonal_monthly.png', dpi=300, bbox_inches='tight')
print("   ✓ seasonal_monthly.png")
plt.close()

# 2. Day of Week Heatmap
fig, ax = plt.subplots(figsize=(10, 6))

day_data = dow[['order_id']].T
sns.heatmap(day_data, annot=True, fmt='.0f', cmap='Blues', cbar_kws={'label': 'Orders'}, linewidths=1)
ax.set_title('Orders by Day of Week', fontsize=14, fontweight='bold')
ax.set_ylabel('')
ax.set_xlabel('')

plt.tight_layout()
plt.savefig('outputs/charts/seasonal_day_of_week.png', dpi=300, bbox_inches='tight')
print("   ✓ seasonal_day_of_week.png")
plt.close()

# 3. Year-over-Year Comparison
fig, ax = plt.subplots(figsize=(10, 7))

x = np.arange(len(yearly))
width = 0.35

ax.bar(x - width/2, yearly['orders'], width, label='Orders', color='steelblue', edgecolor='black')
ax2 = ax.twinx()
ax2.bar(x + width/2, yearly['total_revenue']/1e6, width, label='Revenue (₹M)', color='green', edgecolor='black')

ax.set_xlabel('Year', fontweight='bold')
ax.set_ylabel('Number of Orders', fontweight='bold', color='steelblue')
ax2.set_ylabel('Revenue (₹ Millions)', fontweight='bold', color='green')
ax.set_title('Year-over-Year Comparison', fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(yearly['year'].astype(int))
ax.tick_params(axis='y', labelcolor='steelblue')
ax2.tick_params(axis='y', labelcolor='green')
ax.legend(loc='upper left')
ax2.legend(loc='upper right')
ax.grid(alpha=0.3)

plt.tight_layout()
plt.savefig('outputs/charts/seasonal_yoy.png', dpi=300, bbox_inches='tight')
print("   ✓ seasonal_yoy.png")
plt.close()

# Key Insights
print("\n" + "=" * 60)
print("KEY INSIGHTS")
print("=" * 60)

# Growth
if len(yearly) > 1:
    growth = (yearly.iloc[-1]['total_revenue'] - yearly.iloc[0]['total_revenue']) / yearly.iloc[0]['total_revenue'] * 100
    print(f"\n📈 REVENUE GROWTH:")
    print(f"   • {yearly.iloc[0]['year']:.0f} to {yearly.iloc[-1]['year']:.0f}: {growth:+.1f}%")

# Peak month
peak_month = monthly.loc[monthly['revenue'].idxmax()]
print(f"\n🏆 PEAK MONTH: {peak_month['month']}")
print(f"   • Revenue: ₹{peak_month['revenue']:,.0f}")
print(f"   • Orders: {int(peak_month['orders'])}")

# Best day
best_day = dow['order_id'].idxmax()
print(f"\n📅 BUSIEST DAY: {best_day}")
print(f"   • {int(dow.loc[best_day, 'order_id'])} orders ({dow.loc[best_day, 'order_id']/len(delivered)*100:.1f}%)")

# Recent trend
recent_3_months = monthly.tail(3)['revenue'].mean()
print(f"\n📊 RECENT TREND (Last 3 Months):")
print(f"   • Average monthly revenue: ₹{recent_3_months:,.0f}")

print("\n" + "=" * 60)
print("✅ SEASONAL ANALYSIS COMPLETE")
print("=" * 60)
print("\nOutputs saved:")
print("  📄 outputs/seasonal_trends.csv")
print("  📊 outputs/charts/seasonal_monthly.png")
print("  📊 outputs/charts/seasonal_day_of_week.png")
print("  📊 outputs/charts/seasonal_yoy.png")
print("=" * 60)
