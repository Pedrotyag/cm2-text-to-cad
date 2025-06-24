window.testCase = {
    id: 'case-05-drop-shape-holes',
    name: '(5) Formato de Gota com Furos',
    description: 'A forma 3D é uma peça em forma de gota com dois furos circulares, um grande perto da extremidade mais larga e um pequeno perto da extremidade mais estreita.',
    prompt: 'Crie uma peça em formato de gota com 50mm de comprimento e 25mm de largura máxima, 10mm de espessura, com um furo grande de 8mm próximo à extremidade mais larga e um furo pequeno de 4mm próximo à extremidade mais estreita.',
    
    groundTruthCode: `
import cadquery as cq
import math

# Parâmetros
length = 50
max_width = 25
thickness = 10
large_hole_dia = 8
small_hole_dia = 4

# Criar formato de gota usando spline
# Pontos para definir a forma de gota
points = [
    (0, 0),                           # ponta estreita
    (length * 0.2, max_width * 0.15), # início do alargamento
    (length * 0.5, max_width * 0.4),  # meio da gota
    (length * 0.8, max_width * 0.45), # quase no final
    (length, max_width * 0.3),        # final arredondado (superior)
    (length, -max_width * 0.3),       # final arredondado (inferior)
    (length * 0.8, -max_width * 0.45), # quase no final
    (length * 0.5, -max_width * 0.4),  # meio da gota
    (length * 0.2, -max_width * 0.15), # início do alargamento
    (0, 0)                            # fechar na ponta
]

# Criar formato de gota
drop_shape = cq.Workplane("XY").polyline(points).close()

# Extrudar para criar sólido 3D
drop_solid = drop_shape.extrude(thickness)

# Criar furo grande próximo à extremidade larga
large_hole = (cq.Workplane("XY")
             .circle(large_hole_dia/2)
             .extrude(thickness + 2)
             .translate((length * 0.75, 0, 0)))

# Criar furo pequeno próximo à extremidade estreita  
small_hole = (cq.Workplane("XY")
             .circle(small_hole_dia/2)
             .extrude(thickness + 2)
             .translate((length * 0.15, 0, 0)))

# Cortar os furos da gota
result = drop_solid.cut(large_hole).cut(small_hole)
`,

    expectedFeatures: {
        volume: 9.8, // Volume aproximado em cm³
        isDropShape: true,
        hasLargeHole: true,
        hasSmallHole: true,
        holeCount: 2
    },

    timeout: 40000
}; 