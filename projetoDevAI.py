import tkinter as tk
from tkinter import ttk, messagebox
import requests
import boto3
from botocore.exceptions import ClientError

# Configuração do Bedrock
client = boto3.client("bedrock-runtime", region_name="us-east-1")
model_id = "amazon.titan-text-premier-v1:0"
endereco_texto = ""

# Função para consultar endereço a partir do CEP
def consultar_endereco(cep):
    global endereco_texto
    try:
        url = f"https://viacep.com.br/ws/{cep}/json/"
        response = requests.get(url)
        if response.status_code == 200:
            endereco = response.json()
            if "erro" in endereco:
                endereco_texto = "CEP não encontrado. Verifique e tente novamente."
            else:
                endereco_texto = (
                    f"Endereço encontrado:\n"
                    f"Logradouro: {endereco.get('logradouro', 'N/A')}\n"
                    f"Bairro: {endereco.get('bairro', 'N/A')}\n"
                    f"Cidade: {endereco.get('localidade', 'N/A')}\n"
                    f"Estado: {endereco.get('uf', 'N/A')}\n"
                )
        else:
            endereco_texto = f"Erro ao consultar o endereço. Código de status: {response.status_code}"
    except Exception as e:
        endereco_texto = f"Ocorreu um erro ao consultar o endereço: {e}"



# Função para listar as marcas de veículos
def listar_marcas(tipo_veiculo=None):
    try:
        url = f"https://parallelum.com.br/fipe/api/v1/{tipo_veiculo}/marcas" if tipo_veiculo else "https://parallelum.com.br/fipe/api/v1/carros/marcas"

        response = requests.get(url)
        if response.status_code == 200:
            marcas = response.json()
            return marcas
        else:
            messagebox.showerror("Erro", f"Erro ao consultar a API. Código de status: {response.status_code}")
    except Exception as e:
        messagebox.showerror("Erro", f"Ocorreu um erro ao consultar as marcas: {e}")
    return []

# Função para listar os modelos de um veículo baseado na marca
def listar_modelos(tipo_veiculo, codigo_marca):
    try:
        url = f"https://parallelum.com.br/fipe/api/v1/{tipo_veiculo}/marcas/{codigo_marca}/modelos"
        response = requests.get(url)
        if response.status_code == 200:
            modelos = response.json().get('modelos', [])
            return modelos
        else:
            messagebox.showerror("Erro", f"Erro ao consultar os modelos. Código de status: {response.status_code}")
    except Exception as e:
        messagebox.showerror("Erro", f"Ocorreu um erro ao consultar os modelos: {e}")
    return []

# Função para listar os anos de um modelo
def listar_anos(tipo_veiculo, codigo_marca, codigo_modelo):
    try:
        url = f"https://parallelum.com.br/fipe/api/v1/{tipo_veiculo}/marcas/{codigo_marca}/modelos/{codigo_modelo}/anos"
        response = requests.get(url)
        if response.status_code == 200:
            anos = response.json()
            return anos
        else:
            messagebox.showerror("Erro", f"Erro ao consultar os anos. Código de status: {response.status_code}")
    except Exception as e:
        messagebox.showerror("Erro", f"Ocorreu um erro ao consultar os anos: {e}")
    return []

def listar_precos(tipo_veiculo, codigo_marca, codigo_modelo, codigo_ano, cep):
    global endereco_texto
    try:
        url = f"https://parallelum.com.br/fipe/api/v1/{tipo_veiculo}/marcas/{codigo_marca}/modelos/{codigo_modelo}/anos/{codigo_ano}"
        response = requests.get(url)
        if response.status_code == 200:
            preco = response.json()
            if isinstance(preco, dict) and 'Valor' in preco:
                resultado = (
                    f"Informações do veículo:\n"
                    f"Preço: {preco['Valor']}\n"
                    f"Marca: {preco['Marca']}\n"
                    f"Modelo: {preco['Modelo']}\n"
                    f"Ano Modelo: {preco['AnoModelo']}\n"
                    f"Combustível: {preco['Combustivel']}\n"
                    f"Código FIPE: {preco['CodigoFipe']}\n"
                    f"Mês de referência: {preco['MesReferencia']}\n"
                )
                servicos_bedrock = buscar_servicos_bedrock(cep, preco['Modelo'])
                resultado_completo = endereco_texto + "\n\n" + resultado + "\nServiços automotivos sugeridos na região do CEP:\n" + servicos_bedrock
                return resultado_completo
            else:
                return "Estrutura de dados inesperada para preços."
        else:
            return f"Erro ao consultar os preços. Código de status: {response.status_code}"
    except Exception as e:
        return f"Ocorreu um erro ao consultar os preços: {e}"

