import argparse #permite criar e gerenciar argumentos de linha de comando (Ex.: recebe um parâmetro e executa um script)
import csv
from collections import Counter #estrutura de dados que conta ocorrências de itens (conta palavras, números, etc.)
from datetime import datetime
import re #biblioteca de expressões regulares (usada para buscar e manipular padrões em strings)
import os 
import pandas as pd

try:

    import plotly.graph_objs as go
    from plotly.subplots import make_subplots #permite criar figuras com múltiplos subplots
    _plotly_available = True

except ImportError:
    _plotly_available = False

def classifica_lutador(text: str) -> str:
    texto = str(text).lower()
    mayweather = 'mayweather' in texto
    mcgregor = 'mcgregor' in texto

    if mayweather and not mcgregor:
        return 'mayweather'
    elif mcgregor and not mayweather:
        return 'mcgregor'
    elif mayweather and mcgregor:
        return 'Both'
    else:
        return 'None'
    
def extrair_emojis(text: str) -> list[str]:

    emoji_pattern = re.compile(

        r'['
        r'\U0001F600-\U0001F64F'  #emoticons
        r'\U0001F300-\U0001F5FF'  #simbolos e pictogramas
        r'\U0001F680-\U0001F6FF'  #transportes e simbolos de mapas
        r'\U0001F700-\U0001F77F'  #simbolos quimicos
        r'\U0001F780-\U0001F7FF'
        r'\U0001F800-\U0001F8FF'
        r'\U0001F900-\U0001F9FF'
        r'\U0001FA00-\U0001FA6F'
        r'\U0001FA70-\U0001FAFF'
        r'\u2600-\u26FF'          #simbolos gerais 
        r'\u2700-\u27BF'          #dingbats
        r']',
        flags=re.UNICODE
    )
    return [ch for ch in str(text) if emoji_pattern.match(ch)]

def sentimento(emojis: list[str]) -> int:
    positivos = {
        '😂','🤣','😍','❤','♥','💕','💖','👍','😊','😁','👏','💪','🔥','😄','😃','😆',
        '😇','😎','🙂','🤗','🎉','🌟','💯','🙌','✨','😺','😸'
    }

    negativos = {

        '😡','👎','😢','😭','💀','😠','😖','😩','😤','😪','😓','😞','😟','😔','😬',
        '😕','😣','🙁','😰','😱','💩','☹','⚰','👿','😿'
    }

    pontos = 0

    for ch in emojis:
        if ch in positivos:
            pontos += 1
        elif ch in negativos:
            pontos -= 1
            
    return pontos

def main(csv_caminho: str) -> None:
    if not os.path.exists(csv_caminho):
        raise FileNotFoundError(f"Arquivo csv não encontrado: {csv_caminho}")
    
    df = pd.read_csv(csv_caminho)
    df['created_at'] = pd.to_datetime(df['created_at'])
    df['minute'] = df['created_at'].dt.floor('min')
    df['lutador'] = df['text'].apply(classifica_lutador)
    df['emoji'] = df['text'].apply(extrair_emojis)
    df['sentimento'] = df['emoji'].apply(sentimento)

    sentimento_por_minuto = (

        df.groupby('minute')['sentimento'].mean().reset_index(name='sentimento_medio') #sentimento médio
    )

    engajamento_por_minuto = (

        df.groupby('minute').size().reset_index(name='engajamento') #quantidade por minuto
    )

    top_resultados = {}
    categorias = ['Overall', 'mayweather', 'mcgregor', 'Both', 'None']

    for categoria in categorias:
        if categoria == 'Overall':
            emojis = [e for sub in df['emoji'] for e in sub]

        else:
            emojis = [e for sub in df[df['lutador'] == categoria]['emoji'] for e in sub]
        
        contador = Counter(emojis)
        top_resultados[categoria] = contador.most_common(10)

    sentimento_por_minuto.to_csv(r'C:\Users\davi.carneiro\Desktop\Python02_EAD\06_AS\sentimento_medio_minuto.csv', index=False)
    engajamento_por_minuto.to_csv(r'C:\Users\davi.carneiro\Desktop\Python02_EAD\06_AS\engajamento_minuto.csv', index=False)

    with open('top_emojis.csv', 'w', newline='', encoding='utf-8') as arquivo: #arquivo com o top emojis
        escritor = csv.DictWriter(arquivo, fieldnames=['Grupo', 'Emoji', 'Contagem'])
        escritor.writeheader()
        for group, pairs in top_resultados.items(): #grupo é cada categoria
            for emoji, contador in pairs:
                escritor.writerow({'Grupo':group, 'Emoji': emoji, 'Contagem':contador})

    print('Analise concluida:')
    print('- Sentimento medio e engajamento por minuto salvos em csv')
    print('- Lista de emojis mais frequentes por grupo salva em csv')

    if _plotly_available:

        merged = sentimento_por_minuto.merge(engajamento_por_minuto, on='minute')
        fig = make_subplots(specs=[[{'secondary_y': True}]])
       
        #Adiciona uma barra para representar o volume de engajamento 
        fig.add_trace(go.Bar(
            x=merged['minute'],
            y=merged['engajamento'],
            name='Engajamento',
            marker_color='LightSkyBlue',
            opacity=0.6
    
        ), secondary_y=False)
        
        #Adiciona uma linha para representar o sentimento medio
        fig.add_trace(go.Scatter(

            x=merged['minute'],
            y=merged['sentimento_medio'],
            name='Sentimento Médio',
            mode= 'lines+markers',
            line= dict(color='crimson')

        ), secondary_y=True)

        fig.update_layout(
            title='Clima da Torcida: sentimento e volume por minuto',
            xaxis_title='Hora (minuto)',
            yaxis_title='Engajamento'
            
        )
        fig.update_yaxes(title_text='Número de Tweets' ,secondary_y=False)
        fig.update_yaxes(title_text='Sentimento Médio' ,secondary_y=True)

        fig.write_html(r'C:\Users\davi.carneiro\Desktop\Python02_EAD\06_AS\clima_torcida.html', include_plotlyjs='cdn')
        print('Gráfico interativo salvo como clima_torcida.html')

    else:
        print('plotly não está instalado; gráfico interativo não será gerado')

if __name__ == '__main__':
    #cria o analisador de argumentos com descrição
    parser = argparse.ArgumentParser(
        description = 'Analisa os emojis do twitter para uma luta específica'
    )
    #define um argumento opcional para o caminho csv
    parser.add_argument(
        'csv_caminho',
        nargs='?',
        default=r'C:\Users\davi.carneiro\Desktop\Python02_EAD\06_AS\tw.csv',
        help = 'Caminho para o csv  (Padrão: tw.csv)'
    )

    args = parser.parse_args()
    main(args.csv_caminho)