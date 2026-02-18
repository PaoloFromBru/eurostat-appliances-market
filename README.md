# EU Home Appliances Market Analysis (2014-2024)

This project provides an interactive data visualization of the European market for major domestic appliances, specifically focusing on **Refrigerators, Washing Machines, Dishwashers, and Ovens**. 

The goal is to analyze the shift between local manufacturing and import dependency across the European Union and individual member states.

## 📊 Live Dashboards
If hosted via GitHub Pages, you can access the interactive reports here:
- **[Market Supply & Dependency](index.html)**: Analysis of local production vs. Intra/Extra-EU imports and the Dependency Index.
- **[Manufacturing Dynamics](prodcom_trends.html)**: Trends in production value, quantity, and implicit unit prices.

## 🛠 Methodology & Data Integration
The analysis integrates two primary Eurostat datasets to provide a holistic view of the market:

1. **PRODCOM (Statistics on the production of manufactured goods):**
   - Used to track local EU manufacturing value and volume.
   - Filtered by CPA codes (e.g., `27.51.11` for Refrigerators).
   
2. **COMEXT (International trade in goods):**
   - Used to track Import (Intra-EU and Extra-EU) and Export flows.
   - Filtered by HS/CN8 codes (e.g., `8418` for Refrigeration equipment).

### Key Features
- **EU27 Reconstruction:** Due to missing aggregated data in some trade categories (e.g., Washing Machines), the project includes a "Bottom-up" aggregation logic that reconstructs the EU27 total by summing individual member state data.
- **Dependency Index (Base 2014=100):** A normalized metric tracking how the reliance on imports has evolved relative to the 2014 baseline.
- **Unit Price Analysis:** Calculation of implicit unit prices ($Value / Quantity$) to monitor the "Premiumization" trend in European factories.



## 📈 Strategic Insights
- **Manufacturing Shift:** While local production volumes in some categories remain stable or decline, the **Unit Price Index** often shows an upward trend, suggesting a strategic shift by EU manufacturers toward high-end, energy-efficient appliances.
- **Import Dependency:** The **Dependency Index** highlights which countries and product categories are most vulnerable to Extra-EU competition (e.g., rising imports from China and Turkey).

## 🚀 Technical Stack
- **Python 3.9+**
- **Pandas**: Data cleaning and transformation.
- **Plotly**: Interactive web-based visualizations.
- **SQLite**: Local storage for Eurostat raw data.

---
*Data Source: Eurostat (PRODCOM & COMEXT).*
