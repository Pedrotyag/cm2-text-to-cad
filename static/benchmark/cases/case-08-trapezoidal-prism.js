window.testCase = {
    id: 'case-08-trapezoidal-prism',
    name: '(8) Prisma Trapezoidal',
    description: 'A forma 3D é um prisma fino trapezoidal deitado no plano XY.',
    prompt: 'Crie um prisma trapezoidal FINO como uma placa, com base maior de 30mm, base menor de 15mm, altura do trapézio de 20mm e espessura de apenas 3mm, deitado no plano XY.',
    
    groundTruthCode: `
import cadquery as cq

# Parâmetros para prisma FINO (como uma placa)
base_maior = 30
base_menor = 15
altura_trapezio = 20
espessura = 3  # FINO como uma placa

# Criar trapézio usando pontos
# Trapézio simétrico centrado na origem
points = [
    (-base_maior/2, -altura_trapezio/2),  # base inferior esquerda
    (base_maior/2, -altura_trapezio/2),   # base inferior direita
    (base_menor/2, altura_trapezio/2),    # base superior direita
    (-base_menor/2, altura_trapezio/2),   # base superior esquerda
    (-base_maior/2, -altura_trapezio/2)   # fechar o contorno
]

# Criar o prisma trapezoidal FINO deitado no plano XY
result = (cq.Workplane("XY")
         .polyline(points)
         .close()
         .extrude(espessura))  # Extrusão fina no eixo Z
`,

    expectedFeatures: {
        volume: 5.4, // Volume aproximado em cm³
        isTrapezoidal: true,
        isPrism: true,
        hasSymmetry: true
    },

    timeout: 30000
}; 