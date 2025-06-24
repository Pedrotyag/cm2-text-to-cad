// Sistema de renderização 3D para benchmark - USA O MESMO ThreeSetup do index.html
class BenchmarkThreeRenderer {
    constructor() {
        this.threeInstances = new Map();
    }

    // Inicializar viewport 3D usando ThreeSetup EXATO do index.html
    initViewport(containerId, type = 'llm') {
        console.log(`🎯 Inicializando viewport ${containerId} usando ThreeSetup`);
        
        // Verificar se já existe
        if (this.threeInstances.has(containerId)) {
            console.log(`♻️ Viewport ${containerId} já existe, reutilizando`);
            return this.threeInstances.get(containerId);
        }

        // Verificar se elemento existe
        const container = document.getElementById(containerId);
        if (!container) {
            console.warn(`⚠️ Container ${containerId} não encontrado`);
            return null;
        }

        try {
            // Criar nova instância do ThreeSetup (IGUAL ao index.html)
            const threeInstance = new ThreeSetup(containerId);
            threeInstance.init();
            
            // Armazenar a instância
            this.threeInstances.set(containerId, threeInstance);
            
            console.log(`✅ Viewport ${containerId} inicializado com ThreeSetup`);
            return threeInstance;
            
        } catch (error) {
            console.error(`❌ Erro ao inicializar viewport ${containerId}:`, error);
            return null;
        }
    }
    
    // Limpar instâncias não utilizadas para evitar warnings WebGL
    cleanupUnusedViewports() {
        for (const [containerId, instance] of this.threeInstances.entries()) {
            const container = document.getElementById(containerId);
            if (!container) {
                console.log(`🧹 Limpando viewport órfão: ${containerId}`);
                if (instance && instance.dispose) {
                    instance.dispose();
                }
                this.threeInstances.delete(containerId);
            }
        }
    }

    // Carregar modelo específico para cada caso de teste usando ThreeSetup
    loadGroundTruthModel(containerId, testCaseId) {
        const threeInstance = this.threeInstances.get(containerId);
        if (!threeInstance) {
            console.error(`❌ ThreeSetup ${containerId} não encontrado`);
            return;
        }

        console.log(`🎯 Carregando modelo Ground Truth para ${testCaseId}`);

        // Esconder o overlay (IGUAL ao index.html)
        this.hideViewportOverlay(containerId);

        // Criar dados do modelo específico
        const modelData = this.createModelDataForTestCase(testCaseId);
        
        // Usar o método updateModel do ThreeSetup (IGUAL ao index.html)
        threeInstance.updateModel(modelData);
        
        console.log(`✅ Modelo Ground Truth carregado para ${testCaseId}`);
    }

    // Esconder overlay (IGUAL ao método do app.js)
    hideViewportOverlay(containerId) {
        const overlay = document.getElementById(`${containerId.replace('viewport', 'overlay')}`);
        if (overlay) {
            overlay.style.display = 'none';
            console.log(`🙈 Overlay removido de ${containerId}`);
        }
    }
    
    // Criar dados de modelo específicos (formato que ThreeSetup.updateModel espera)
    createModelDataForTestCase(testCaseId) {
        console.log(`🎨 Criando dados de modelo para ${testCaseId}`);
        
        // Como não temos dados STL reais, vamos simular dados para placeholder
        // O ThreeSetup.updateModel vai usar createPlaceholderModel() quando não há mesh_data
        const modelData = {
            mesh_data: null, // Forçar uso do placeholder
            bounding_box: {
                min: [-30, -30, -30],
                max: [30, 30, 30]
            },
            parameters: this.getParametersForTestCase(testCaseId),
            test_case_id: testCaseId // Adicionar ID para identificar
        };
        
        return modelData;
    }
    
