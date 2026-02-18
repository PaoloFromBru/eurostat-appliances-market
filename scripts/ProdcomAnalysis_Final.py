import sqlite3
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import warnings

warnings.filterwarnings("ignore")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PRODCOM = os.path.join(BASE_DIR, 'eurostat_prodcom.db')

def get_prodcom_trends():
    conn = sqlite3.connect(DB_PRODCOM)
    # Rimuoviamo 'unit' dalla SELECT per evitare l'errore
    query = """
    SELECT reporter, year, product, "indicators\\TIME_PERIOD" as indicator, value
    FROM home_appliances_clean
    WHERE indicator IN ('PRODVAL', 'PRODQNT')
      AND CAST(year AS INTEGER) >= 2014
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    # Pivot per avere PRODVAL e PRODQNT come colonne separate
    df_pivot = df.pivot_table(index=['reporter', 'year', 'product'], 
                                columns='indicator', values='value').reset_index()
    
    # Mapping categorie in Inglese
    def cat_map(code):
        if code.startswith('275111'): return 'Refrigerators'
        if code.startswith('275113'): return 'Washing Machines'
        if code.startswith('275112'): return 'Dishwashers'
        if code.startswith('27512'): return 'Ovens'
        return None
        
    df_pivot['category'] = df_pivot['product'].apply(cat_map)
    # Filtriamo via i dati mancanti
    df_pivot = df_pivot.dropna(subset=['category', 'PRODVAL', 'PRODQNT'])
    
    # Aggregazione per Anno e Categoria (Somma di tutti i paesi UE presenti)
    df_agg = df_pivot.groupby(['year', 'category']).agg({'PRODVAL': 'sum', 'PRODQNT': 'sum'}).reset_index()
    
    # Calcolo Prezzo Unitario Implicito (Value / Quantity)
    df_agg['unit_price'] = df_agg['PRODVAL'] / df_agg['PRODQNT']

    # Calcolo Indici Base 2014 = 100
    def calc_indices(group):
        group = group.sort_values('year')
        # Prendiamo i valori del primo anno disponibile (2014)
        b_val = group['PRODVAL'].iloc[0]
        b_qnt = group['PRODQNT'].iloc[0]
        b_prc = group['unit_price'].iloc[0]
        
        # Evitiamo divisioni per zero
        group['val_idx'] = (group['PRODVAL'] / b_val * 100) if b_val > 0 else 100
        group['qnt_idx'] = (group['PRODQNT'] / b_qnt * 100) if b_qnt > 0 else 100
        group['price_idx'] = (group['unit_price'] / b_prc * 100) if b_prc > 0 else 100
        return group

    return df_agg.groupby('category', group_keys=False).apply(calc_indices)

def plot_prodcom():
    df = get_prodcom_trends()
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    categories = sorted(df['category'].unique())

    for cat in categories:
        temp = df[df['category'] == cat]
        is_vis = (cat == 'Refrigerators')
        
        # Traccia Valore (Verde)
        fig.add_trace(go.Scatter(x=temp['year'], y=temp['val_idx'], name="Production Value Index", 
                                 line=dict(color='#2ecc71', width=2), visible=is_vis, meta=cat))
        # Traccia Quantità (Blu)
        fig.add_trace(go.Scatter(x=temp['year'], y=temp['qnt_idx'], name="Production Quantity Index", 
                                 line=dict(color='#3498db', width=2), visible=is_vis, meta=cat))
        # Traccia Prezzo Unitario (Rosso - Dash)
        fig.add_trace(go.Scatter(x=temp['year'], y=temp['price_idx'], name="Unit Price Index", 
                                 line=dict(color='#e74c3c', width=4, dash='dot'), visible=is_vis, meta=cat))

    # Linea orizzontale di riferimento 100
    fig.add_hline(y=100, line_dash="dash", line_color="black")
    
    btns = [dict(label=c, method="update", args=[{"visible": [t.meta == c for t in fig.data]}, 
            {"title": f"EU Manufacturing Dynamics: {c} (Index 2014=100)"}]) for c in categories]
    
    fig.update_layout(
        updatemenus=[dict(buttons=btns, x=0, y=1.2, xanchor="left")],
        template="plotly_white",
        title="Manufacturing Evolution: Value, Quantity and Unit Price",
        yaxis=dict(title="Index (2014 = 100)")
    )
    
    fig.write_html("prodcom_trends.html")
    print("Success: prodcom_trends.html generated.")

if __name__ == "__main__":
    plot_prodcom()
