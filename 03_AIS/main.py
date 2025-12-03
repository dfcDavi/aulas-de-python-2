from flask import Flask, request, jsonify, render_template_string
import pandas as pd
import sqlite3
import os
import plotly.graph_objs as go
from dash import Dash, html, dcc
import numpy as np
import config

app = Flask(__name__)
DB_PATH = config.DB_PATH

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS inadimplencia (
            mes TEXT PRIMARY KEY,
            inadimplencia REAL          
        )''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS selic (
            mes TEXT PRIMARY KEY,
            selic_diaria REAL          
        )''')

        conn.commit()

@app.route('/')
def index():
    return render_template_string('''
        <h1>Upload de dados economicos</h1>
        <form action="/upload" method="POST" enctype="multipart/form-data">
               <label for="campo_inadimplencia">Arquivo de Inadimplencia (CSV):</label>
               <input name="campo_inadimplencia" type="file"><br>   

               <label for "campo_selic">Arquivo de Taxa Selic (CSV):</label>
               <input name="campo_selic" type="file"><br>

               <input type="submit" value="Fazer Upload">               
        </form>   
        <br>
        <hr>
        <a href="/consultar">Consultar dados armazenados</a><br> 
        <a href="/graficos">Visualizar gráficos</a><br>  
        <a href="/editar_inadimplencia">Editar dados de inadimplencia</a><br>  
        <a href="/editar_selic">Editar dados da Selic</a><br> 
        <a href="/correlacao">Analisar correlação</a><br>                          
    ''')

@app.route('/upload', methods=['POST', 'GET'])
def upload():
    inad_file = request.files.get('campo_inadimplencia')
    selic_file = request.files.get('campo_selic')

    if not inad_file or not selic_file:
        return jsonify("Erro: ambos os dados devem ser enviados")

    inad_df = pd.read_csv(
        inad_file,
        sep = ';',
        names = ['data', 'inadimplencia'],
        header = 0
    )

    selic_df = pd.read_csv(
        selic_file,
        sep = ';',
        names = ['data', 'selic_diaria'],
        header = 0
    )

    inad_df['data'] = pd.to_datetime(inad_df['data'], format ='%d/%m/%Y')
    selic_df['data'] = pd.to_datetime(selic_df['data'], format ='%d/%m/%Y')

    inad_df['mes'] = inad_df['data'].dt.to_period('M').astype(str)
    selic_df['mes'] = selic_df['data'].dt.to_period('M').astype(str)
    
    inad_mensal = inad_df[['mes', 'inadimplencia']].drop_duplicates()
    selic_mensal = selic_df.groupby('mes')['selic_diaria'].mean().reset_index()

    with sqlite3.connect(DB_PATH) as conn:
        inad_mensal.to_sql('inadimplencia', conn, if_exists='replace', index=False)
        selic_mensal.to_sql('selic', conn, if_exists='replace', index=False)
    return jsonify({'Mensagem':'Dados armazenados com sucesso!'})
   
@app.route('/consultar', methods=['POST', 'GET'])
def consultar():
   
    if request.method == 'POST':
        tabela = request.form.get('campo_tabela')

        if tabela not in ['inadimplencia', 'selic']:
            return jsonify({'Erro': 'Tabela Inválida!'})

        with sqlite3.connect(DB_PATH) as conn:
            df = pd.read_sql_query(f"SELECT * FROM {tabela}", conn)
            return df.to_html(index=False)

    return render_template_string('''
    <h1>Consulta de tabelas</h1>
    <form method="POST"
        <label for="campo_tabela">Escolha a tabela:</label> 
        <select name="campo_tabela">
            <option value="inadimplencia">Inadimplencia</option>    
            <option value="selic">Taxa Selic</option>  
        </select>
        <input type="submit" value="Consultar">  
    </form>
    <br>
    <a href='/'>Voltar</a>

