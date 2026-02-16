"""
Churn Prediction - Identify At-Risk Customers
Predicts customers likely to churn based on behavior patterns
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
import warnings
warnings.filterwarnings('ignore')

plt.style.use('seaborn-v0_8-darkgrid')

print("=" * 60)
print("CHURN PREDICTION - AT-RISK CUSTOMERS")
print("=" * 60)

# Load data
print("\n1. Loading data...")
customers = pd.read_csv('data/customers.csv')
orders = pd.read_csv('data/orders.csv')
order_items = pd.read_csv('data/order_items.csv')

customers['signup_date'] = pd.to_datetime(customers['signup_date'])
orders['order_date'] = pd.to_datetime(orders['order_date'])

# Calculate revenue
order_revenue = order_items.groupby('order_id')['revenue'].sum().reset_index()
orders_with_revenue = orders.merge(order_revenue, on='order_id', how='left')
delivered = orders_with_revenue[orders_with_revenue['order_status'] == 'Delivered'].copy()

analysis_date = delivered['order_date'].max()
churn_threshold_days = 90  # No purchase in last 90 days = churned

print(f"   ✓ Analysis Date: {analysis_date.date()}")
print(f"   ✓ Churn Threshold: {churn_threshold_days} days")

# Define churn
print("\n2. Defining churn...")

customer_last_order = delivered.groupby('customer_id')['order_date'].max().reset_index()
customer_last_order.columns = ['customer_id', 'last_order_date']
customer_last_order['days_since_last_order'] = (analysis_date - customer_last_order['last_order_date']).dt.days

# Customer is churned if they haven't purchased in 90+ days AND had at least one previous purchase
customer_last_order['churned'] = (customer_last_order['days_since_last_order'] > churn_threshold_days).astype(int)

churned_count = customer_last_order['churned'].sum()
churn_rate = churned_count / len(customer_last_order) * 100

print(f"   ✓ Customers analyzed: {len(customer_last_order):,}")
print(f"   ✓ Churned customers: {churned_count:,} ({churn_rate:.1f}%)")
print(f"   ✓ Active customers: {len(customer_last_order) - churned_count:,} ({100-churn_rate:.1f}%)")

# Build features for prediction
print("\n3. Building prediction features...")

# RFM features
rfm = delivered.groupby('customer_id').agg({
    'order_date': lambda x: (analysis_date - x.max()).days,
    'order_id': 'count',
    'revenue': 'sum'
}).reset_index()
rfm.columns = ['customer_id', 'recency', 'frequency', 'monetary']

# Merge with customer data
features = rfm.merge(customers[['customer_id', 'signup_date', 'acquisition_channel', 'age']], 
                      on='customer_id', how='left')

# Customer lifetime
features['customer_lifetime_days'] = (analysis_date - features['signup_date']).dt.days

# Average time between orders
customer_order_dates = delivered.groupby('customer_id')['order_date'].apply(list).reset_index()
features = features.merge(customer_order_dates, on='customer_id', how='left')

def avg_days_between_orders(dates):
    if len(dates) < 2:
        return 0
    dates_sorted = sorted(dates)
    diffs = [(dates_sorted[i+1] - dates_sorted[i]).days for i in range(len(dates_sorted)-1)]
    return np.mean(diffs)

features['avg_days_between_orders'] = features['order_date'].apply(avg_days_between_orders)
features = features.drop('order_date', axis=1)

# Merge churn label
features = features.merge(customer_last_order[['customer_id', 'churned']], 
                           on='customer_id', how='left')

# Encode categorical
features['channel_encoded'] = pd.Categorical(features['acquisition_channel']).codes

# Select features for model
feature_cols = ['recency', 'frequency', 'monetary', 'age', 'customer_lifetime_days', 
                'avg_days_between_orders', 'channel_encoded']

X = features[feature_cols].fillna(0)
y = features['churned']

print(f"   ✓ Features created: {len(feature_cols)}")

# Train model
print("\n4. Training churn prediction model...")

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)

model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
model.fit(X_train, y_train)

# Predict
y_pred = model.predict(X_test)
y_pred_proba = model.predict_proba(X_test)[:, 1]

# Evaluate
print("\n   Model Performance:")
print("   " + "-" * 60)
print(classification_report(y_test, y_pred, target_names=['Active', 'Churned']))
print("   " + "-" * 60)
print(f"   ROC-AUC Score: {roc_auc_score(y_test, y_pred_proba):.3f}")

# Predict for all customers
features['churn_probability'] = model.predict_proba(X)[:, 1]
features['churn_prediction'] = model.predict(X)
features['risk_level'] = pd.cut(features['churn_probability'], 
                                 bins=[0, 0.3, 0.6, 1.0], 
                                 labels=['Low', 'Medium', 'High'])

# Feature importance
feature_importance = pd.DataFrame({
    'feature': feature_cols,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

print(f"\n   Feature Importance:")
print("   " + "-" * 60)
for idx, row in feature_importance.iterrows():
    print(f"   {row['feature']:25s}: {row['importance']:.3f}")
print("   " + "-" * 60)

# Save results
print("\n5. Saving results...")
churn_output = features[['customer_id', 'recency', 'frequency', 'monetary', 'acquisition_channel',
                           'churned', 'churn_probability', 'churn_prediction', 'risk_level']].copy()
churn_output.to_csv('outputs/churn_predictions.csv', index=False)
print("   ✓ Saved to outputs/churn_predictions.csv")

# Visualizations
print("\n6. Creating visualizations...")

# 1. Churn Probability Distribution
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

axes[0].hist(features['churn_probability'], bins=30, edgecolor='black', alpha=0.7, color='orangered')
axes[0].axvline(0.5, color='red', linestyle='--', linewidth=2, label='Threshold (0.5)')
axes[0].set_title('Churn Probability Distribution', fontweight='bold')
axes[0].set_xlabel('Churn Probability')
axes[0].set_ylabel('Number of Customers')
axes[0].legend()
axes[0].grid(alpha=0.3)

# Risk level pie
risk_counts = features['risk_level'].value_counts()
colors = ['green', 'orange', 'red']
axes[1].pie(risk_counts, labels=risk_counts.index, autopct='%1.1f%%', colors=colors, startangle=90)
axes[1].set_title('Customers by Risk Level', fontweight='bold')

plt.tight_layout()
plt.savefig('outputs/charts/churn_probability.png', dpi=300, bbox_inches='tight')
print("   ✓ churn_probability.png")
plt.close()

# 2. Feature Importance
fig, ax = plt.subplots(figsize=(10, 6))

ax.barh(range(len(feature_importance)), feature_importance['importance'], color='coral', edgecolor='black')
ax.set_yticks(range(len(feature_importance)))
ax.set_yticklabels(feature_importance['feature'])
ax.set_xlabel('Importance', fontweight='bold')
ax.set_title('Feature Importance for Churn Prediction', fontsize=14, fontweight='bold')
ax.grid(alpha=0.3, axis='x')
ax.invert_yaxis()

plt.tight_layout()
plt.savefig('outputs/charts/churn_feature_importance.png', dpi=300, bbox_inches='tight')
print("   ✓ churn_feature_importance.png")
plt.close()

# Key Insights
print("\n" + "=" * 60)
print("KEY INSIGHTS")
print("=" * 60)

at_risk = features[features['risk_level'].isin(['Medium', 'High'])]
print(f"\n⚠️  AT-RISK CUSTOMERS: {len(at_risk):,} ({len(at_risk)/len(features)*100:.1f}%)")
print(f"   • High risk: {len(features[features['risk_level'] == 'High']):,}")
print(f"   • Medium risk: {len(features[features['risk_level'] == 'Medium']):,}")
print(f"   • Potential revenue at risk: ₹{at_risk['monetary'].sum():,.0f}")

top_feature = feature_importance.iloc[0]
print(f"\n🔑 TOP PREDICTOR: {top_feature['feature']}")
print(f"   • Importance: {top_feature['importance']:.3f}")

high_risk_top_10 = features[features['risk_level'] == 'High'].nlargest(10, 'monetary')
if len(high_risk_top_10) > 0:
    print(f"\n💰 HIGH-VALUE AT-RISK CUSTOMERS: {len(high_risk_top_10)}")
    print(f"   • Total value: ₹{high_risk_top_10['monetary'].sum():,.0f}")

print("\n" + "=" * 60)
print("✅ CHURN PREDICTION COMPLETE")
print("=" * 60)
print("\nOutputs saved:")
print("  📄 outputs/churn_predictions.csv")
print("  📊 outputs/charts/churn_probability.png")
print("  📊 outputs/charts/churn_feature_importance.png")
print("=" * 60)
