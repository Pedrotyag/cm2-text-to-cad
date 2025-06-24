window.testCase = {
    id: 'case-04-hexagonal-plate',
    name: '(4) Placa Hexagonal',
    description: 'A forma 3D é uma placa hexagonal.',
    prompt: 'Crie uma placa hexagonal com 25mm de distância entre faces paralelas e 8mm de espessura.',
    
    groundTruthCode: `
import cadquery as cq

# Parâmetros
hex_size = 25  # distância entre faces paralelas
thickness = 8

# Criar placa hexagonal
# Para hexágono regular: raio = distância_faces / (2 * cos(30°))
import math
radius = hex_size / (2 * math.cos(math.pi/6))

result = (cq.Workplane("XY")
         .polygon(6, radius)  # hexágono regular com raio calculado
         .extrude(thickness))
`,

    expectedFeatures: {
        volume: 12.8, // Volume aproximado em cm³
        isHexagonal: true,
        isPlate: true,
        hasUniformThickness: true
    },

    timeout: 25000
}; 