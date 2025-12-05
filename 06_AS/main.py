import argparse #permite criar e gerenciar argumentos de linha de comando (Ex.: recebe um parâmetro e executa um script)
import csv
from collections import Counter #estrutura de dados que conta ocorrências de itens (conta palavras, números, etc.)
from datetime import datetime
import re #biblioteca de expressões regulares (usada para buscar e manipular padrões em strings)
import os 
import pandas as pd
import google.generativeai as genai

genai.configure(api_key='AIzaSyBTPYWMbR4hv18JLeP7JvGPuvjLbewX5nU')

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

def gerar_analise_ia(df, sentimento_por_minuto, eng_por_may, eng_por_mcg):

    prompt = f"""

        Você é um analista esportivo com foco em comportamento de torcida.
        Com base nos dados abaixo, gere uma análise textual clara, objetiva e em português:

        ### Dados

        - Média de sentimento por minuto (Resumo estatístico):
        {sentimento_por_minuto['sentimento_medio'].describe().to_string()}

        - Engajamento Mayweather total: {eng_por_may.sum()}
        - Engajamento McGregor total: {eng_por_mcg.sum()}

        - Tweets analisados: {len(df)}
        - Tweets mencionando Mayweather: {sum(df['lutador'] == 'mayweather')}
        - Tweets mencionando McGregor: {sum(df['lutador'] == 'mcgregor')}
        - Tweets mencionando ambos: {sum(df['lutador'] == 'Both')}
        - Tweets sem lutador indentificado: {sum(df['lutador'] == 'None')}

        ### Tarefa

        Escreve uma análise narrativa que responda:

        - Qual torcida pareceu mais engajado no total?
        - Houve momento de pico de sentimento?
        - A torcida estava mais positiva, neutra ou negativa no geral?
        - Existe relação visível entre sentimento e engajamento?

        Formato: **Texto corrido de 1-3 parágrafos.** 

        Estilo de escrita: **Linguagem jovem e descolada*, bem formatado em html e css*

    """
    modelo = genai.GenerativeModel('gemini-2.5-flash')
    resposta = modelo.generate_content(prompt)

    return resposta.text

def main(csv_caminho: str) -> None:
    # if not os.path.exists(csv_caminho):
    #     raise FileNotFoundError(f"Arquivo csv não encontrado: {csv_caminho}")
    
    if not os.path.exists(csv_caminho):
        pasta = os.path.dirname(csv_caminho)
        if not pasta:
            pasta = os.getcwd()
        print(f"Arquivo csv não encontrado: {csv_caminho}")

        if os.path.isdir(pasta):
            print(f'Arquivo encontrado na pasta: {csv_caminho}')

            for nome in os.listdir(pasta):
                caminho_completo  = os.path.join(pasta, nome)
                if os.path.isfile(caminho_completo):
                    print(" -", nome)
            else:
                print(f'A pasta informada não existe: {pasta}')
            return
    
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

    engajamento_por_minuto_lutador = (

        #unstack cria colunas mayweather e mcgregor
        df[df['lutador'].isin(['mayweather', 'mcgregor'])].groupby(['minute','lutador']).size().unstack(fill_value=0).reset_index()

    )

    #Garante que as colunas existam mesmo se um lutador não aparecer
    for coluna in ['mayweather', 'mcgregor']:
     if coluna not in engajamento_por_minuto_lutador.columns:
         engajamento_por_minuto_lutador[coluna] = 0

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

        merged = sentimento_por_minuto.merge(engajamento_por_minuto_lutador, on='minute', how='left').fillna(0)

        fig = make_subplots(specs=[[{'secondary_y': True}]])

        fig.add_trace(

            go.Bar(

                x=merged['minute'],
                y=merged['mayweather'],
                name='Engajamento Mayweather',
                opacity=0.6

            ), secondary_y=False
        )

        fig.add_trace(

            go.Bar(

                x=merged['minute'],
                y=merged['mcgregor'],
                name='Engajamento McGregor',
                opacity=0.6

            ), secondary_y=False
        )

        fig.add_trace(

            go.Scatter(
                x=merged['minute'],
                y=merged['sentimento_medio'],
                name='Sentimento Médio',
                mode='lines+markers'

            ), secondary_y=True

        )

        fig.update_layout(

            title='Clima da Torcida: sentimento e volume por minuto',
            xaxis_title='Hora (minuto)',
            yaxis_title='Engajamento',
            barmode='stack'
        )

        fig.update_yaxes(title_text='Número de Tweets' ,secondary_y=False)
        fig.update_yaxes(title_text='Sentimento Médio' ,secondary_y=True)

        fig.write_html(r'C:\Users\davi.carneiro\Desktop\Python02_EAD\06_AS\clima_torcida.html', include_plotlyjs='cdn')
        print('Gráfico interativo salvo como clima_torcida.html')

        engajamento_por_may = merged['mayweather']
        engajamento_por_mcg = merged['mcgregor']

        analise_textual = gerar_analise_ia(df, sentimento_por_minuto, engajamento_por_may, engajamento_por_mcg)

        caminho_html = r'C:\Users\davi.carneiro\Desktop\Python02_EAD\06_AS\clima_torcida.html'

        with open(caminho_html, 'r', encoding='utf-8') as arquivo:
            conteudo = arquivo.read()
            conteudo += f""" 

                <hr>
                <h2>Análise Automatizada (IA - Gemini)</h2>
                <div style='font-size:18px; line-height:1.6; max-width:900px;'>
                    {analise_textual}
                </div>

            """

            with open(caminho_html, 'w', encoding='utf-8') as arquivo:
                arquivo.write(conteudo)
            print("Analise com ia adicionada ao arquivo")

        # merged = sentimento_por_minuto.merge(engajamento_por_minuto, on='minute')
        # fig = make_subplots(specs=[[{'secondary_y': True}]])
       
        # #Adiciona uma barra para representar o volume de engajamento 
        # fig.add_trace(go.Bar(
        #     x=merged['minute'],
        #     y=merged['engajamento'],
        #     name='Engajamento',
        #     marker_color='LightSkyBlue',
        #     opacity=0.6
    
        # ), secondary_y=False)
        
        # #Adiciona uma linha para representar o sentimento medio
        # fig.add_trace(go.Scatter(

        #     x=merged['minute'],
        #     y=merged['sentimento_medio'],
        #     name='Sentimento Médio',
        #     mode= 'lines+markers',
        #     line= dict(color='crimson')

        # ), secondary_y=True)

        # fig.update_layout(
        #     title='Clima da Torcida: sentimento e volume por minuto',
        #     xaxis_title='Hora (minuto)',
        #     yaxis_title='Engajamento'
            
        # )
        # fig.update_yaxes(title_text='Número de Tweets' ,secondary_y=False)
        # fig.update_yaxes(title_text='Sentimento Médio' ,secondary_y=True)

        # fig.write_html(r'C:\Users\davi.carneiro\Desktop\Python02_EAD\06_AS\clima_torcida.html', include_plotlyjs='cdn')
        # print('Gráfico interativo salvo como clima_torcida.html')

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