    // Obter parâmetros específicos para cada caso de teste  
    getParametersForTestCase(testCaseId) {
        switch (testCaseId) {
            case 'case-01-cylinder-hex-hole':
                return {
                    radius: 25,
                    height: 40,
                    hole_diameter: 8,
                    type: 'cylinder'
                };
                
            case 'case-02-block-semicylinder-channel':
                return {
                    length: 60,
                    width: 40,
                    height: 20,
                    channel_radius: 8,
                    type: 'block'
                };
                
            case 'case-03-half-pipe':
                return {
                    radius: 20,
                    length: 80,
                    type: 'pipe'
                };
                
            case 'case-04-hexagonal-plate':
                return {
                    radius: 30,
                    height: 5,
                    sides: 6,
                    type: 'hexagon'
                };
                
            case 'case-05-drop-shape-holes':
                return {
                    radius: 25,
                    holes_count: 3,
                    hole_diameter: 3,
                    type: 'drop'
                };
                
            case 'case-06-cylinder-square-hole':
                return {
                    radius: 12.5,
                    height: 15,
                    hole_size: 6,
                    type: 'cylinder'
                };
                
            case 'case-07-four-cylinders-corners':
                return {
                    radius: 4,
                    height: 20,
                    spacing: 30,
                    count: 4,
                    type: 'cylinders'
                };
                
            case 'case-08-trapezoidal-prism':
                return {
                    base_major: 30,
                    base_minor: 15,
                    height: 20,
                    thickness: 3,  // Atualizado para espessura FINA
                    type: 'trapezoid'
                };
                
            case 'case-09-three-parallel-sheets':
                return {
                    width: 25,
                    height: 40,
                    thickness: 3,
                    spacing: 8,
                    count: 3,
                    type: 'sheets'
                };
                
            case 'case-10-cylindrical-band-cut':
                return {
                    outer_diameter: 30,
                    inner_diameter: 20,
                    height: 15,
                    cut_angle: 60,
                    type: 'band'
                };
                
            default:
                return {
                    width: 30,
                    height: 30,
                    depth: 30,
                    type: 'box'
                };
        }
    }

    // 🚀 RENDERIZAR MESH REAL DO GROUNDTRUTH CODE
    async renderRealMesh(containerId, meshData, testCase) {
        console.log(`🚀 Renderizando mesh real para ${containerId}:`, meshData);
        
        const threeInstance = this.threeInstances.get(containerId);
        if (!threeInstance) {
            console.error(`❌ ThreeSetup ${containerId} não encontrado`);
            return;
        }

        // Esconder overlay
        this.hideViewportOverlay(containerId);

        // Criar dados do modelo com o mesh real
        const modelData = {
            testCase: testCase,  // Passar o caso de teste completo
            mesh_data: meshData,
            bounding_box: {
                min: [-50, -50, -50],
                max: [50, 50, 50]
            }
        };
        
        // Usar o método updateModel do ThreeSetup que agora suporta groundTruthCode
        await threeInstance.updateModel(modelData);
        
        console.log(`✅ Mesh real renderizada para ${testCase.name}`);
    }

    // Carregar placeholder usando ThreeSetup
    loadPlaceholder(containerId, type = 'loading', testCaseId = null) {
        console.log(`🔧 Carregando placeholder ${type} para ${containerId}`);
        
        const threeInstance = this.threeInstances.get(containerId);
        if (!threeInstance) {
            console.error(`❌ ThreeSetup ${containerId} não encontrado para placeholder`);
            return;
        }

        if (type === 'ground-truth' && testCaseId) {
            // Carregar modelo específico para ground truth
            this.loadGroundTruthModel(containerId, testCaseId);
        } else {
            // Para loading/error, apenas usar o placeholder padrão do ThreeSetup
            threeInstance.updateModel(null); // Forçar placeholder padrão
        }
    }

    // MÉTODO FALTANDO: Compatibilidade com código antigo
    loadPlaceholderModel(containerId, type = 'error') {
        console.log(`🔧 loadPlaceholderModel (compatibilidade): ${type} para ${containerId}`);
        this.loadPlaceholder(containerId, type);
    }

    // Limpar viewport
    destroyViewport(containerId) {
        const threeInstance = this.threeInstances.get(containerId);
        if (threeInstance) {
            threeInstance.dispose();
            this.threeInstances.delete(containerId);
            console.log(`🗑️ Viewport ${containerId} destruído`);
        }
    }
}

// Exportar instância global
window.benchmarkRenderer = new BenchmarkThreeRenderer(); 