window.testCase = {
    id: 'case-06-cylinder-square-hole',
    name: '(6) Cilindro com Furo Quadrado',
    description: 'A forma é um cilindro com um furo quadrado centralizado no topo, que se estende de cima a baixo.',
    prompt: 'Crie um cilindro de 25mm de diâmetro e 15mm de altura com um furo quadrado de 6mm x 6mm passando do topo até a base.',
    
    groundTruthCode: `
import cadquery as cq

# Parâmetros
cylinder_diameter = 25
cylinder_height = 15
square_size = 6

# Criar cilindro base
cylinder = cq.Workplane("XY").cylinder(cylinder_height, cylinder_diameter/2)

# Criar furo quadrado passante centralizado
# O furo deve atravessar completamente o cilindro de cima a baixo
square_hole = (cq.Workplane("XY")
              .rect(square_size, square_size)
              .extrude(cylinder_height + 4)  # Extra para garantir corte completo
              .translate((0, 0, -2)))  # Posicionar para atravessar completamente

# Cortar o furo do cilindro
result = cylinder.cut(square_hole)
`,

    expectedFeatures: {
        volume: 6.8, // Volume aproximado em cm³
        hasCylinder: true,
        hasSquareHole: true,
        isPassingThrough: true
    },

    timeout: 30000
}; 