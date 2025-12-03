import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import io
import base64

#iniciando o app dash
app = dash.Dash(__name__)

df = pd.read_csv(r'C:\Users\davi.carneiro\Desktop\Python02_EAD\04_vendas\vendas.csv')

class AnalisadorDeVendas:

    def __init__(self,dados):
        self.dados = dados
        self.limpar_dados()

    def limpar_dados(self):
        self.dados['data'] = pd.to_datetime(self.dados['data'], errors='coerce') #coerce -> se der erro, continua e não interrompe
        self.dados['valor'] = self.dados['valor'].replace({',':'.'},regex=True).astype(float) #corrige valores monetários
        self.dados.dropna(subset = ['produto','valor'], inplace=True) #remove dados ausentes em colunas importantes
        self.dados['mes'] = self.dados['data'].dt.month #adiciona coluna para mes
        self.dados['ano'] = self.dados['data'].dt.year #adiciona coluna para ano
        self.dados['dia'] = self.dados['data'].dt.day #adiciona coluna para dia
        self.dados['dia_da_semana'] = self.dados['data'].dt.weekday #adiciona coluna para dia da semana

    def analise_vendas_por_produto(self, produtos_filtrados):

        df_produto = self.dados[self.dados['produto'].isin(produtos_filtrados)]
        df_produto = df_produto.groupby('produto')['valor'].sum().reset_index().sort_values(by='valor', ascending=False)

        fig = px.bar(df_produto, x='produto', y='valor', title='Vendas por Produto', color='valor')
        return fig
  
    def analise_vendas_por_regiao(self, regioes_filtradas):
        df_regiao = self.dados[self.dados['regiao'].isin(regioes_filtradas)]
        df_regiao = df_regiao.groupby('regiao')['valor'].sum().reset_index().sort_values(by='valor', ascending=False)
        fig = px.pie(df_regiao, names='regiao', values='valor', title='Vendas Por Região', color='valor')
        
        return fig
    
    def analise_vendas_diarias(self, data_inicio, data_fim):
        df_dia = self.dados[(self.dados['data'] >= data_inicio) & (self.dados['data'] <= data_fim)]
        df_dia = df_dia.groupby('data')['valor'].sum().reset_index()
        fig = px.line(df_dia, x='data', y='valor', title='Vendas Diárias', markers=True)
        
        return fig
    
    def analise_vendas_mensais(self, ano_filtrado):
        df_mes = self.dados[self.dados['ano'] == ano_filtrado]
        df_mes = df_mes.groupby(['ano','mes'])['valor'].sum().reset_index()
        fig = px.line(df_mes, x='mes', y='valor',color='ano',title=f'Vendas Mensais - {ano_filtrado}', markers=True, line_shape='spline')
        return fig
    
    def analise_vendas_por_dia_da_semana(self):
        df_dia_semana = self.dados.groupby('dia_da_semana')['valor'].sum().reset_index()
        df_dia_semana['dia_da_semana'] = df_dia_semana['dia_da_semana'].map({
            0:'Segunda', 1:'Terça', 2:'Quarta', 3:'Quinta', 4:'Sexta', 5:'Sábado',6:'Domingo'
        })
        fig = px.bar(df_dia_semana, x='dia_da_semana',y='valor',title="Vendas por Dia da Semana", color='valor')

        return fig
    
    def distribuicao_vendas(self):

        #nbins divide em varios instervalos os valores, ou seja, vai criar 30 intervalos, cada um com um tamanho aproximado
        #ex.: quantas vendas ficaram entre 0-10, quantas ficaram entre 10-20, quantas ficaram entre 20-30...etc.
        fig = px.histogram(self.dados, x='valor', nbins=30, title='Distribuição de Vendas', color='valor')
        return fig
    
    def analise_media_desvio(self):

        media = self.dados['valor'].mean() #calcula a média
        desvio = self.dados['valor'].std() #calcula o desvio padrão



        return media, desvio

    def vendas_acumuladas(self):

        df_acumulado = self.dados.groupby('data')['valor'].sum().cumsum().reset_index() #cumsum => soma acumulada ao longo do tempo
        df_acumulado['media_movel_7'] = df_acumulado['valor'].rolling(window=7).mean() #média móvel dos últimos 7 dias
        df_acumulado['desvio_padrao_7'] = df_acumulado['valor'].rolling(window=7).std() #desvio padrão dos últimos 7 dias
        df_acumulado['crescimento_percentual'] = df_acumulado['valor'].pct_change() * 100 # #pct_change => variação percentual de um período
        df_acumulado['max_valor'] = df_acumulado['valor'].expanding().max() #considera todas as linhas da tabela
        df_acumulado['min_valor'] = df_acumulado['valor'].expanding().min() #considera todas as linhas da tabela

        fig = px.line(
            df_acumulado,
            x= 'data',
            y=['valor', 'media_movel_7', 'max_valor', 'min_valor'],
            title='Vendas acumuladas ao longo do tempo com Insights Estatísticos',
            labels={
                'valor': 'Vendas Acumuladas',
                'media_movel_7': 'Média móvel (7 dias)',
                'max_valor': 'Máximo Acumulado',
                'min_valor': 'Mínimo Acumulado'
            },
            markers=True
        )
        fig.add_trace(
            go.Scatter(
                x=df_acumulado['data'],
                y=df_acumulado['crescimento_percentual'],
                mode='lines+markers',
                name='Crescimento Percentual',
                line=dict(
                    color='orange',
                    width=2,
                    dash='dot'
                ),
                yaxis='y2' #indica que uará um segundo eixo x (eixo direito do gráfico)

            )
        )

        #estilização do gráfico
        fig.update_layout(
            title_font= dict(size=20, family='Poppins', color='#2980b9'),
            plot_bgcolor= '#34495e',#fundo onde o gráfico é desenhado
            paper_bgcolor='#2c3e30', #fundo externo total da figura, como uma folha por trás do gráfico
            font= dict(color='#ecf0f1', family='Roboto'),
            xaxis= dict(
                title='Data',
                tickformat='%Y-%m-%d',
                showgrid=True,
                gridcolor='#7f8c8d',
                tickangle=45
            ),
            yaxis=dict(
                title='Vendas Acumuladas',
                showgrid=True,
                gridcolor='#7f8c8d'
            ),
            yaxis2=dict(
                title='Crescimento percentual (%)',
                overlaying='y', #usa a mesma área do eixo y principal (sobreposto)
                side='right',
                showgrid=False,
                tickformat='.1f'
            ),
            #configurações da legenda
            legend=dict(
                title='Métricas',
                orientation='h',
                yanchor='bottom',
                y=1.1, #posiciona verticalmente acima do gráfico
                xanchor='center',
                x=0.5 #centraliza horizontalmente a legenda
            ),
            hovermode='x unified', #ao pousar o mouse, exibe uma dica de tela contendo todas as curvas alinhadas ao X
            autosize=True,
            margin=dict(t=50, b=50, l=40, r=40),
            #lista de formas geométricas adicionadas ao gráfico(linhas horizontais)
            shapes=[
                dict(
                    type='line', #Tipo da forma: linha horizontal
                    x0= df_acumulado['data'].min(), #inicio da linha no eixo x: data mínima da série
                    x1= df_acumulado['data'].max(), #final da linha do eixo x: data máxima da série
                    y0= df_acumulado['max_valor'].max(), #altura da linha baseada no valor máximo acumulado
                    y1= df_acumulado['max_valor'].max(), #mesma altura para formar a linha horizontal
                    line= dict(color='red', width=2, dash='dash'), #estilo da linha: vermelha com espessura 2 e tracejada
                    name='Máximo Histórico'
                ),
                dict(
                    type = 'line',
                    x0=df_acumulado['data'].min(),
                    x1=df_acumulado['data'].max(),
                    y0=df_acumulado['min_valor'].min(),
                    y1=df_acumulado['min_valor'].min(),
                    line=dict(color='green', width=2, dash='dash'),
                    name='Mínimo Histórico'

                )
            ]
        )

        return fig