def selecionar_ano(event):
    tipo_veiculo = tipo_veiculo_var.get().strip().lower()
    marca_selecionada = marca_menu.get()
    modelo_selecionado = modelo_menu.get()
    ano_selecionado = ano_menu.get()
    cep = cep_entry.get().strip()
    codigo_marca = next((marca['codigo'] for marca in listar_marcas(tipo_veiculo) if marca['nome'] == marca_selecionada), None)
    codigo_modelo = next((modelo['codigo'] for modelo in listar_modelos(tipo_veiculo, codigo_marca) if modelo['nome'] == modelo_selecionado), None)
    codigo_ano = next((ano['codigo'] for ano in listar_anos(tipo_veiculo, codigo_marca, codigo_modelo) if ano['nome'] == ano_selecionado), None)
    
    if codigo_ano:
        resultado = listar_precos(tipo_veiculo, codigo_marca, codigo_modelo, codigo_ano, cep)
        if resultado:
            resultado_text.insert(tk.END, resultado + "\n\n")


# Função para buscar serviços automotivos via Bedrock
def buscar_servicos_bedrock(cep, modelo_veiculo):
    prompt = (f"Eu possuo um veículo do modelo {modelo_veiculo}. "
              f"Estou localizado no CEP {cep}, no Brasil. "
              "Por favor, responda em português e liste 10 empresas de serviços automotivos disponíveis na região com endereço e telefoneo.")
    conversation = [{"role": "user", "content": [{"text": prompt}]}]
    try:
        response = client.converse(
            modelId=model_id,
            messages=conversation,
            inferenceConfig={"maxTokens": 1000, "temperature": 0.5, "topP": 0.9},
        )
        response_text = response["output"]["message"]["content"][0]["text"]
        return response_text
    except (ClientError, Exception) as e:
        return f"Erro ao buscar serviços automotivos via Bedrock: {e}"

def iniciar_consulta():
    global endereco_texto
    tipo_veiculo = tipo_veiculo_var.get().strip().lower()
    cep = cep_entry.get().strip()

    if not cep.isdigit() or len(cep) != 8:
        messagebox.showerror("Erro", "CEP inválido.")
        return

    consultar_endereco(cep)
    if "CEP não encontrado" in endereco_texto or "Erro ao consultar" in endereco_texto:
        messagebox.showerror("Erro", endereco_texto)
        return

    resultado_text.delete(1.0, tk.END)
    resultado_text.insert(tk.END, endereco_texto + "\n\n")

    marcas = listar_marcas(tipo_veiculo)
    if marcas:
        marca_nomes = [marca['nome'] for marca in marcas]
        marca_menu['values'] = marca_nomes


def selecionar_marca(event):
    tipo_veiculo = tipo_veiculo_var.get().strip().lower()
    marca_selecionada = marca_menu.get()
    codigo_marca = next((marca['codigo'] for marca in listar_marcas(tipo_veiculo) if marca['nome'] == marca_selecionada), None)
    
    if codigo_marca:
        modelos = listar_modelos(tipo_veiculo, codigo_marca)
        if modelos:
            modelo_nomes = [modelo['nome'] for modelo in modelos]
            modelo_menu['values'] = modelo_nomes

def selecionar_modelo(event):
    tipo_veiculo = tipo_veiculo_var.get().strip().lower()
    marca_selecionada = marca_menu.get()
    modelo_selecionado = modelo_menu.get()
    codigo_marca = next((marca['codigo'] for marca in listar_marcas(tipo_veiculo) if marca['nome'] == marca_selecionada), None)
    codigo_modelo = next((modelo['codigo'] for modelo in listar_modelos(tipo_veiculo, codigo_marca) if modelo['nome'] == modelo_selecionado), None)
    
    if codigo_modelo:
        anos = listar_anos(tipo_veiculo, codigo_marca, codigo_modelo)
        if anos:
            ano_desc = [ano['nome'] for ano in anos]
            ano_menu['values'] = ano_desc

