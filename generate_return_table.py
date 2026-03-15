import re
import pandas as pd
import warnings

warnings.filterwarnings('ignore')

html_file = 'tamc_backtest_4y_sol_1h.html'
with open(html_file, 'r', encoding='utf-8') as f:
    html = f.read()

labels_match = re.search(r'const labels = \[(.*?)\];', html, re.DOTALL)
equity_match = re.search(r'const equity = \[(.*?)\];', html, re.DOTALL)

if labels_match and equity_match:
    labels_str = labels_match.group(1)
    equity_str = equity_match.group(1)
    
    labels = [x.strip().strip('"') for x in labels_str.split(',')]
    equity = [float(x.strip()) for x in equity_str.split(',')]
    
    df = pd.DataFrame({'Equity': equity}, index=pd.to_datetime(labels))
    df = df.sort_index()
    
    # Identificar capital inicial
    initial_cap = 10000.0  # Asumido por el reporte
    
    # Mensual
    df_monthly = df.resample('M').last()
    df_monthly['Return'] = df_monthly['Equity'].pct_change()
    if len(df_monthly) > 0:
        df_monthly.iloc[0, df_monthly.columns.get_loc('Return')] = (df_monthly.iloc[0]['Equity'] - initial_cap) / initial_cap
        
    # Anual
    df_yearly = df.resample('Y').last()
    df_yearly['Return'] = df_yearly['Equity'].pct_change()
    if len(df_yearly) > 0:
        df_yearly.iloc[0, df_yearly.columns.get_loc('Return')] = (df_yearly.iloc[0]['Equity'] - initial_cap) / initial_cap

    print("\n" + "="*40)
    print("      RETORNOS POR AÑO")
    print("="*40)
    for index, row in df_yearly.iterrows():
        if pd.notna(row['Return']):
            print(f" {index.year}: {row['Return']*100:>10.2f}%")
            
    print("\n" + "="*100)
    print("      RETORNOS POR MES")
    print("="*100)
    
    df_monthly['Year'] = df_monthly.index.year
    df_monthly['Month'] = df_monthly.index.month
    pivot_monthly = df_monthly.pivot(index='Year', columns='Month', values='Return')
    
    month_names = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    # Filtrar solo los meses que existan en el pivot
    cols = []
    for m in pivot_monthly.columns:
        if 1 <= m <= 12:
            cols.append(month_names[int(m)-1])
        else:
            cols.append(str(m))
    pivot_monthly.columns = cols
    
    # Formatear
    formatted_pivot = pivot_monthly.applymap(lambda x: f"{x*100:>7.2f}%" if pd.notna(x) else "      -")
    print(formatted_pivot.to_string())
else:
    print("Datos no encontrados en el HTML.")
