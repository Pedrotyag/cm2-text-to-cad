window.testCase = {
    id: 'case-01-cylinder-hex-hole',
    name: '(1) Cilindro com Furo Hexagonal',
    description: 'A forma 3D é um cilindro com um furo hexagonal interno, que é menor e torna a parede muito fina.',
    prompt: 'Crie um cilindro de 30mm de diâmetro e 20mm de altura com um furo hexagonal de 8mm passando pelo centro de cima a baixo.',
    
    groundTruthCode: `
import cadquery as cq

# Parâmetros
cylinder_diameter = 30
cylinder_height = 20
hex_size = 8  # distância entre faces paralelas

# Criar cilindro base
cylinder = cq.Workplane("XY").cylinder(cylinder_height, cylinder_diameter/2)

# Criar furo hexagonal passante
# Para hexágono regular: raio = distância_faces / (2 * cos(30°))
import math
hex_radius = hex_size / (2 * math.cos(math.pi/6))

hex_hole = (cq.Workplane("XY")
           .polygon(6, hex_radius)  # hexágono com raio calculado
           .extrude(cylinder_height + 2))

# Cortar o furo do cilindro
result = cylinder.cut(hex_hole)
`,

    expectedFeatures: {
        volume: 12.5, // Volume aproximado em cm³
        hasCylinder: true,
        hasHexHole: true,
        isPassingThrough: true
    },

    timeout: 30000
}; 