def selecionar_ano(event):
    tipo_veiculo = tipo_veiculo_var.get().strip().lower()
    marca_selecionada = marca_menu.get()
    modelo_selecionado = modelo_menu.get()
    ano_selecionado = ano_menu.get()
    cep = cep_entry.get().strip()
    codigo_marca = next((marca['codigo'] for marca in listar_marcas(tipo_veiculo) if marca['nome'] == marca_selecionada), None)
    codigo_modelo = next((modelo['codigo'] for modelo in listar_modelos(tipo_veiculo, codigo_marca) if modelo['nome'] == modelo_selecionado), None)
    codigo_ano = next((ano['codigo'] for ano in listar_anos(tipo_veiculo, codigo_marca, codigo_modelo) if ano['nome'] == ano_selecionado), None)
    
    if codigo_ano:
        resultado = listar_precos(tipo_veiculo, codigo_marca, codigo_modelo, codigo_ano, cep)
        resultado_text.delete(1.0, tk.END)
        resultado_text.insert(tk.END, resultado)

# Criação da interface gráfica
app = tk.Tk()
app.title("Consulta FIPE")
app.geometry("600x400")  # Ajusta o tamanho da janela

# Permite que a janela seja redimensionada e os widgets se ajustem 
app.grid_columnconfigure(0, weight=1) 
app.grid_columnconfigure(1, weight=1) 
app.grid_rowconfigure(6, weight=1)


# Campos de entrada e botões
ttk.Label(app, text="CEP:").grid(row=0, column=0, padx=10, pady=10, sticky='ew')
cep_entry = ttk.Entry(app)
cep_entry.grid(row=0, column=1, padx=10, pady=10, sticky='ew')

ttk.Label(app, text="Tipo de Veículo:").grid(row=1, column=0, padx=10, pady=10, sticky='ew')
tipo_veiculo_var = tk.StringVar()
tipo_veiculo_var.set("carros")  # Definindo o valor padrão

frame_tipo_veiculo = ttk.Frame(app)
frame_tipo_veiculo.grid(row=1, column=1, padx=10, pady=10, sticky='ew')

tipos_veiculo = ["carros", "motos", "caminhoes"]
for tipo in tipos_veiculo:
    ttk.Radiobutton(frame_tipo_veiculo, text=tipo.capitalize(), variable=tipo_veiculo_var, value=tipo).pack(side=tk.LEFT, padx=5)

ttk.Button(app, text="Start", command=iniciar_consulta).grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky='ew')

marca_label = ttk.Label(app, text="Marca:")
marca_label.grid(row=3, column=0, padx=10, pady=10, sticky='ew')
marca_menu = ttk.Combobox(app, width=20)
marca_menu.grid(row=3, column=1, padx=10, pady=10, sticky='ew')

modelo_label = ttk.Label(app, text="Modelo:")
modelo_label.grid(row=4, column=0, padx=10, pady=10, sticky='ew')
modelo_menu = ttk.Combobox(app, width=20)
modelo_menu.grid(row=4, column=1, padx=10, pady=10, sticky='ew')

ano_label = ttk.Label(app, text="Ano:")
ano_label.grid(row=5, column=0, padx=10, pady=10, sticky='ew')
ano_menu = ttk.Combobox(app, width=20)
ano_menu.grid(row=5, column=1, padx=10, pady=10, sticky='ew')

# Aumenta a área de retorno do texto
resultado_text = tk.Text(app, height=10, width=60)
resultado_text.grid(row=6, column=0, columnspan=2, padx=10, pady=10, sticky='nsew')


marca_menu.bind("<<ComboboxSelected>>", selecionar_marca)
modelo_menu.bind("<<ComboboxSelected>>", selecionar_modelo)
ano_menu.bind("<<ComboboxSelected>>", selecionar_ano)

app.mainloop()
