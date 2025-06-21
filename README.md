# CM² Text-to-CAD

🚀 **Sistema Avançado de Geração de Modelos CAD 3D usando Linguagem Natural**

Um sistema revolucionário que converte descrições em linguagem natural em modelos CAD 3D profissionais usando CadQuery e Inteligência Artificial.

## ✨ Características Principais

### 🔧 Capacidades Mecânicas Avançadas
- **Componentes Profissionais**: Parafusos Phillips, rolamentos, engrenagens, molas
- **Operações CadQuery Completas**: 200+ operações disponíveis (loft, sweep, fillet, chamfer, etc.)
- **Código CadQuery Direto**: LLM tem total liberdade para gerar geometrias complexas
- **Parâmetros Nomeados**: Todos os valores são parametrizáveis e editáveis

### 🎯 Exemplos de Criação
```
"Crie um parafuso Phillips M6x25 com cabeça cilíndrica e fenda em cruz"
→ Gera parafuso completo com todas as características mecânicas

"Crie um rolamento 6200 com esferas distribuídas"
→ Gera rolamento completo com anéis e esferas

"Crie uma engrenagem com 20 dentes"
→ Gera engrenagem com perfil de involuta
```

### 🏗️ Arquitetura Modular
- **Planning Module**: Interface com Gemini AI para interpretação
- **Executor**: Execução segura de código CadQuery
- **PIG Manager**: Grafo de intenções paramétricas
- **3D Viewer**: Visualização em tempo real
- **Export System**: Múltiplos formatos (STEP, STL, IGES)

## 🚀 Instalação Rápida

### Pré-requisitos
- Python 3.10+
- Node.js 18+
- Chave API do Google Gemini

### 1. Clone o Repositório
```bash
git clone https://github.com/seu-usuario/cm2-text-to-cad.git
cd cm2-text-to-cad
```

### 2. Configuração do Backend
```bash
# Criar ambiente virtual
python -m venv env
source env/bin/activate  # Linux/Mac
# ou
env\Scripts\activate     # Windows

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com sua GEMINI_API_KEY
```

### 3. Configuração do Frontend
```bash
cd frontend
npm install
npm run build
cd ..
```

### 4. Executar o Sistema
```bash
python main.py
```

Acesse: `http://localhost:8000`

## 🎮 Como Usar

### Interface Web
1. **Digite sua solicitação** em linguagem natural
2. **Visualize o modelo 3D** gerado em tempo real
3. **Edite parâmetros** dinamicamente
4. **Exporte** em formatos profissionais

### Exemplos de Comandos
```
✅ "Crie um cilindro com raio 10 e altura 20"
✅ "Faça um parafuso com cabeça hexagonal"
✅ "Crie uma caixa com furos nas laterais"
✅ "Gere um rolamento de esferas 6200"
✅ "Faça uma engrenagem com 24 dentes"
```

## 🔧 Tecnologias

### Backend
- **Python 3.10+**: Linguagem principal
- **FastAPI**: Framework web assíncrono
- **CadQuery**: Biblioteca CAD paramétrica
- **Google Gemini**: LLM para interpretação
- **Pydantic**: Validação de dados

### Frontend
- **HTML5/CSS3/JavaScript**: Interface moderna
- **Three.js**: Renderização 3D
- **WebSocket**: Comunicação em tempo real
- **Responsive Design**: Adaptável a qualquer dispositivo

### Formatos Suportados
- **STEP**: Padrão industrial
- **STL**: Impressão 3D
- **IGES**: Intercâmbio CAD
- **JSON**: Dados paramétricos

## 📁 Estrutura do Projeto

