window.testCase = {
    id: 'case-03-half-pipe',
    name: '(3) Half-pipe',
    description: 'A forma 3D é uma estrutura oca e semicilíndrica cortada longitudinalmente, lembrando um meio-cano (half-pipe).',
    prompt: 'Crie um half-pipe (meio tubo) com 60mm de comprimento, 40mm de diâmetro externo e 4mm de espessura da parede.',
    
    groundTruthCode: `
import cadquery as cq

# Parâmetros
length = 60
outer_diameter = 40
wall_thickness = 4
inner_diameter = outer_diameter - 2 * wall_thickness

# Criar cilindro externo
outer_cylinder = cq.Workplane("XY").cylinder(length, outer_diameter/2)

# Criar cilindro interno (para fazer o tubo)
inner_cylinder = cq.Workplane("XY").cylinder(length + 2, inner_diameter/2)

# Fazer o tubo
tube = outer_cylinder.cut(inner_cylinder)

# Cortar metade para fazer o half-pipe
cutting_box = (cq.Workplane("XY")
              .box(outer_diameter + 10, outer_diameter + 10, length + 10)
              .translate((0, (outer_diameter + 10)/2, 0)))

# Resultado final
result = tube.cut(cutting_box)
`,

    expectedFeatures: {
        volume: 8.2, // Volume aproximado em cm³
        isHalfPipe: true,
        hasThickness: true,
        isHollow: true
    },

    timeout: 35000
}; 