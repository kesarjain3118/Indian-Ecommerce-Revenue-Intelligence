"""
RFM Analysis - Customer Segmentation
Calculates Recency, Frequency, Monetary scores and segments customers
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
print("RFM ANALYSIS - CUSTOMER SEGMENTATION")
print("=" * 60)

# Load data
print("\n1. Loading data...")
customers = pd.read_csv('data/customers.csv')
orders = pd.read_csv('data/orders.csv')
order_items = pd.read_csv('data/order_items.csv')

print(f"   ✓ Customers: {len(customers):,}")
print(f"   ✓ Orders: {len(orders):,}")
print(f"   ✓ Order Items: {len(order_items):,}")

# Convert dates
orders['order_date'] = pd.to_datetime(orders['order_date'])
customers['signup_date'] = pd.to_datetime(customers['signup_date'])

# Analysis date (use the most recent order date)
analysis_date = orders['order_date'].max()
print(f"\n   Analysis Date: {analysis_date.date()}")

# Calculate revenue per order
print("\n2. Calculating revenue per order...")
order_revenue = order_items.groupby('order_id')['revenue'].sum().reset_index()
orders_with_revenue = orders.merge(order_revenue, on='order_id', how='left')

# Filter only delivered orders for RFM
delivered_orders = orders_with_revenue[orders_with_revenue['order_status'] == 'Delivered'].copy()
print(f"   ✓ Delivered orders: {len(delivered_orders):,}")

# Calculate RFM metrics per customer
print("\n3. Calculating RFM metrics...")

rfm = delivered_orders.groupby('customer_id').agg({
    'order_date': lambda x: (analysis_date - x.max()).days,  # Recency
    'order_id': 'count',  # Frequency
    'revenue': 'sum'  # Monetary
}).reset_index()

rfm.columns = ['customer_id', 'recency', 'frequency', 'monetary']

print(f"\n   RFM Statistics:")
print(f"   ┌─────────────────────────────────────┐")
print(f"   │ Metric    │ Min    │ Max    │ Mean │")
print(f"   ├─────────────────────────────────────┤")
print(f"   │ Recency   │ {rfm['recency'].min():6.0f} │ {rfm['recency'].max():6.0f} │ {rfm['recency'].mean():5.0f} │")
print(f"   │ Frequency │ {rfm['frequency'].min():6.0f} │ {rfm['frequency'].max():6.0f} │ {rfm['frequency'].mean():5.1f} │")
print(f"   │ Monetary  │ {rfm['monetary'].min():6.0f} │ {rfm['monetary'].max():6.0f} │ {rfm['monetary'].mean():5.0f} │")
print(f"   └─────────────────────────────────────┘")

# Calculate RFM scores (1-5 scale using quintiles)
print("\n4. Calculating RFM scores (1-5 scale)...")

# Recency: Lower is better, so invert
rfm['R_score'] = pd.qcut(rfm['recency'], q=5, labels=[5, 4, 3, 2, 1], duplicates='drop')
# Frequency: Higher is better
rfm['F_score'] = pd.qcut(rfm['frequency'].rank(method='first'), q=5, labels=[1, 2, 3, 4, 5], duplicates='drop')
# Monetary: Higher is better
rfm['M_score'] = pd.qcut(rfm['monetary'].rank(method='first'), q=5, labels=[1, 2, 3, 4, 5], duplicates='drop')

# Convert to integer
rfm['R_score'] = rfm['R_score'].astype(int)
rfm['F_score'] = rfm['F_score'].astype(int)
rfm['M_score'] = rfm['M_score'].astype(int)

# Calculate RFM score (concatenated)
rfm['RFM_score'] = rfm['R_score'].astype(str) + rfm['F_score'].astype(str) + rfm['M_score'].astype(str)

# Calculate RFM total (sum for easier segmentation)
rfm['RFM_total'] = rfm['R_score'] + rfm['F_score'] + rfm['M_score']

print("   ✓ Scores calculated")

# Define customer segments based on RFM scores
print("\n5. Segmenting customers...")

def segment_customer(row):
    """Segment customers based on RFM scores"""
    r, f, m = row['R_score'], row['F_score'], row['M_score']
    
    # Champions: High R, F, M
    if r >= 4 and f >= 4 and m >= 4:
        return 'Champions'
    # Loyal Customers: High F
    elif f >= 4:
        return 'Loyal'
    # Potential Loyalist: Recent customers with average frequency
    elif r >= 4 and f >= 2 and f <= 3:
        return 'Potential Loyalist'
    # New Customers: High R, low F
    elif r >= 4 and f == 1:
        return 'New Customers'
    # Promising: Recent, moderate spending
    elif r >= 3 and m >= 3:
        return 'Promising'
    # Need Attention: Average on all
    elif r >= 2 and r <= 3:
        return 'Need Attention'
    # At Risk: Low R, but were good customers
    elif r <= 2 and f >= 3:
        return 'At Risk'
    # Cannot Lose Them: Low R, high M/F
    elif r <= 2 and m >= 4:
        return 'Cannot Lose'
    # Hibernating: Low R, F
    elif r <= 2 and f <= 2:
        return 'Hibernating'
    # Lost: Very low R
    elif r == 1:
        return 'Lost'
    else:
        return 'Others'

rfm['segment'] = rfm.apply(segment_customer, axis=1)

# Segment summary
segment_summary = rfm.groupby('segment').agg({
    'customer_id': 'count',
    'recency': 'mean',
    'frequency': 'mean',
    'monetary': 'sum'
}).round(2)
segment_summary.columns = ['count', 'avg_recency', 'avg_frequency', 'total_revenue']
segment_summary['pct_customers'] = (segment_summary['count'] / len(rfm) * 100).round(1)
segment_summary = segment_summary.sort_values('total_revenue', ascending=False)

print("\n   Customer Segments:")
print("   " + "=" * 80)
print(f"   {'Segment':<20} {'Count':>8} {'%':>6} {'Avg Recency':>12} {'Avg Freq':>10} {'Revenue':>15}")
print("   " + "-" * 80)
for idx, row in segment_summary.iterrows():
    print(f"   {idx:<20} {int(row['count']):>8} {row['pct_customers']:>5.1f}% "
          f"{row['avg_recency']:>11.0f}d {row['avg_frequency']:>9.1f} "
          f"₹{row['total_revenue']:>13,.0f}")
print("   " + "=" * 80)

# Save results
print("\n6. Saving results...")
rfm_output = rfm.copy()
rfm_output = rfm_output.merge(customers[['customer_id', 'city', 'state', 'acquisition_channel']], 
                                on='customer_id', how='left')
rfm_output.to_csv('outputs/rfm_segments.csv', index=False)
print(f"   ✓ Saved to outputs/rfm_segments.csv")

# Create visualizations
print("\n7. Creating visualizations...")

# 1. RFM Score Distribution
fig, axes = plt.subplots(1, 3, figsize=(15, 4))
fig.suptitle('RFM Score Distributions', fontsize=16, fontweight='bold', y=1.02)

axes[0].hist(rfm['R_score'], bins=5, edgecolor='black', alpha=0.7, color='#e74c3c')
axes[0].set_title('Recency Score', fontweight='bold')
axes[0].set_xlabel('Score (1=Old, 5=Recent)')
axes[0].set_ylabel('Number of Customers')
axes[0].grid(alpha=0.3)

axes[1].hist(rfm['F_score'], bins=5, edgecolor='black', alpha=0.7, color='#3498db')
axes[1].set_title('Frequency Score', fontweight='bold')
axes[1].set_xlabel('Score (1=Low, 5=High)')
axes[1].set_ylabel('Number of Customers')
axes[1].grid(alpha=0.3)

axes[2].hist(rfm['M_score'], bins=5, edgecolor='black', alpha=0.7, color='#2ecc71')
axes[2].set_title('Monetary Score', fontweight='bold')
axes[2].set_xlabel('Score (1=Low, 5=High)')
axes[2].set_ylabel('Number of Customers')
axes[2].grid(alpha=0.3)

plt.tight_layout()
plt.savefig('outputs/charts/rfm_distribution.png', dpi=300, bbox_inches='tight')
print("   ✓ rfm_distribution.png")
plt.close()

# 2. Customer Segments Pie Chart
fig, ax = plt.subplots(figsize=(12, 8))
colors = plt.cm.Set3(range(len(segment_summary)))

wedges, texts, autotexts = ax.pie(segment_summary['count'], 
                                    labels=segment_summary.index,
                                    autopct='%1.1f%%',
                                    colors=colors,
                                    startangle=90,
                                    textprops={'fontsize': 11})

for autotext in autotexts:
    autotext.set_color('white')
    autotext.set_fontweight('bold')

ax.set_title('Customer Segmentation Distribution', fontsize=16, fontweight='bold', pad=20)
plt.tight_layout()
plt.savefig('outputs/charts/rfm_segments.png', dpi=300, bbox_inches='tight')
print("   ✓ rfm_segments.png")
plt.close()

# 3. RFM Heatmap (R vs F, color by M average)
pivot_table = rfm.pivot_table(values='monetary', index='R_score', columns='F_score', aggfunc='mean')

fig, ax = plt.subplots(figsize=(10, 8))
sns.heatmap(pivot_table, annot=True, fmt='.0f', cmap='YlOrRd', 
            cbar_kws={'label': 'Average Monetary Value (₹)'},
            linewidths=0.5, ax=ax)
ax.set_title('RFM Heatmap: Average Monetary Value\n(Recency vs Frequency)', 
             fontsize=14, fontweight='bold', pad=15)
ax.set_xlabel('Frequency Score →', fontsize=12, fontweight='bold')
ax.set_ylabel('Recency Score →', fontsize=12, fontweight='bold')
plt.tight_layout()
plt.savefig('outputs/charts/rfm_heatmap.png', dpi=300, bbox_inches='tight')
print("   ✓ rfm_heatmap.png")
plt.close()

# 4. Segment Comparison
fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle('Customer Segment Analysis', fontsize=16, fontweight='bold', y=0.995)

# Count by segment
segment_summary_sorted = segment_summary.sort_values('count', ascending=True)
axes[0, 0].barh(range(len(segment_summary_sorted)), segment_summary_sorted['count'], 
                color='steelblue', edgecolor='black')
axes[0, 0].set_yticks(range(len(segment_summary_sorted)))
axes[0, 0].set_yticklabels(segment_summary_sorted.index)
axes[0, 0].set_xlabel('Number of Customers', fontweight='bold')
axes[0, 0].set_title('Customers per Segment', fontweight='bold')
axes[0, 0].grid(alpha=0.3, axis='x')

# Revenue by segment
segment_summary_sorted = segment_summary.sort_values('total_revenue', ascending=True)
axes[0, 1].barh(range(len(segment_summary_sorted)), segment_summary_sorted['total_revenue']/1e6, 
                color='green', edgecolor='black')
axes[0, 1].set_yticks(range(len(segment_summary_sorted)))
axes[0, 1].set_yticklabels(segment_summary_sorted.index)
axes[0, 1].set_xlabel('Total Revenue (₹ Millions)', fontweight='bold')
axes[0, 1].set_title('Revenue per Segment', fontweight='bold')
axes[0, 1].grid(alpha=0.3, axis='x')

# Average Recency by segment
segment_summary_sorted = segment_summary.sort_values('avg_recency', ascending=False)
axes[1, 0].barh(range(len(segment_summary_sorted)), segment_summary_sorted['avg_recency'], 
                color='coral', edgecolor='black')
axes[1, 0].set_yticks(range(len(segment_summary_sorted)))
axes[1, 0].set_yticklabels(segment_summary_sorted.index)
axes[1, 0].set_xlabel('Average Days Since Last Purchase', fontweight='bold')
axes[1, 0].set_title('Average Recency per Segment', fontweight='bold')
axes[1, 0].grid(alpha=0.3, axis='x')

# Average Frequency by segment
segment_summary_sorted = segment_summary.sort_values('avg_frequency', ascending=True)
axes[1, 1].barh(range(len(segment_summary_sorted)), segment_summary_sorted['avg_frequency'], 
                color='purple', edgecolor='black')
axes[1, 1].set_yticks(range(len(segment_summary_sorted)))
axes[1, 1].set_yticklabels(segment_summary_sorted.index)
axes[1, 1].set_xlabel('Average Number of Orders', fontweight='bold')
axes[1, 1].set_title('Average Frequency per Segment', fontweight='bold')
axes[1, 1].grid(alpha=0.3, axis='x')

plt.tight_layout()
plt.savefig('outputs/charts/rfm_segment_comparison.png', dpi=300, bbox_inches='tight')
print("   ✓ rfm_segment_comparison.png")
plt.close()

# Key Insights
print("\n" + "=" * 60)
print("KEY INSIGHTS")
print("=" * 60)

top_segment = segment_summary.iloc[0]
print(f"\n💎 TOP SEGMENT: {top_segment.name}")
print(f"   • {int(top_segment['count'])} customers ({top_segment['pct_customers']:.1f}%)")
print(f"   • Total Revenue: ₹{top_segment['total_revenue']:,.0f}")
print(f"   • Avg Recency: {top_segment['avg_recency']:.0f} days")
print(f"   • Avg Frequency: {top_segment['avg_frequency']:.1f} orders")

at_risk = rfm[rfm['segment'].isin(['At Risk', 'Cannot Lose', 'Hibernating'])]
print(f"\n⚠️  AT-RISK CUSTOMERS: {len(at_risk)} ({len(at_risk)/len(rfm)*100:.1f}%)")
print(f"   • Potential revenue to save: ₹{at_risk['monetary'].sum():,.0f}")

champions = rfm[rfm['segment'] == 'Champions']
if len(champions) > 0:
    print(f"\n🏆 CHAMPIONS: {len(champions)} customers")
    print(f"   • Total Revenue: ₹{champions['monetary'].sum():,.0f}")
    print(f"   • Average Order Value: ₹{(champions['monetary'] / champions['frequency']).mean():,.0f}")

print("\n" + "=" * 60)
print("✅ RFM ANALYSIS COMPLETE")
print("=" * 60)
print("\nOutputs saved:")
print("  📄 outputs/rfm_segments.csv")
print("  📊 outputs/charts/rfm_distribution.png")
print("  📊 outputs/charts/rfm_segments.png")
print("  📊 outputs/charts/rfm_heatmap.png")
print("  📊 outputs/charts/rfm_segment_comparison.png")
print("=" * 60)
