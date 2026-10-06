# AI-Powered Business Decision Intelligence Platform

An end-to-end business analytics and decision intelligence project built using real-world e-commerce data.

The project transforms raw transactional data into validated business analytics, customer segmentation, product and seller analysis, delivery-performance insights, customer-experience analysis, and an executive Power BI dashboard.

---

## 🎯 Project Objective

The goal of this project is to answer four practical business questions:

1. What happened?
2. Why did it happen?
3. What patterns can be identified in customers, products, sellers, delivery, and reviews?
4. What areas should the business investigate or act on?

The project focuses on reproducible analytics rather than fabricated business assumptions.

---

## 📊 Dataset

**Brazilian E-Commerce Public Dataset by Olist**

The dataset contains interconnected tables covering:

- Customers
- Orders
- Order items
- Payments
- Reviews
- Products
- Sellers
- Geolocation
- Product category translations

The dataset contains approximately 100K orders and more than 1.1M geolocation records.

Order purchase dates span from September 2016 to October 2018.

---

## 🏗️ Project Architecture

```text
Real Business Data
        ↓
Data Loading & Profiling
        ↓
Cleaning & Validation
        ↓
SQL Analytical Layer
        ↓
Business Analytics
        ├── RFM Customer Analysis
        ├── Cohort Analysis
        ├── Product & Category Analysis
        ├── Seller & Geographic Analysis
        ├── Delivery & Operations Analysis
        └── Customer Experience Analysis
        ↓
Master Analytics Layer
        ↓
Power BI
        ↓
Executive Business Dashboard

🧹 Data Preparation
The Python pipeline performs:
- Data loading
- Data type conversion
- Date parsing
- Numeric conversion
- Text cleaning
- Duplicate detection and removal
- Missing-value profiling
- Relationship integrity validation
- Delivery-time calculations
- Delivery-performance classification
- Analytical table generation
Important data-quality issues are investigated and documented rather than silently removed.
🗄️ SQL Analytics
A SQLite analytical database is created from the cleaned datasets.
The SQL layer supports analytical queries across:
- Orders
- Customers
- Products
- Sellers
- Payments
- Reviews
- Delivery performance
Database:
04_sql/business_intelligence.db

👥 Customer Analytics
Customer analysis includes:
- Customer frequency
- Repeat-customer identification
- Customer monetary value
- RFM analysis
- Customer segmentation
- Cohort analysis
- Retention analysis
Observed Results
- 96,096 unique customers
- 2,997 repeat customers
- Repeat customer rate: approximately 3.12%
- Most customers placed only one observed order
RFM segmentation was performed using delivered orders and a defined snapshot date.
📦 Product & Category Analytics
Product analysis examines:
- Category sales
- Category order volume
- Average item price
- Freight-to-sales ratio
- Category review performance
Top delivered-sales categories included:
1. Health & Beauty
2. Watches & Gifts
3. Bed Bath Table
4. Sports & Leisure
5. Computers & Accessories
Freight-to-sales ratios are used as an operational indicator only.
They are not treated as profit margins, because the dataset does not contain complete product cost or profit information.
🏪 Seller & Geographic Analytics
Seller analysis includes:
- Seller sales
- Seller order volume
- Seller concentration
- Seller state distribution
Geographic analysis includes:
- Customer state
- Seller state
- Orders by state
- Sales by state
- Average order value
- Delivery performance by state
The top 10 sellers account for approximately 13.27% of delivered item sales.
🚚 Delivery & Operations Analytics
Delivery analysis evaluates:
- Delivery rate
- Average delivery time
- Median delivery time
- Early/late delivery performance
- Delivery-time buckets
- State-level delivery performance
- Approval-to-carrier processing time
Observed results:
- 99,441 total orders
- 96,478 delivered orders
- 97.02% delivery rate
- Average delivery time: approximately 12.56 days
- 7,826 delivered orders classified as late
- Late rate: approximately 8.11%
The dataset also contains timing anomalies, which are documented rather than artificially corrected.
⭐ Customer Experience Analytics
Review analysis examines:
- Review-score distribution
- Review scores vs delivery time
- Review scores vs delivery performance
- State-level review performance
- Review-text availability
Observed results:
- 99,224 reviews
- Average review score: approximately 4.09
- 57,328 five-star reviews
- 11,424 one-star reviews
- 14,575 low reviews (1–2 stars)
- 76,470 high reviews (4–5 stars)
A negative relationship was observed between delivery time and review score.
Correlation between delivery days and review score:
-0.334 approximately

This represents association, not proof of causation.
📈 Power BI Dashboard
The final Power BI dashboard provides an executive overview containing:
KPI Cards
- Total Customers
- Total Orders
- Delivery Rate
- Total Payment Value
- Average Order Value
- Repeat Rate
- Average Review Score
Visual Analytics
- Average Delivery Days by State
- Sales by Product Category
- Monthly Orders Trend
- Customer Type Distribution
- Review Score Distribution
The dashboard uses a dark executive-style theme and is designed for quick business interpretation.
🔍 Data Validation
The project includes a dedicated final validation process.
Final validation result:
35 checks
35 passed
0 failed

Validation includes:
- Source/master order counts
- Delivered-order counts
- Unique customer counts
- Sales reconciliation
- Payment reconciliation
- Missing customer IDs
- Missing order IDs
- Review validation
- Required output-file validation
Final status:
FINAL VALIDATION PASSED
DATA READY FOR POWER BI

🛠️ Tech Stack
Programming
- Python
- Pandas
- NumPy
Analytics
- Statistical analysis
- RFM analysis
- Cohort analysis
- Customer segmentation
- Operational analytics
Database
- SQLite
- SQL
Visualization
- Power BI
- Matplotlib
- Seaborn
Development
- VS Code
- Jupyter Notebook
- Git
- GitHub
📁 Project Structure
Business-Decision-Intelligence/
│
├── 01_data/
│   ├── raw/
│   └── power_bi/
│
├── 02_notebooks/
│   └── 01_data_exploration.ipynb
│
├── 03_src/
│   ├── 01_load_orders.py
│   ├── 02_build_analytics.py
│   ├── 03_create_database.py
│   ├── 04_run_sql.py
│   ├── 05_rfm_analysis.py
│   ├── 06_cohort_analysis.py
│   ├── 07_product_category_analysis.py
│   ├── 08_seller_geographic_analysis.py
│   ├── 09_delivery_operations_analysis.py
│   ├── 10_customer_experience_analysis.py
│   ├── 11_build_master_analytics.py
│   ├── 11a_diagnose_category_sales.py
│   └── 12_final_validation.py
│
├── 04_sql/
│   ├── business_intelligence.db
│   └── analysis_queries.sql
│
├── Business Decision Intelligence.pbix
└── README.md

⚠️ Limitations
This project uses historical observational e-commerce data.
Therefore:
- Correlation does not establish causation.
- Repeat-customer behavior is limited by the dataset observation window.
- The dataset does not provide complete profit/margin information.
- Delivery anomalies are identified but not artificially corrected.
- Some customer review text fields are missing.
- Final business recommendations should be validated against current operational and financial data before implementation.
💡 Key Business Questions Enabled
The platform can help investigate:
- Which product categories generate the most sales?
- Which states experience longer delivery times?
- Where are late deliveries concentrated?
- How does delivery performance relate to customer reviews?
- What proportion of customers return?
- Which customers show higher observed monetary value?
- How concentrated are sales among sellers?
- How does customer behavior change across cohorts?
- Which operational areas deserve further investigation?
🚀 Project Outcome
This project demonstrates an end-to-end analytics workflow:
Raw Data → Python → SQL → Business Analytics → Validation → Power BI → Business Decision Support
The emphasis is on reproducibility, data validation, business reasoning, and honest interpretation of analytical results.
👤 Author
Rachitesh Sharma
MCA — Artificial Intelligence & Machine Learning
Data Analytics | Python | SQL | Power BI | Machine Learning