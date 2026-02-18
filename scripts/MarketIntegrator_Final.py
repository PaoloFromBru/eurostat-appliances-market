import sqlite3
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import warnings

warnings.filterwarnings("ignore")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PRODCOM = os.path.join(BASE_DIR, 'eurostat_prodcom.db')
DB_COMEXT = os.path.join(BASE_DIR, 'data/database.db')

UE27_MEMBERS = ['AT', 'BE', 'BG', 'CY', 'CZ', 'DE', 'DK', 'EE', 'ES', 'FI', 
                'FR', 'GR', 'HR', 'HU', 'IE', 'IT', 'LT', 'LU', 'LV', 'MT', 
                'NL', 'PL', 'PT', 'RO', 'SE', 'SI', 'SK']

def get_data_english():
    # Production Data (PRODCOM)
    conn_p = sqlite3.connect(DB_PRODCOM)
    df_p = pd.read_sql_query("SELECT reporter, year, product, value as prod_val FROM home_appliances_clean WHERE \"indicators\\TIME_PERIOD\" = 'PRODVAL' AND CAST(year AS INTEGER) >= 2014", conn_p)
    conn_p.close()
    
    # CPA to Category Mapping (English)
    def cat_map_en(code):
        if code.startswith('275111'): return 'Refrigerators'
        if code.startswith('275113'): return 'Washing Machines'
        if code.startswith('275112'): return 'Dishwashers'
        if code.startswith('27512'): return 'Ovens'
        return None
    df_p['category'] = df_p['product'].apply(cat_map_en)
    df_p = df_p.dropna(subset=['category']).groupby(['reporter', 'year', 'category'])['prod_val'].sum().reset_index()

    # Trade Data (COMEXT)
    conn_c = sqlite3.connect(DB_COMEXT)
    df_c = pd.read_sql_query("SELECT r.reporter_id as reporter, r.period as year, pg.name as cat_raw, r.flow_id, t.name as t_type, SUM(r.value_in_eur) as t_val FROM records r JOIN trade_types t ON r.trade_type_id = t.id JOIN products p ON r.product_id = p.id JOIN product_groups pg ON p.product_group_id = pg.id WHERE CAST(r.period AS INTEGER) >= 2014 GROUP BY reporter, year, cat_raw, flow_id, t_type", conn_c)
    conn_c.close()

    # Align Category Names
    cat_align = {'Refrigerators': 'Refrigerators', 'Washing machines': 'Washing Machines', 'Dishwashers': 'Dishwashers', 'Ovens': 'Ovens'}
    df_c['category'] = df_c['cat_raw'].map(cat_align)
    df_c = df_c.dropna(subset=['category'])

    # Virtual EU27 Reconstruction
    df_ue_agg = df_c[df_c['reporter'].isin(UE27_MEMBERS)].groupby(['year', 'category', 'flow_id', 't_type'])['t_val'].sum().reset_index()
    df_ue_agg['reporter'] = 'EU27_2020'
    df_c_final = pd.concat([df_c, df_ue_agg]).drop_duplicates(subset=['reporter', 'year', 'category', 'flow_id', 't_type'], keep='last')

    # Pivot and Dependency Calculation
    df_pivot = df_c_final.pivot_table(index=['reporter', 'year', 'category'], columns=['flow_id', 't_type'], values='t_val', fill_value=0)
    df_pivot.columns = [f"f{c[0]}_{'Intra' if 'Intra' in c[1] else 'Extra'}" for c in df_pivot.columns]
    df_pivot = df_pivot.reset_index()
    df_pivot['imp_tot'] = df_pivot.get('f1_Intra', 0) + df_pivot.get('f1_Extra', 0)
    
    df_merged = pd.merge(df_p, df_pivot, on=['reporter', 'year', 'category'], how='outer').fillna(0)
    df_merged['dependency'] = (df_merged['imp_tot'] / (df_merged['prod_val'] + df_merged['imp_tot']) * 100).fillna(0)
    
    def calc_idx(group):
        group = group.sort_values('year')
        base = group['dependency'].iloc[0]
        group['dep_index'] = (group['dependency'] / base * 100) if base > 0.1 else 100.0
        return group
    
    return df_merged.groupby(['reporter', 'category'], as_index=False).apply(calc_idx).reset_index(drop=True)

def plot_final():
    df = get_data_english()
    if df.empty:
        print("Error: No data found after integration.")
        return

    reporters = sorted(df['reporter'].unique())
    categories = sorted(df['category'].unique())
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Set default view
    def_rep = 'EU27_2020' if 'EU27_2020' in reporters else reporters[0]
    def_cat = 'Refrigerators' if 'Refrigerators' in categories else categories[0]

    for cat in categories:
        for rep in reporters:
            temp = df[(df['category'] == cat) & (df['reporter'] == rep)].sort_values('year')
            if temp.empty: continue
            
            # Initial visibility logic
            is_vis = (cat == def_cat and rep == def_rep)
            m_tag = f"{cat}|{rep}"
            
            # Area Chart Traces (Y1)
            fig.add_trace(go.Scatter(x=temp['year'], y=temp['prod_val'], name="Local Manufacturing", stackgroup='one', fillcolor='#2ecc71', line=dict(width=0), visible=is_vis, meta=m_tag), secondary_y=False)
            fig.add_trace(go.Scatter(x=temp['year'], y=temp.get('f1_Intra', 0), name="Intra-EU Import", stackgroup='one', fillcolor='#3498db', line=dict(width=0), visible=is_vis, meta=m_tag), secondary_y=False)
            fig.add_trace(go.Scatter(x=temp['year'], y=temp.get('f1_Extra', 0), name="Extra-EU Import", stackgroup='one', fillcolor='#e74c3c', line=dict(width=0), visible=is_vis, meta=m_tag), secondary_y=False)
            
            # Index Trace (Y2)
            fig.add_trace(go.Scatter(x=temp['year'], y=temp['dep_index'], name="Dependency Index", visible=is_vis, line=dict(color='black', width=3), meta=m_tag), secondary_y=True)

    # Define Buttons (This was missing!)
    cat_btns = [dict(label=c, method="update", args=[{"visible": [t.meta == f"{c}|{def_rep}" for t in fig.data]}, {"title": f"{c} Trend in {def_rep}"}]) for c in categories]
    rep_btns = [dict(label=r, method="update", args=[{"visible": [t.meta == f"{def_cat}|{r}" for t in fig.data]}, {"title": f"{def_cat} Trend in {r}"}]) for r in reporters]

    # Baseline 2014
    fig.add_hline(y=100, line_dash="dash", line_color="grey", secondary_y=True, annotation_text="2014 Baseline")

    fig.update_layout(
        updatemenus=[
            dict(buttons=cat_btns, x=0.0, y=1.2, xanchor="left", active=categories.index(def_cat) if def_cat in categories else 0),
            dict(buttons=rep_btns, x=0.2, y=1.2, xanchor="left", active=reporters.index(def_rep) if def_rep in reporters else 0)
        ],
        template="plotly_white",
        title=f"{def_cat} Market Analysis in {def_rep}",
        yaxis=dict(title="Market Value (EUR)"),
        yaxis2=dict(title="Index (2014=100)", side="right", overlaying="y", range=[0, None]),
        margin=dict(t=150)
    )

    fig.write_html("index.html")
    print("Dashboard generated successfully as index.html")

if __name__ == "__main__":
    plot_final()