```
cm2-text-to-cad/
├── src/                    # Código fonte backend
│   ├── core/              # Módulos principais
│   │   ├── planning_module.py    # Interface Gemini AI
│   │   ├── executor.py           # Execução CadQuery
│   │   ├── pig_manager.py        # Grafo paramétrico
│   │   └── orchestrator.py       # Orquestração
│   ├── models/            # Modelos de dados
│   └── utils/             # Utilitários
├── frontend/              # Interface web
│   ├── index.html         # Página principal
│   ├── script.js          # Lógica frontend
│   └── style.css          # Estilos
├── generated_codes/       # Códigos CadQuery gerados
├── gemini_responses/      # Respostas do AI
├── requirements.txt       # Dependências Python
├── main.py               # Servidor principal
└── README.md             # Esta documentação
```

## 🌟 Exemplos Avançados

### Parafuso Phillips M6x25
```python
# Código CadQuery gerado automaticamente
import cadquery as cq

# Parâmetros
head_diameter = 10.0
head_height = 4.0
body_diameter = 6.0
body_length = 21.0
phillips_width = 1.2
phillips_depth = 2.0

# Criar cabeça
screw_head = cq.Workplane('XY').cylinder(head_height, head_diameter/2)

# Criar fenda Phillips
slot1 = cq.Workplane('XY').rect(phillips_width, phillips_depth*2).extrude(phillips_depth)
slot2 = cq.Workplane('XY').rect(phillips_depth*2, phillips_width).extrude(phillips_depth)
phillips_cutter = slot1.union(slot2)

# Cortar fenda na cabeça
screw_head = screw_head.cut(phillips_cutter.translate((0, 0, head_height - phillips_depth/2)))

# Criar corpo
screw_body = cq.Workplane('XY').cylinder(body_length, body_diameter/2).translate((0, 0, -body_length/2))

# Resultado final
result = screw_head.union(screw_body).faces('>Z').chamfer(0.5)
```

### Rolamento 6200
```python
# Componentes do rolamento
bearing_od = 30.0
bearing_id = 10.0  
bearing_width = 9.0
ball_diameter = 4.0
num_balls = 8

# Anel externo
outer_ring = (cq.Workplane('XY')
              .cylinder(bearing_width, bearing_od/2)
              .cylinder(bearing_width, (bearing_od - ball_diameter)/2, combine=False))

# Esferas distribuídas
pitch_radius = (bearing_od - bearing_id - ball_diameter) / 2 + bearing_id/2
balls = (cq.Workplane('XY')
         .center(pitch_radius, 0)
         .sphere(ball_diameter/2)
         .polarArray(radius=0, startAngle=0, angle=360, count=num_balls))

result = outer_ring.union(inner_ring).union(balls)
```

## 🔬 Arquitetura Técnica

### Fluxo de Processamento
1. **Input**: Linguagem natural do usuário
2. **Planning**: Gemini AI interpreta e gera plano
3. **Execution**: CadQuery executa código 3D
4. **Visualization**: Three.js renderiza modelo
5. **Export**: Múltiplos formatos disponíveis

### Segurança
- Execução em sandbox isolado
- Validação de código gerado
- Timeout de execução
- Sanitização de inputs

## 🤝 Contribuindo

### Desenvolvimento
1. Fork o projeto
2. Crie uma branch para sua feature
3. Faça commit das mudanças
4. Abra um Pull Request

### Reportar Bugs
Use as [Issues do GitHub](https://github.com/seu-usuario/cm2-text-to-cad/issues) para reportar problemas.

## 📄 Licença

Este projeto está licenciado sob a MIT License - veja o arquivo [LICENSE](LICENSE) para detalhes.

## 🙏 Agradecimentos

- **CadQuery**: Biblioteca CAD paramétrica em Python
- **Google Gemini**: Modelo de linguagem avançado
- **Three.js**: Renderização 3D no navegador
- **FastAPI**: Framework web moderno

## 📞 Contato

- **GitHub**: [seu-usuario](https://github.com/seu-usuario)
- **Email**: seu-email@exemplo.com

---

⭐ **Se este projeto foi útil, considere dar uma estrela no GitHub!** 