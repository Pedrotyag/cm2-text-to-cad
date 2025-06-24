window.testCase = {
    id: 'case-07-four-cylinders-corners',
    name: '(7) Quatro Cilindros nos Cantos',
    description: 'A forma é composta por quatro cilindros verticais, aproximadamente do mesmo tamanho, distribuídos de forma desigual nos quatro cantos.',
    prompt: 'Crie quatro cilindros verticais idênticos com 8mm de diâmetro e 20mm de altura, distribuídos DE FORMA DESIGUAL nos quatro cantos como os pés de uma mesa irregular.',
    
    groundTruthCode: `
import cadquery as cq

# Parâmetros
cylinder_diameter = 8
cylinder_height = 20
spacing = 30  # distância entre centros dos cilindros

# Posições dos cilindros nos cantos (DISTRIBUIÇÃO DESIGUAL)
# Como os pés de uma mesa com distribuição irregular
positions = [
    (18, 12),     # canto superior direito - mais afastado
    (-10, 14),    # canto superior esquerdo - assimétrico  
    (-16, -8),    # canto inferior esquerdo - posição irregular
    (20, -15)     # canto inferior direito - desbalanceado
]

# Criar primeiro cilindro na posição correta
result = (cq.Workplane("XY")
         .center(positions[0][0], positions[0][1])
         .cylinder(cylinder_height, cylinder_diameter/2))

# Adicionar os outros três cilindros
for pos in positions[1:]:
    cylinder = (cq.Workplane("XY")
               .center(pos[0], pos[1])
               .cylinder(cylinder_height, cylinder_diameter/2))
    result = result.union(cylinder)
`,

    expectedFeatures: {
        volume: 8.0, // Volume aproximado em cm³
        cylinderCount: 4,
        isSymmetric: false,
        hasUniformSpacing: false
    },

    timeout: 35000
}; 