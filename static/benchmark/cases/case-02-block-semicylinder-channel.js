window.testCase = {
    id: 'case-02-block-semicylinder-channel',
    name: '(2) Bloco com Canal Semicilíndrico',
    description: 'A forma 3D é um bloco retangular com um recorte semicilíndrico localizado em seu centro, formando um canal em forma de U.',
    prompt: 'Crie um bloco de 60x40x20mm com um canal semicilíndrico de 8mm de raio passando pelo centro na direção longitudinal. Adicione 4 furos de 4mm nos cantos para fixação.',
    
    groundTruthCode: `
import cadquery as cq

# Parâmetros
block_length = 60
block_width = 40
block_height = 20
channel_radius = 8
hole_diameter = 4
corner_offset = 8

# Criar bloco base
block = cq.Workplane("XY").box(block_length, block_width, block_height)

# Criar canal semicilíndrico
# Criar cilindro horizontal para formar o canal
channel = (cq.Workplane("YZ")
          .circle(channel_radius)
          .extrude(block_length + 2)
          .translate((0, 0, block_height/2)))

# Cortar o canal do bloco
result = block.cut(channel)

# Adicionar furos nos cantos
hole_positions = [
    (block_length/2 - corner_offset, block_width/2 - corner_offset),
    (-block_length/2 + corner_offset, block_width/2 - corner_offset),
    (block_length/2 - corner_offset, -block_width/2 + corner_offset),
    (-block_length/2 + corner_offset, -block_width/2 + corner_offset)
]

for x, y in hole_positions:
    hole = cq.Workplane("XY").circle(hole_diameter/2).extrude(block_height + 2)
    hole = hole.translate((x, y, 0))
    result = result.cut(hole)
`,

    expectedFeatures: {
        volume: 38.5, // Volume aproximado em cm³
        hasChannel: true,
        hasCornerHoles: true,
        holeCount: 4
    },

    timeout: 45000
}; 