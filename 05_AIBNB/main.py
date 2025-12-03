import pandas as pd
import numpy as np
import plotly.graph_objects as go
import webbrowser

#função recebe um dataframe como entrada e devolve um dataframe como saída
def padroniza_colunas(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    #várias possibilidades de como pode vir a coluna na leitura dos dados
    lat_candidatos = ['lat', 'latitude', 'Latitude', 'LAT', 'Lat', 'LATITUDE']
    lon_candidatos = ['lon', 'longitude', 'longitude', 'LON', 'Lon', 'Long', 'lng']
    custo_candidatos = ['custo', 'valor', 'preco', 'preço', 'cost', 'valor_total', 'price']
    nome_candidatos = ['nome', 'place', 'title', 'name', 'local', 'titulo']

    def pegar(nome_coluna, candidatos):

        #nome_coluna: lista de nomes das colunas da tabela
        #candidato: lista de possíveis nomes de colunas a serem percorridas
        
        #percorre cada candidato dentro da lista de candidatos
        for candidato in candidatos:
            if candidato in nome_coluna:
                return candidato
        
        #se não encontrou uma correspondência exata, percorre novamente cada candidato
        #mas dessa vez ignorando maiusculas e minusculas
        for candidato in candidatos:
            for coluna in nome_coluna:
                if candidato.lower() in coluna.lower():
                    return coluna
                
        return None
    
    lat_col = pegar(df.columns,lat_candidatos)
    lon_col = pegar(df.columns,lon_candidatos)
    custo_col = pegar(df.columns,custo_candidatos)
    nome_col = pegar(df.columns,nome_candidatos)

    if lat_col is None or lon_col is None:
        raise ValueError(f"Não encontrei colunas de latitude e longitude {list(df.columns)}")
    
    out = pd.DataFrame()
    out['lat']    = pd.to_numeric(df[lat_col], errors='coerce') 
    out['lon']    = pd.to_numeric(df[lon_col], errors='coerce') 
    out['custo']  = pd.to_numeric(df[custo_col], errors='coerce') if custo_col is not None else np.nan 
    out['nome']   = df[nome_col].astype(str) if nome_col is not None else [f"Ponto {i}" for i in range (len(df))] 
    out = out.dropna(subset=['lat', 'lon']).reset_index(drop=True)

    if out['custo'].notna().any():
        med = float(out['custo'].median())

        if not np.isfinite(med):
            med = 1.0

        out['custo'] = out['custo'].fillna(med)

    else:
        out['custo'] = 1.0

    return out

def centralizar_mapa(df: pd.DataFrame) -> dict:

    return dict(
        lat = float(df['lat'].mean()),
        lon = float(df['lon'].mean())
    )

#Traces do gráfico
def pontos_trace(df: pd.DataFrame, name:str) -> go.Scattermapbox:

    hover = ("<b>%{customdata[0]}%</b><br>"
             "Custo: %{customdata[1]}<br>"
             "Lat: %{lat: .5f} <br> Lon: %{lon: .5f}<br>")
    c = df['custo'].astype(float).values
    c_min, c_max = float(np.min(c)), float(np.max(c))

    #esse bloco é usado quando existem valores não numéricos , ou todos os custos são praticamente iguais
    if not np.isfinite(c_min) or not np.isfinite(c_max) or abs(c_max - c_min) < 1e-9:
        size = np.full_like(c, 10.0, dtype=float)
    else:
        #[caso normal]
        #Normalizamos os valores válidos diferentes, onde transformamos os valores no intervalo 0,1
        #depois escalonamos para 6 até 26, ou seja, valores baixos para tamanho proximo a 6 e custos altos
        size = (c - c_min) / (c_max - c_min) * 20 + 6

    sizes = np.clip(size, 6, 26)
    custom = np.stack([df['nome'].values, df['custo'].values], axis=1)

    return go.Scattermapbox(
        lat=df['lat'],
        lon=df['lon'],
        mode='markers',
        marker=dict(
            size=sizes,
            color=df['custo'],
            colorscale="Viridis",
            colorbar=dict(title='Custo')
        ),
        name=f"{name} * Pontos",
        hovertemplate= hover,
        customdata= custom
    )

def densidade_trace(df: pd.DataFrame, name:str) -> go.Densitymapbox:
   return go.Densitymapbox(
       lat=df['lat'],
       lon=df['lon'],
       z=df['custo'],
       radius=20,
       colorscale='Inferno',
       name=f"{name} * Calor",
       colorbar=dict(title='custo')
   )

def salvar_csv(df: pd.DataFrame, caminho:str) -> None:
    df.to_csv(caminho, index=False)
    print(f"Arquivo salvo: {caminho}")


def grafico_custo_medio(ny: pd.DataFrame, rj: pd.DataFrame, boston: pd.DataFrame, pasta) -> None:
    cidades = ['New York', 'Rio de Janeiro', 'Boston']
    custos_medios = [
        float(ny['custo'].mean()),
        float(rj['custo'].mean()),
        float(boston['custo'].mean()),
    ]

    fig_bar = go.Figure(

        data=[
            go.Bar(
                x=cidades,
                y=custos_medios,
                text=[f"{custo:.2f}" for custo in custos_medios],
                textposition='auto',
                name='Custo Médio'
            )
        ]
    )

    fig_bar.update_layout(
        title='Custo médio por cidade',
        xaxis_title='Cidade',
        yaxis_title='Custo médio'
    )
    arquivo = f"{pasta}custo_medio_cidades.html"

    fig_bar.write_html(arquivo, include_plotlyjs='cdn', full_html=True)
    print(f"Arquivo salvo: {arquivo}")

#---------------MAIN-----------------#
def main():
    pasta = "C:/Users/davi.carneiro/Desktop/Python02_EAD/05_AIBNB/"
    ny = padroniza_colunas(pd.read_csv(f"{pasta}ny.csv"))
    rj = padroniza_colunas(pd.read_csv(f"{pasta}rj.csv"))
    boston = padroniza_colunas(pd.read_csv(f"{pasta}boston.csv"))

    ny_pontos = pontos_trace(ny, "New York Point Trace")
    ny_calor = densidade_trace(ny, "New York Heat Map")

    rj_pontos = pontos_trace(rj, "Rio de Janeiro Point Trace")
    rj_calor = densidade_trace(rj, "Rio de Janeiro Heat Map")

    boston_pontos = pontos_trace(boston, "Boston Point Trace")
    boston_calor = densidade_trace(boston, "Boston Heat Map")

    fig = go.Figure([ny_pontos, ny_calor, rj_pontos, rj_calor, boston_pontos, boston_calor])

    def centralizar_mapa_e_zoom(df, zoom):
        #return dict(center=centralizar_mapa(df),zoom=zoom)
        return {
            "mapbox.center": dict(
                lat=float(df["lat"].mean()),
                lon=float(df["lon"].mean())
            ),
            "mapbox.zoom": zoom
        }
    
    buttons = [
        dict(
            label="New York * Pontos",
            method="update",
            args= [
                {"visible":[True,False,False,False, False, False]},
                centralizar_mapa_e_zoom(ny,9)
            ]
        ),
        dict(

            label="New York * Calor",
            method="update",
            args= [
                {"visible":[False,True,False,False, False, False]},
                centralizar_mapa_e_zoom(ny,9)
            ]

        ),
        dict(

            label="Rio de Janeiro * Pontos",
            method="update",
            args= [
                {"visible":[False,False,True,False, False, False]},
                centralizar_mapa_e_zoom(rj,10)
            ]

        ),
        dict(

            label="Rio de Janeiro * Calor",
            method="update",
            args= [
                {"visible":[False,False,False,True, False, False]},
                centralizar_mapa_e_zoom(rj,10)
            ]    

        ),
        dict(

            label="Boston * Pontos",
            method="update",
            args= [
                {"visible":[False,False,False,False,True,False]},
                centralizar_mapa_e_zoom(boston,10)
            ]    

        ),
        dict(

            label="Boston * Calor",
            method="update",
            args= [
                {"visible":[False,False,False,False,False,True]},
                centralizar_mapa_e_zoom(boston,10)
            ]    

        )
    ]

    buttons.append(
        dict(
            label = "Todas as Cidades * Pontos",
            method = "update",
            args = [
                {"visible":[True,False,True,False,True,False]},
                centralizar_mapa_e_zoom(
                    pd.concat([ny, rj, boston], ignore_index=True),
                    zoom=2.5
                )
            ]
        )
    )

    buttons.append(
        dict(
            label = "Todas as Cidades * Calor",
            method = "update",
            args = [
                {"visible":[False,True,False,True,False,True]},
                centralizar_mapa_e_zoom(
                    pd.concat([ny, rj, boston], ignore_index=True),
                    zoom=2.5
                )
            ]
        )
    )

    fig.update_layout(
        title="Mapa Interativo de Custos",
        mapbox_style="open-street-map",
        mapbox=dict(center=dict(lat=float(rj['lat'].mean()),lon=float(rj['lon'].mean())),zoom=10),
        margin=dict(l=10,r=10,t=50,b=10),
        updatemenus=[dict(
            buttons = buttons,
            direction="down",
            x=0.01,
            y=0.99,
            xanchor="left",
            yanchor="top",
            bgcolor="white",
            bordercolor="lightgray"
        )],
        legend = dict(
            orientation = 'h',
            x=0.01,
            y=0.99
        )
    )

    arquivo = f"{pasta}mapa_custos_interativos.html"

    fig.write_html(
        f"{pasta}mapa_custos_interativos.html",
        include_plotlyjs = "cdn",
        full_html = True
    )

    for nome, df_cidade in [("Nova York", ny), ("Rio de Janeiro", rj), ("Boston", boston)]:
        print(f"\n Resumo de {nome}:")
        print(f" Pontos: {len(df_cidade)}")
        print(f"Custo médio: {df_cidade['custo'].mean():.2f}")
        print(f"Custo médio: {df_cidade['custo'].min():.2f}")
        print(f"Custo médio: {df_cidade['custo'].max():.2f}")
    salvar_csv(ny, f"{pasta}ny_limpo.csv")
    salvar_csv(rj, f"{pasta}rj_limpo.csv")
    salvar_csv(boston, f"{pasta}boston_limpo.csv")

    grafico_custo_medio(ny, rj, boston, pasta)

    print(f"Arquivo gerado com sucesso em: {pasta}mapa_custos_interativos.html")
    webbrowser.open(arquivo)

if __name__ == '__main__':
    main()

#Fazer o ranking das cidades com maiores custos