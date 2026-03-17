# Example Input Template for LLM Schema Generator

Use this template to gather the information you'll need before starting the schema generation interview with the LLM.

## 1. Table Schema

Provide your table structure in one of these formats:

### Option A: DDL Statement
```sql
CREATE TABLE main.sales.orders (
  order_id STRING, 
  customer_id BIGINT,
  order_date TIMESTAMP,
  order_status STRING,
  total_amount DECIMAL(10,2),
  tax_amount DECIMAL(10,2),
  shipping_fee DECIMAL(10,2),
  payment_method STRING,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

### Option B: Column List
```
Table: main.sales.orders

Columns:
- order_id (STRING) - Primary key
- customer_id (BIGINT) - Foreign key to customers table
- order_date (TIMESTAMP) - When order was placed
- order_status (STRING) - Current status: PENDING, PROCESSING, SHIPPED, DELIVERED, CANCELLED
- total_amount (DECIMAL(10,2)) - Total order value including tax and shipping
- tax_amount (DECIMAL(10,2)) - Sales tax
- shipping_fee (DECIMAL(10,2)) - Shipping cost
- payment_method (STRING) - How customer paid
- created_at (TIMESTAMP) - System created timestamp
- updated_at (TIMESTAMP) - System updated timestamp
```

### Option C: DESCRIBE TABLE Output
```
Paste the output from: DESCRIBE TABLE main.sales.orders
```

## 2. Data Profiling (Optional but Recommended)

Gather basic statistics about your data:

```
Row Count: 2,500,000 rows

Date Range: 
- order_date: 2020-01-01 to present
- Oldest record: 2020-01-01
- Most recent record: 2024-01-15

Key Statistics:
- Unique customers: 150,000
- Average order value: $125.50
- Orders per day: ~2,000

Null Percentages:
- tax_amount: 3% (NULL for tax-exempt orders)
- shipping_fee: <1%
- All other critical fields: <0.1%

Top Values:
- order_status: DELIVERED (60%), SHIPPED (15%), PROCESSING (10%), PENDING (8%), CANCELLED (7%)
- payment_method: CREDIT_CARD (55%), DEBIT_CARD (25%), PAYPAL (15%), OTHER (5%)
```

## 3. Common Queries

List 3-5 typical questions users ask or SQL queries they run:

**Natural Language Questions:**
1. "Show me total revenue for last month"
2. "How many orders do we have today?"
3. "What's the average order value by customer segment?"
4. "Which products are selling best this quarter?"
5. "Show me pending orders that need to ship"

**SQL Queries:**
```sql
-- Daily revenue report
SELECT 
  DATE(order_date) as date,
  SUM(total_amount) as revenue,
  COUNT(DISTINCT order_id) as order_count
FROM main.sales.orders
WHERE order_status = 'DELIVERED'
  AND order_date >= CURRENT_DATE - 30
GROUP BY DATE(order_date);

-- Top customers
SELECT 
  customer_id,
  COUNT(*) as order_count,
  SUM(total_amount) as lifetime_value
FROM main.sales.orders
WHERE order_status != 'CANCELLED'
GROUP BY customer_id
ORDER BY lifetime_value DESC
LIMIT 10;
```

## 4. Business Context

Who uses this table and why:

```
Primary Users:
- Sales analytics team (daily revenue reporting)
- Finance team (monthly reconciliation)
- Operations team (order fulfillment tracking)
- Executive dashboard (KPI monitoring)

Primary Use Cases:
- Revenue reporting and trending
- Order volume analysis
- Customer purchase behavior analysis
- Operational monitoring (pending/processing orders)

Business Domain: Sales / E-commerce

Critical Business Rules:
- Cancelled orders should be excluded from revenue calculations
- Test orders (order_id starting with 'TEST-') should be filtered out
- Only DELIVERED orders count as completed revenue
- Same-day cancellations within 1 hour are expected behavior
```

## 5. Related Tables

List tables that are commonly joined:

```
Related Tables:
1. customers (customer_id) - Get customer name, email, segment, demographics
2. order_items (order_id) - Get line-item product details
3. products (via order_items.product_id) - Get product information
4. shipping_addresses (shipping_address_id) - Get delivery location
5. promotions (promo_code) - Get discount/promotion details
```

## 6. Known Issues & Limitations (Optional)

```
Data Quality Issues:
- Orders before 2021-01-01 may have incomplete shipping addresses
- International orders sometimes have NULL tax_amount
- ~2% of orders missing payment_method due to legacy data

Limitations:
- Only includes completed checkouts (abandoned carts in separate table)
- Refunds tracked in separate refunds table
- Historical data before 2020 archived in orders_archive table
```

## 7. Special Requirements (Optional)

```
Compliance:
- Contains transaction data subject to financial reporting requirements
- PII when joined with customers table

Performance Notes:
- Very high volume table (~2M rows)
- Partitioned by DATE(order_date)
- Always include date filters in queries

SLA:
- Real-time updates (new orders appear within 30 seconds)
- Data retained for 7 years
- 99.9% availability
```

---

## Ready to Generate?

Once you've gathered this information:

1. Copy the LLM schema generator prompt from `app/prompts/schema_generator_prompt.md`
2. Paste it into your LLM interface (Claude, GPT-4, etc.)
3. Provide the information you gathered above
4. Answer the adaptive questions the LLM asks
5. Receive your complete schema YAML file!

## Tips for Best Results

- **Be specific** - The more detail you provide, the better the schema
- **Include examples** - Real queries and use cases help tremendously
- **Know your business rules** - What filters should always apply?
- **Have SQL ready** - Common queries show how the table is actually used
- **Think about ambiguity** - When someone says "revenue", what should it mean?

The more context you provide upfront, the fewer follow-up questions you'll need to answer!
