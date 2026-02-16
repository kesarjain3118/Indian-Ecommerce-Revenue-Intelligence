"""
Product Affinity Analysis - Market Basket Analysis
Identifies products frequently bought together
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder
import warnings
warnings.filterwarnings('ignore')

# Set style
plt.style.use('seaborn-v0_8-darkgrid')

print("=" * 60)
print("PRODUCT AFFINITY ANALYSIS - MARKET BASKET")
print("=" * 60)

# Load data
print("\n1. Loading data...")
orders = pd.read_csv('data/orders.csv')
order_items = pd.read_csv('data/order_items.csv')
products = pd.read_csv('data/products.csv')

# Filter delivered orders
delivered_orders = orders[orders['order_status'] == 'Delivered']['order_id'].unique()
order_items_delivered = order_items[order_items['order_id'].isin(delivered_orders)]

print(f"   ✓ Delivered Orders: {len(delivered_orders):,}")
print(f"   ✓ Order Items: {len(order_items_delivered):,}")

# Create transactions (list of products per order)
print("\n2. Creating transaction data...")

transactions = order_items_delivered.groupby('order_id')['product_id'].apply(list).values
print(f"   ✓ Total transactions: {len(transactions):,}")

# Filter transactions with multiple items (for association rules)
multi_item_transactions = [t for t in transactions if len(t) > 1]
print(f"   ✓ Multi-item transactions: {len(multi_item_transactions):,}")

# Transform to binary format for apriori
te = TransactionEncoder()
te_ary = te.fit(multi_item_transactions).transform(multi_item_transactions)
df_binary = pd.DataFrame(te_ary, columns=te.columns_)

# Run Apriori algorithm
print("\n3. Finding frequent itemsets...")
min_support = max(0.005, 5/len(multi_item_transactions))  # At least 5 occurrences or 0.5%
frequent_itemsets = apriori(df_binary, min_support=min_support, use_colnames=True)

print(f"   ✓ Found {len(frequent_itemsets)} frequent itemsets")
print(f"   • Min support threshold: {min_support:.4f}")

if len(frequent_itemsets) > 0:
    # Generate association rules
    print("\n4. Generating association rules...")
    
    rules = association_rules(frequent_itemsets, metric ="lift", min_threshold=1.0)
    
    if len(rules) > 0:
        # Sort by lift
        rules = rules.sort_values('lift', ascending=False)
        
        # Add product names (if available in products.csv)
        if 'product_name' in products.columns:
            rules['antecedent_names'] = rules['antecedents'].apply(
                lambda x: ', '.join([products[products['product_id'] == prod]['product_name'].values[0] 
                                   if len(products[products['product_id'] == prod]) > 0 else prod 
                                   for prod in x])
            )
            rules['consequent_names'] = rules['consequents'].apply(
                lambda x: ', '.join([products[products['product_id'] == prod]['product_name'].values[0] 
                                   if len(products[products['product_id'] == prod]) > 0 else prod 
                                   for prod in x])
            )
        
        print(f"   ✓ Generated {len(rules)} association rules")
        print(f"\n   Top 10 Product Associations:")
        print("   " + "=" * 80)
        
        for idx, row in rules.head(10).iterrows():
            ant = list(row['antecedents'])[0] if len(row['antecedents']) == 1 else str(row['antecedents'])
            cons = list(row['consequents'])[0] if len(row['consequents']) == 1 else str(row['consequents'])
            print(f"   {ant[:20]:20s} → {cons[:20]:20s} | "
                  f"Lift: {row['lift']:5.2f} | Conf: {row['confidence']*100:5.1f}% | "
                  f"Supp: {row['support']*100:4.1f}%")
        print("   " + "=" * 80)
        
        # Save results
        print("\n5. Saving results...")
        
        # Prepare output
        affinity_output = rules[['antecedents', 'consequents', 'support', 'confidence', 'lift']].copy()
        affinity_output['antecedents'] = affinity_output['antecedents'].apply(lambda x: ', '.join(list(x)))
        affinity_output['consequents'] = affinity_output['consequents'].apply(lambda x: ', '.join(list(x)))
        affinity_output.to_csv('outputs/product_affinity.csv', index=False)
        
        print("   ✓ Saved to outputs/product_affinity.csv")
        
        # Visualizations
        print("\n6. Creating visualizations...")
        
        # 1. Top rules by lift
        fig, ax = plt.subplots(figsize=(12, 8))
        
        top_rules = rules.head(20).copy()
        top_rules['rule'] = top_rules.apply(
            lambda x: f"{list(x['antecedents'])[0][:8]}→{list(x['consequents'])[0][:8]}", axis=1
        )
        
        ax.barh(range(len(top_rules)), top_rules['lift'], color='coral', edgecolor='black')
        ax.set_yticks(range(len(top_rules)))
        ax.set_yticklabels(top_rules['rule'], fontsize=9)
        ax.set_xlabel('Lift', fontweight='bold')
        ax.set_title('Top 20 Product Associations by Lift', fontsize=14, fontweight='bold')
        ax.grid(alpha=0.3, axis='x')
        ax.invert_yaxis()
        
        plt.tight_layout()
        plt.savefig('outputs/charts/affinity_top_rules.png', dpi=300, bbox_inches='tight')
        print("   ✓ affinity_top_rules.png")
        plt.close()
        
        # 2. Confidence vs Support scatter
        fig, ax = plt.subplots(figsize=(10, 8))
        
        scatter = ax.scatter(rules['support']*100, rules['confidence']*100, 
                           c=rules['lift'], cmap='YlOrRd', s=100,  alpha=0.6, edgecolors='black')
        
        ax.set_xlabel('Support (%)', fontweight='bold')
        ax.set_ylabel('Confidence (%)', fontweight='bold')
        ax.set_title('Association Rules: Support vs Confidence (colored by Lift)', 
                     fontsize=14, fontweight='bold')
        ax.grid(alpha=0.3)
        
        cbar = plt.colorbar(scatter, ax=ax)
        cbar.set_label('Lift', fontweight='bold')
        
        plt.tight_layout()
        plt.savefig('outputs/charts/affinity_scatter.png', dpi=300, bbox_inches='tight')
        print("   ✓ affinity_scatter.png")
        plt.close()
        
        # Key Insights
        print("\n" + "=" * 60)
        print("KEY INSIGHTS")
        print("=" * 60)
        
        print(f"\n📊 TOTAL ASSOCIATION RULES: {len(rules)}")
        print(f"   • Average lift: {rules['lift'].mean():.2f}")
        print(f"   • Max lift: {rules['lift'].max():.2f}")
        
        # Best rule
        best_rule = rules.iloc[0]
        print(f"\n🏆 STRONGEST ASSOCIATION:")
        print(f"   {list(best_rule['antecedents'])} → {list(best_rule['consequents'])}")
        print(f"   • Lift: {best_rule['lift']:.2f}")
        print(f"   • Confidence: {best_rule['confidence']*100:.1f}%")
        print(f"   • Support: {best_rule['support']*100:.2f}%")
        
        high_conf_rules = rules[rules['confidence'] >= 0.5]
        if len(high_conf_rules) > 0:
            print(f"\n💡 HIGH CONFIDENCE RULES: {len(high_conf_rules)}")
            print(f"   • Rules with >50% confidence")
    else:
        print("\n   ⚠️ No association rules found with current thresholds")
        print("   • Consider lowering min_support or min_threshold")
        # Create empty file
        pd.DataFrame().to_csv('outputs/product_affinity.csv', index=False)
else:
    print("\n   ⚠️ No frequent itemsets found")
    print("   • Most orders contain single items")
    pd.DataFrame().to_csv('outputs/product_affinity.csv', index=False)

# Additional analysis: most commonly bought together
print("\n7. Top product pairs (co-occurrence)...")

# Count product pairs
from itertools import combinations

pair_counts = {}
for transaction in multi_item_transactions:
    if len(transaction) >= 2:
        for pair in combinations(sorted(transaction), 2):
            pair_counts[pair] = pair_counts.get(pair, 0) + 1

# Sort by frequency
sorted_pairs = sorted(pair_counts.items(), key=lambda x: x[1], reverse=True)

print("\n   Top 10 Product Pairs:")
print("   " + "-" * 60)
for pair, count in sorted_pairs[:10]:
    pct = count / len(multi_item_transactions) * 100
    print(f"   {pair[0]:12s} + {pair[1]:12s}: {count:3d} times ({pct:4.1f}%)")
print("   " + "-" * 60)

# Save pair analysis
pairs_df = pd.DataFrame([
    {'product_1': pair[0], 'product_2': pair[1], 'count': count, 
     'pct_of_transactions': count/len(multi_item_transactions)*100}
    for pair, count in sorted_pairs
])
pairs_df.to_csv('outputs/product_pairs.csv', index=False)
print("\n   ✓ Saved to outputs/product_pairs.csv")

print("\n" + "=" * 60)
print("✅ PRODUCT AFFINITY ANALYSIS COMPLETE")
print("=" * 60)
print("\nOutputs saved:")
print("  📄 outputs/product_affinity.csv")
print("  📄 outputs/product_pairs.csv")
if len(frequent_itemsets) > 0 and len(rules) > 0:
    print("  📊 outputs/charts/affinity_top_rules.png")
    print("  📊 outputs/charts/affinity_scatter.png")
print("=" * 60)
