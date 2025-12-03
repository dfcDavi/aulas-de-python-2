import requests
import pandas as pd
import time
import sqlite3
import datetime
import random
from bs4 import BeautifulSoup

#pip install beautifulsoap4

#camuflagem para fazer o request
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0 Safari/537.36'}

#URL base para utilizar com as páginas a serem lidas
baseURL = "https://www.adorocinema.com/filmes/melhores/"
filmes = []
data_hoje = datetime.date.today().strftime('%d-%m-%Y')
agora = datetime.datetime.now()
paginaLimite = 5
card_temp_min = 1
card_temp_max = 3
pag_temp_min = 3
pag_temp_max = 5

bancoDados = r"C:\Users\davi.carneiro\Desktop\Python02_EAD\filmes.db" #onde armazena os dados coletados
saidaCSV = f"C:/Users/davi.carneiro/Desktop/Python02_EAD/filmes_adorocinema_{data_hoje}.csv" #arquivo csv saída

#percorre cada página para coletar as informações
for pagina in range(1, paginaLimite+1):
    url = f'{baseURL}?page={pagina}' #https://www.adorocinema.com/filmes/melhores/?page=1
    print(f'coletando dados da pagina {pagina}: {url}')
    resposta = requests.get(url, headers=headers)

    soup = (BeautifulSoup(resposta.text, 'html.parser'))

    #se a pagina não responder, pula para a próxima página
    if resposta.status_code != 200:
        print(f'Erro ao carregar a pagina {pagina}. \nCodigo do erro é: {resposta.status_code}')
        continue

    cards = soup.find_all('div', class_='card entity-card entity-card-list cf')

    #percorre os cartões do site
    for card in cards:
       try:
            #capturar o titulo e link da pagina do filme
            titulo_tag = card.find('a', class_='meta-title-link')
            titulo = titulo_tag.text.strip() if titulo_tag else 'N/A'
            link = 'https://www.adorocinema.com' + titulo_tag['href'] if titulo_tag else None
            
            #capturar a nota do filme
            nota_tag = card.find('span', class_='stareval-note')
            nota = nota_tag.text.strip().replace(',','.') if nota_tag else "N/A"

            if link:
                filme_resposta = requests.get(link, headers=headers)
                filme_soup = BeautifulSoup(filme_resposta.text, 'html.parser')

                #capturar diretor do filme
                diretor_tag = filme_soup.find('div', class_='meta-body-item meta-body-direction meta-body-oneline')
                if diretor_tag:
                    #vamos higienizar o texto do diretor
                    diretor = diretor_tag.text.strip().replace('Direção:', '').replace(',', '').replace('|', '').strip()
                else:
                    diretor = 'N/A'
                diretor = diretor.replace('\n','').replace('\r','').strip

            #captura dos gêneros
            genero_block = filme_soup.find('div', class_='meta-body-info')
            if genero_block:
                generos_links = genero_block.find_all('a')
                generos = [g.text.strip() for g in generos_links]
                categoria = ', '.join(generos[:3]) if generos else 'N/A' #captura até os 3 primeiros. [2:5] seria do segundo ao quinto
            else:
                categoria = 'N/A'
            
            #captura o ano de lançamento
            ano_tag = genero_block.find('span', class_='date') if genero_block else None
            ano = ano_tag.text.strip() if ano_tag else 'N/A'
            
            #
            if titulo != 'N/A' and link != 'N/A' and nota != 'N/A':
                filmes.append(
                    {
                        'Titulo': titulo,
                        'Direcao': diretor,
                        'Nota': nota,
                        'Link': link,
                        'Ano': ano,
                        'Categoria': categoria
                    }
                )
            else:
                print('Filme incompleto ou erro na coleta de dados.')
            
            #aguardar um tempo aleatorio entre cards para não sobrecarregar o site nem revelar que somos um script de webscrapping  (vulgarmente conhecido como 'bot')
            tempo = random.uniform(card_temp_min, card_temp_max)
            time.sleep(tempo)
            print(f'Tempo de espera: {tempo}')


       except Exception as erro: 
           print(f'Erro ao processar o filme. Erro: {erro}')

    #esperar um tempo entre uma página e outra
    tempo = random.uniform(pag_temp_min, pag_temp_max)
    time.sleep(tempo)

df = pd.DataFrame(filmes)
print(df)

#Salvando os dados em um arquivo CSV
df.to_csv(saidaCSV, index=False, encoding='utf-8-sig', quotechar="'", quoting = 1)

#Conectar no banco de dados SQLite (cria se não existe)
con = sqlite3.connect(bancoDados)
cursor = con.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS filmes(
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               titulo TEXT,
               direcao TEXT,
               nota REAL,
               link TEXT,
               ano TEXT,
               categoria TEXT)''')
for filme in filmes:
    try:
        cursor.execute("INSERT INTO filmes (titulo, direcao, nota, link, ano, categoria) VALUES (?, ?, ?, ?, ?, ?)",
                       (filme['Titulo'],
                        filme['Direcao'],
                        float(filme['Nota']) if filme['Nota'] != 'N/A' else None,
                        filme['Link'],
                        filme['Ano'],
                        filme['Categoria'])
                    )

    except Exception as erro:
        print(f'Erro ao inserir o filme {filme['Titulo']} no banco de dados. Código de erro: {erro}')

con.commit()
con.close()

print('------------------------------------------')
print('Dados raspados e salvos com sucesso')
print(f'Arquivo salvo em {saidaCSV}')
print('Obrigado por usar o script de Webscrapping feito por Davi Carneiro')
print(f'Finalizado em: {agora.strftime("%H:%M:%S")}')
print('------------------------------------------')