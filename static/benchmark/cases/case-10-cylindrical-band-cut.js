window.testCase = {
    id: 'case-10-cylindrical-band-cut',
    name: '(10) Banda Cilíndrica com Corte',
    description: 'A forma é um anel cilíndrico oco com um setor vertical removido, lembrando um anel incompleto com uma abertura em cunha.',
    prompt: 'Crie uma banda cilíndrica oca com 30mm de diâmetro externo, 20mm de diâmetro interno, 15mm de altura, com um setor vertical de 60 graus removido (como uma fatia de pizza removida de cima a baixo).',
    
    groundTruthCode: `
import cadquery as cq
import math

# Parâmetros
outer_diameter = 30
inner_diameter = 20
height = 15
cut_angle = 60  # graus

# Criar cilindro externo
outer_cylinder = cq.Workplane("XY").cylinder(height, outer_diameter/2)

# Criar cilindro interno (para fazer a banda oca)
inner_cylinder = cq.Workplane("XY").cylinder(height + 2, inner_diameter/2)

# Fazer a banda oca
band = outer_cylinder.cut(inner_cylinder)

# Criar corte em setor usando duas caixas rotacionadas
# Simular um corte angular usando intersecção de boxes

# Criar primeira caixa de corte
box_size = outer_diameter + 10
cutting_box1 = (cq.Workplane("XY")
               .box(box_size, box_size/2, height + 4)
               .translate((box_size/4, 0, 0)))

# Criar segunda caixa de corte rotacionada
cutting_box2 = (cq.Workplane("XY")
               .box(box_size, box_size/2, height + 4)
               .translate((box_size/4, 0, 0))
               .rotate((0, 0, 0), (0, 0, 1), cut_angle))

# Criar setor de corte como intersecção das duas caixas
cutting_sector = cutting_box1.intersect(cutting_box2)

# Aplicar o corte do setor
result = band.cut(cutting_sector)
`,

    expectedFeatures: {
        volume: 4.8, // Volume aproximado em cm³
        isCylindrical: true,
        isHollow: true,
        hasSectorCut: true,
        cutAngle: 60
    },

    timeout: 40000
}; 