analise = AnalisadorDeVendas(df)

app.layout = html.Div([
    #titulo do formulário
    html.H1("Dashboard de Análise de Vendas", style={'textAlign':'center'}),
    #filtros de seleção do formulário
    html.Div([
        html.Label('Selecione os Produtos:'),
        dcc.Dropdown(
            id = 'produto-dropdown',
            options = [{'label': produto, 'value': produto} for produto in df['produto'].unique()],
            multi = True,
            value = df['produto'].unique().tolist(),
            style = {'width':'48%'}
        ),

        html.Label('Selecione as Regiões:'),
        dcc.Dropdown(
            id = 'regiao-dropdown',
            options = [{'label': regiao, 'value': regiao} for regiao in df['regiao'].unique()],
            multi = True,
            value = df['regiao'].unique().tolist(),
            style = {'width':'48%'}
        ),

        html.Label('Selecione o Ano:'),
        dcc.Dropdown(
            id = 'ano-dropdown',
            options = [{'label': str(ano), 'value': ano} for ano in df['ano'].unique()],
            multi = True,
            value = df['ano'].min(),
            style = {'width':'48%'}
        ),

        html.Label('Selecione o Período:'),
        dcc.DatePickerRange(
            id = 'date-picker-range',
            style = {'width':'48%'},
            start_date = df['data'].min().date(),
            end_date = df['data'].max().date(),
            display_format = 'YYYY-MM-DD'
        ),

        html.Div([

            dcc.Graph(id='grafico-produto'),
            dcc.Graph(id='grafico-regiao'),
            dcc.Graph(id='grafico-diario'),
            dcc.Graph(id='grafico-mensal'),
            dcc.Graph(id='grafico-dia-da-semana'),
            dcc.Graph(id='grafico-distribuicao'),
            dcc.Graph(id='grafico-media-desvio'),
            dcc.Graph(id='grafico-acumulado')

        ])

    ]), #fechamento do html.Div
    

]) #fechamento do html.Div principal