''')

@app.route('/editar_inadimplencia', methods=['POST', 'GET'])
def editar_inadimplencia():

    if request.method == 'POST':
        mes = request.form.get('campo_mes')
        novo_valor = request.form.get('campo_valor')
        try:
            novo_valor = float(novo_valor)
        except:
            return jsonify({'Erro': 'Valor inválido!'})
        
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE inadimplencia SET inadimplencia = ? WHERE mes = ?", (novo_valor,mes))
            conn.commit()

        return jsonify({'Mensagem:': f'Valor atualizado com sucesso para o mes {mes}!'})

    return render_template_string('''

    <h1>Editar Inadimplência</h1>
        <form method="POST"
            <label for="campo_mes">Mês (AAAA-MM):</label> 
            <input type="text" name="campo_mes">
                                    
            <label for="campo_valor">Novo valor de inadimplência:</label> 
            <input type="text" name="campo_valor">

            <input type="submit" value="Atualizar dados">  
        </form>
        <br>
        <a href='/'>Voltar</a>

    ''')

@app.route('/editar_selic', methods=['POST', 'GET'])
def editar_selic():

    if request.method == 'POST':
        mes = request.form.get('campo_mes')
        novo_valor = request.form.get('campo_valor')

        try:
            novo_valor = float(novo_valor)
        
        except:
            return jsonify({'Erro': 'Valor Inválido!'})
        
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE selic SET selic_diaria = ? WHERE mes = ?",(novo_valor,mes))
            conn.commit()
        
        return jsonify({'Mensagem:': f'Valor atualizado para o mes {mes}'})

    return render_template_string('''

    <h1>Editar Taxa Selic</h1>
        <form method="POST" action="/editar_selic">
            <label for="campo_mes">Mês (AAAA-MM):</label> 
            <input type="text" name="campo_mes">
                                    
            <label for="campo_valor">Novo valor da Selic Diaria:</label> 
            <input type="text" name="campo_valor">

            <input type="submit" value="Atualizar dados">  
        </form>
        <br>
        <a href='/'>Voltar</a>

    ''')

@app.route('/graficos')
def graficos():
    with sqlite3.connect(DB_PATH) as conn:
        inad_df = pd.read_sql_query('SELECT * FROM inadimplencia', conn)
        selic_df = pd.read_sql_query('SELECT * FROM selic', conn)
        
    fig1 = go.Figure()
    fig1.add_trace(
        go.Scatter(
            x = inad_df['mes'],
            y = inad_df['inadimplencia'],
            mode = 'lines+markers',
            name = 'Inadimplencia'
        )
    )

    fig2 = go.Figure()
    fig2.add_trace(
        go.Scatter(
            x = selic_df['mes'],
            y = selic_df['selic_diaria'],
            mode = 'lines+markers',
            name = 'Selic Diaria'
        )
    )
    #tipos de templates: ggplot2, seaborn, simple_white, plotly, plotly_white, plotly_dark, presentation,xgridoff, ygridoff, gridon, none
    fig1.update_layout(
        title = 'Evolução da Inadimplência',
        xaxis_title = 'Mês',
        yaxis_title = '%',
        template = 'plotly_dark'
    )

    fig2.update_layout(
        title = 'Selic Diária',
        xaxis_title = 'Mês',
        yaxis_title = '%',
        template = 'plotly_dark'
    )

    # \/ Aqui vai a SELIC!

    # /\ até aqui.

    graph_html_1 = fig1.to_html(full_html=False, include_plotlyjs='cdn')
    graph_html_2 = fig2.to_html(full_html=False, include_plotlyjs='cdn')

    return render_template_string(
        '''
        <html>
            <head>
                <title> Gráficos Econômicos </title>
                <style>
                    .container{
                        display:flex;
                        justify-content:space-around;
                    }
                    .graph{
                        width: 48%;
                    }
                </style>
            </head>

            <body>

                <h1> Gráficos Econômicos </h1>
                <div class="container">

                    <div class="graph">{{ grafico1|safe }}</div>
                    <div class="graph">{{ grafico2|safe }}</div>

                </div>
            </body>
        </html>
    ''', grafico1 = graph_html_1, grafico2 = graph_html_2)

@app.route('/correlacao')
def correlacao():
    with sqlite3.connect(DB_PATH) as conn:
        inad_df = pd.read_sql_query("SELECT * FROM inadimplencia", conn)
        selic_df = pd.read_sql_query("SELECT * FROM selic", conn)
    merged = pd.merge(inad_df, selic_df, on='mes')

    #o resultado da correl é: 1 -> quando a selic sobe a inadimplencia sobe perfeitamente (correlação positiva),
    #0 -> não há correlação,
    #-1 -> quando a selic sobe, a inadimplencia cai perfeitamente  (correlação negativa)
    correl = merged['inadimplencia'].corr(merged['selic_diaria'])

    #regressão linear para visualização
    x = merged['selic_diaria']
    y = merged['inadimplencia']

    '''
    O polyfit retorna um array de polinomios, onde o grau 1 devolve dois valores
    [m] será nosso coeficiente angular (inclinação da reta)
    [b] será nosso coeficiente linear (intercepto -> valor de y quando x = 0)
    '''
    m, b = np.polyfit(x, y, 1)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x = x,
        y = y,
        mode = 'markers',
        name = 'Inadimplência x Selic',
        marker = dict(
            color = 'rgba(0,123,255,0.8)',
            size = 12,
            line = dict(width = 2, color = 'white'),
            symbol = 'circle'
        ),
        hovertemplate = 'SELIC: %{x:.2f}%<br>Inadimplência: %{y:.2f}% <extra> </extra>'
    ))

    fig.add_trace(go.Scatter(
        x = x,
        y = m * x + b,
        mode = 'lines',
        name = 'Linha de Tendência',
        line = dict(color = 'rgba(220,53,69,1)' , width = 4 , dash = 'dot')
    ))
   
    fig.update_layout(
        title = {
            'text':f'<b>Correlação entre Selic e Inadimplência</b><br><span style="font-size:16px">Coeficiente de Correlação:{correl:.2f}</span>',
            'y':0.95,
            'x':0.5,
            'xanchor':'center',
            'yanchor':'top'
        },
        xaxis_title = dict(
            text = 'SELIC Média Mensal (%)',
            font = dict(size=18, family='Arial', color='gray')
        ),
        yaxis_title = dict(
            text = 'Inadimplência (%)',
            font = dict(size=18, family='Arial', color='gray' )
        ),
        xaxis = dict(
            tickfont = dict(size=14, family='Arial', color='black'),
            gridcolor = 'lightgray'
        ),
        yaxis = dict(
            tickfont = dict(size=14, family='Arial', color='black'),
            gridcolor = 'lightgray'
        ),
        plot_bgcolor = '#f8f9fa',
        paper_bgcolor = 'white',
        font = dict(family='Arial', size=14, color='black'),
        legend = dict(
            orientation = 'h',
            yanchor = 'bottom',
            xanchor = 'center',
            y = 1.05,
            x = 0.5,
            bgcolor = 'rgba(0,0,0,0)',
            borderwidth = 0
        ),
        margin = dict(l=60, r=60, t=120, b=60) #left, right, top, bottom
    )
    graph_html = fig.to_html(full_html=False, include_plotlyjs='cdn')

    return render_template_string('''

        <html>
            <head>
                <title> Correlação Selic vs Inadimplência </title>
                <style>
                    body{font-family:Arial; background-color: #ffffff; color: #333;}
                    .container{
                        width: 90%;
                        margin: auto;
                        text-align: center;
                    }
                    h1 {margin-top: 40px;}
                    a {text-decoration: none; color: #007bff;}
                    a:hover{text-decoration:underline;}
                    .graph{
                        width: 48%;
                    }
                </style>
            </head>

            <body>

                <h1> Correlação Selic vs Inadimplência </h1>
                <div class="container">

                    <div class="graph">{{ graph|safe }}</div>
                    <br>
                </div>
                <div><a href = '/'> Voltar </a></div>
            </body>
        </html>
    ''', graph = graph_html

    )


if __name__ == '__main__':
    init_db()
    app.run(debug=True)