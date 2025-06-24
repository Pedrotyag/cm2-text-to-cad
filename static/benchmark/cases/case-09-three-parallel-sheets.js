window.testCase = {
    id: 'case-09-three-parallel-sheets',
    name: '(9) Três Chapas Paralelas',
    description: 'Três chapas retangulares idênticas posicionadas VERTICALMENTE (em pé), dispostas em paralelo e com espaçamento uniforme.',
    prompt: 'Crie três chapas retangulares idênticas de 25mm x 40mm x 3mm, dispostas VERTICALMENTE (em pé, não deitadas) e espaçadas uniformemente com 8mm entre elas.',
    
    groundTruthCode: `
import cadquery as cq

# Parâmetros
sheet_width = 25
sheet_height = 40
sheet_thickness = 3
spacing = 8  # espaçamento entre chapas

# Posições das chapas no eixo Y
y_positions = [
    -spacing - sheet_thickness/2,  # chapa 1
    0,                             # chapa 2 (centro)
    spacing + sheet_thickness/2    # chapa 3
]

# Criar primeira chapa na posição inicial
result = (cq.Workplane("XZ")  # plano vertical (largura X, altura Z)
         .rect(sheet_width, sheet_height)
         .extrude(sheet_thickness)
         .translate((0, y_positions[0], 0)))

# Adicionar segunda chapa
sheet2 = (cq.Workplane("XZ")
         .rect(sheet_width, sheet_height)
         .extrude(sheet_thickness)
         .translate((0, y_positions[1], 0)))

result = result.union(sheet2)

# Adicionar terceira chapa
sheet3 = (cq.Workplane("XZ")
         .rect(sheet_width, sheet_height)
         .extrude(sheet_thickness)
         .translate((0, y_positions[2], 0)))

result = result.union(sheet3)
`,

    expectedFeatures: {
        volume: 9.0, // Volume aproximado em cm³
        sheetCount: 3,
        isParallel: true,
        hasUniformSpacing: true
    },

    timeout: 35000
}; 