@app.callback(
    Output('grafico-produto', 'figure'),
    Output('grafico-regiao', 'figure'),
    Output('grafico-diario', 'figure'),
    Output('grafico-mensal', 'figure'),
    Output('grafico-dia-da-semana', 'figure'),
    Output('grafico-distribuicao', 'figure'),
    Output('grafico-media-desvio', 'figure'),
    Output('grafico-acumulado', 'figure'),
    Input('produto-dropdown','value'),
    Input('regiao-dropdown','value'),
    Input('ano-dropdown','value'),
    Input('date-picker-range','start_date'),
    Input('date-picker-range','end_date')
)
def update_graphs(produtos, regioes, ano, start_date, end_date):
    try:

        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)

        fig_produto = analise.analise_vendas_por_produto(produtos)
        fig_regiao = analise.analise_vendas_por_regiao(regioes)
        fig_diario = analise.analise_vendas_diarias(start_date,end_date)
        fig_mensal = analise.analise_vendas_mensais(ano)
        fig_dia_da_semana = analise.analise_vendas_por_dia_da_semana()
        fig_distribuicao = analise.distribuicao_vendas()
        media, desvio = analise.analise_media_desvio()
        fig_acumulado = analise.vendas_acumuladas()

        fig_media_desvio = go.Figure(data=[

            go.Bar(x=['Média','Desvio Padrão'], y=[media,desvio],marker_color=['blue','red'])
            
        ], layout=go.Layout(title=f'Média e Desvio Padrão: Média: {media:.2f}, Desvio: {desvio:.2f}',plot_bgcolor='lightgray'))

        return fig_produto, fig_regiao, fig_diario, fig_mensal, fig_dia_da_semana, fig_distribuicao, fig_media_desvio, fig_acumulado

    except Exception as erro:
        print(f'Erro ao atualizar os gáficos: {str(erro)}')
        return go.Figure(), go.Figure(), go.Figure(), go.Figure(), go.Figure(), go.Figure(), go.Figure(), go.Figure()


if __name__ == '__main__':
    app.run(debug=True)
