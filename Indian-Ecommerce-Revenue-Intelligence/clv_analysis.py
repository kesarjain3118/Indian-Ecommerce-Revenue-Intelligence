"""
Customer Lifetime Value (CLV) Analysis
Calculates historical and predictive CLV for each customer
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

print("=" * 60)
print("CUSTOMER LIFETIME VALUE (CLV) ANALYSIS")
print("=" * 60)

# Load data
print("\n1. Loading data...")
customers = pd.read_csv('data/customers.csv')
orders = pd.read_csv('data/orders.csv')
order_items = pd.read_csv('data/order_items.csv')

# Convert dates
customers['signup_date'] = pd.to_datetime(customers['signup_date'])
orders['order_date'] = pd.to_datetime(orders['order_date'])

# Calculate revenue per order
order_revenue = order_items.groupby('order_id')['revenue'].sum().reset_index()
orders_with_revenue = orders.merge(order_revenue, on='order_id', how='left')

# Filter delivered orders
delivered_orders = orders_with_revenue[orders_with_revenue['order_status'] == 'Delivered'].copy()

print(f"   ✓ Customers: {len(customers):,}")
print(f"   ✓ Delivered Orders: {len(delivered_orders):,}")

# Calculate CLV metrics per customer
print("\n2. Calculating CLV metrics...")

clv = delivered_orders.groupby('customer_id').agg({
    'revenue': ['sum', 'mean', 'count'],
    'order_date': ['min', 'max']
}).reset_index()

clv.columns = ['customer_id', 'total_revenue', 'avg_order_value', 'order_count', 'first_order', 'last_order']

# Calculate customer lifetime (days)
clv['customer_lifetime_days'] = (clv['last_order'] - clv['first_order']).dt.days + 1

# Merge with customer demographics
clv = clv.merge(customers[['customer_id', 'signup_date', 'state', 'acquisition_channel', 'age', 'gender']], 
                on='customer_id', how='left')

# Calculate CLV (use total revenue as historical CLV)
clv['historical_clv'] = clv['total_revenue']

# Calculate purchase frequency (orders per month)
clv['purchase_frequency'] = clv['order_count'] / (clv['customer_lifetime_days'] / 30 + 1)

print(f"\n   CLV Statistics:")
print(f"   ┌─────────────────────────────────────────┐")
print(f"   │ Metric       │ Min     │ Max      │ Mean  │")
print(f"   ├─────────────────────────────────────────┤")
print(f"   │ CLV          │ ₹{clv['historical_clv'].min():6.0f}  │ ₹{clv['historical_clv'].max():7.0f} │ ₹{clv['historical_clv'].mean():6.0f}│")
print(f"   │ Orders       │ {clv['order_count'].min():6.0f}  │ {clv['order_count'].max():7.0f} │ {clv['order_count'].mean():6.1f}│")
print(f"   │ AOV          │ ₹{clv['avg_order_value'].min():6.0f}  │ ₹{clv['avg_order_value'].max():7.0f} │ ₹{clv['avg_order_value'].mean():6.0f}│")
print(f"   └─────────────────────────────────────────┘")

# Segment customers by CLV
print("\n3. Segmenting customers by CLV...")

# Create CLV quintiles
clv['clv_segment'] = pd.qcut(clv['historical_clv'], q=5, labels=['Very Low', 'Low', 'Medium', 'High', 'Very High'], duplicates='drop')

segment_summary = clv.groupby('clv_segment').agg({
    'customer_id': 'count',
    'historical_clv': ['sum', 'mean'],
    'order_count': 'mean',
    'avg_order_value': 'mean'
}).round(0)

segment_summary.columns = ['customers', 'total_revenue', 'avg_clv', 'avg_orders', 'avg_order_value']

print("\n   CLV Segments:")
print("   " + "=" * 80)
for idx, row in segment_summary.iterrows():
    pct = row['customers'] / len(clv) * 100
    print(f"   {idx:11s}: {int(row['customers']):4d} customers ({pct:4.1f}%) - "
          f"Total: ₹{row['total_revenue']:10,.0f} - Avg CLV: ₹{row['avg_clv']:7,.0f}")
print("   " + "=" * 80)

# Top customers by CLV
top_customers = clv.nlargest(20, 'historical_clv')[['customer_id', 'historical_clv', 'order_count', 'avg_order_value', 'state', 'acquisition_channel']]

print("\n   🏆 Top 10 Customers by CLV:")
print("   " + "-" * 80)
for idx, row in top_customers.head(10).iterrows():
    print(f"   {row['customer_id']}: ₹{row['historical_clv']:9,.0f} ({int(row['order_count'])} orders, {row['state']})")
print("   " + "-" * 80)

# CLV by acquisition channel
channel_clv = clv.groupby('acquisition_channel').agg({
    'customer_id': 'count',
    'historical_clv': ['sum', 'mean']
}).round(0)
channel_clv.columns = ['customers', 'total_revenue', 'avg_clv']
channel_clv = channel_clv.sort_values('avg_clv', ascending=False)

print("\n   📊 CLV by Acquisition Channel:")
print("   " + "-" * 80)
for idx, row in channel_clv.iterrows():
    print(f"   {idx:15s}: {int(row['customers']):4d} customers - Avg CLV: ₹{row['avg_clv']:7,.0f}")
print("   " + "-" * 80)

# Save results
print("\n4. Saving results...")
clv.to_csv('outputs/clv_scores.csv', index=False)
print("   ✓ Saved to outputs/clv_scores.csv")

# Create visualizations
print("\n5. Creating visualizations...")

# 1. CLV Distribution
fig, axes = plt.subplots(1, 2, figsize=(15, 5))
fig.suptitle('Customer Lifetime Value Distribution', fontsize=16, fontweight='bold')

# Histogram
axes[0].hist(clv['historical_clv']/1000, bins=50, edgecolor='black', alpha=0.7, color='green')
axes[0].set_title('CLV Distribution', fontweight='bold')
axes[0].set_xlabel('CLV (₹ Thousands)')
axes[0].set_ylabel('Number of Customers')
axes[0].grid(alpha=0.3)

# Box plot by segment
clv.boxplot(column='historical_clv', by='clv_segment', ax=axes[1])
axes[1].set_title('CLV by Segment', fontweight='bold')
axes[1].set_xlabel('CLV Segment')
axes[1].set_ylabel('CLV (₹)')
axes[1].get_figure().suptitle('')  # Remove auto title
plt.suptitle('Customer Lifetime Value Distribution', fontsize=16, fontweight='bold', y=1.02)

plt.tight_layout()
plt.savefig('outputs/charts/clv_distribution.png', dpi=300, bbox_inches='tight')
print("   ✓ clv_distribution.png")
plt.close()

# 2. Top Customers
fig, ax = plt.subplots(figsize=(12, 8))

top_20 = clv.nlargest(20, 'historical_clv')
ax.barh(range(20), top_20['historical_clv']/1000, color='darkgreen', edgecolor='black')
ax.set_yticks(range(20))
ax.set_yticklabels([f"{cid[:10]}..." for cid in top_20['customer_id']])
ax.set_xlabel('CLV (₹ Thousands)', fontweight='bold')
ax.set_title('Top 20 Customers by Lifetime Value', fontsize=14, fontweight='bold')
ax.grid(alpha=0.3, axis='x')
ax.invert_yaxis()

plt.tight_layout()
plt.savefig('outputs/charts/clv_top_customers.png', dpi=300, bbox_inches='tight')
print("   ✓ clv_top_customers.png")
plt.close()

# 3. CLV by Acquisition Channel
fig, ax = plt.subplots(figsize=(12, 7))

channels = channel_clv.index
avg_clvs = channel_clv['avg_clv']/1000

colors = plt.cm.viridis(np.linspace(0, 1, len(channels)))
ax.bar(channels, avg_clvs, color=colors, edgecolor='black')
ax.set_title('Average CLV by Acquisition Channel', fontsize=14, fontweight='bold')
ax.set_xlabel('Acquisition Channel', fontweight='bold')
ax.set_ylabel('Average CLV (₹ Thousands)', fontweight='bold')
ax.grid(alpha=0.3, axis='y')

# Add value labels
for i, (channel, value) in enumerate(zip(channels, avg_clvs)):
    ax.text(i, value + max(avg_clvs)*0.02, f'₹{value:.0f}k', ha='center', fontweight='bold')

plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.savefig('outputs/charts/clv_by_channel.png', dpi=300, bbox_inches='tight')
print("   ✓ clv_by_channel.png")
plt.close()

# 4. CLV vs Order Frequency  
fig, ax = plt.subplots(figsize=(12, 8))

scatter = ax.scatter(clv['order_count'], clv['historical_clv']/1000, 
                     c=clv['avg_order_value'], cmap='YlOrRd', 
                     s=50, alpha=0.6, edgecolors='black', linewidth=0.5)

ax.set_title('CLV vs Order Frequency (colored by AOV)', fontsize=14, fontweight='bold')
ax.set_xlabel('Number of Orders', fontweight='bold')
ax.set_ylabel('Customer Lifetime Value (₹ Thousands)', fontweight='bold')
ax.grid(alpha=0.3)

# Add colorbar
cbar = plt.colorbar(scatter, ax=ax)
cbar.set_label('Avg Order Value (₹)', fontweight='bold')

plt.tight_layout()
plt.savefig('outputs/charts/clv_vs_frequency.png', dpi=300, bbox_inches='tight')
print("   ✓ clv_vs_frequency.png")
plt.close()

# Key Insights
print("\n" + "=" * 60)
print("KEY INSIGHTS")
print("=" * 60)

print(f"\n💰 AVERAGE CLV: ₹{clv['historical_clv'].mean():,.0f}")
print(f"   • Median CLV: ₹{clv['historical_clv'].median():,.0f}")
print(f"   • Top 10% CLV: ₹{clv['historical_clv'].quantile(0.9):,.0f}")

top_20_pct = (top_customers.head(20)['historical_clv'].sum() / clv['historical_clv'].sum() * 100)
print(f"\n🎯 TOP 20 CUSTOMERS")
print(f"   • Contribute {top_20_pct:.1f}% of total revenue")
print(f"   • Average CLV: ₹{top_customers.head(20)['historical_clv'].mean():,.0f}")

best_channel = channel_clv.iloc[0]
print(f"\n🏆 BEST ACQUISITION CHANNEL: {best_channel.name}")
print(f"   • Average CLV: ₹{best_channel['avg_clv']:,.0f}")
print(f"   • {int(best_channel['customers'])} customers")

high_value = clv[clv['clv_segment'] == 'Very High']
print(f"\n💎 HIGH-VALUE CUSTOMERS: {len(high_value)} ({len(high_value)/len(clv)*100:.1f}%)")
print(f"   • Total Revenue: ₹{high_value['historical_clv'].sum():,.0f}")
print(f"   • Average orders: {high_value['order_count'].mean():.1f}")

print("\n" + "=" * 60)
print("✅ CLV ANALYSIS COMPLETE")
print("=" * 60)
print("\nOutputs saved:")
print("  📄 outputs/clv_scores.csv")
print("  📊 outputs/charts/clv_distribution.png")
print("  📊 outputs/charts/clv_top_customers.png")
print("  📊 outputs/charts/clv_by_channel.png")
print("  📊 outputs/charts/clv_vs_frequency.png")
print("=" * 60)
