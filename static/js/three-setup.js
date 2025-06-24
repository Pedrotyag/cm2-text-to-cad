// Configuração do Three.js para visualização 3D
class ThreeSetup {
    constructor(containerId) {
        this.containerId = containerId;
        this.container = null;
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.currentModel = null;
        this.selectedGeometry = null;
        this.raycaster = null;
        this.mouse = null;
        
        // Configurações
        this.cameraDistance = 200;
        this.modelBounds = { min: [-50, -50, -50], max: [50, 50, 50] };
    }
    
    init() {
        this.container = document.getElementById(this.containerId);
        if (!this.container) {
            throw new Error(`Container ${this.containerId} não encontrado`);
        }
        
        this.setupScene();
        this.setupCamera();
        this.setupRenderer();
        this.setupControls();
        this.setupLighting();
        this.setupInteraction();
        this.setupGrid();
        
        // Iniciar loop de renderização
        this.animate();
        
        // Lidar com redimensionamento
        window.addEventListener('resize', () => this.onWindowResize());
        
        console.log('🎯 Three.js inicializado');
    }
    
    setupScene() {
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0xf5f7fa);
        this.scene.fog = new THREE.Fog(0xf5f7fa, 500, 2000);
    }
    
    setupCamera() {
        const aspect = this.container.clientWidth / this.container.clientHeight;
        this.camera = new THREE.PerspectiveCamera(60, aspect, 1, 2000);
        // Posição para mostrar plano XY (olhando de cima com ângulo)
        this.camera.position.set(80, 80, 120);
        this.camera.lookAt(0, 0, 0);
    }
    
    setupRenderer() {
        this.renderer = new THREE.WebGLRenderer({ 
            antialias: true,
            alpha: true
        });
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        this.renderer.outputEncoding = THREE.sRGBEncoding;
        this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        this.renderer.toneMappingExposure = 1.2;
        
        this.container.appendChild(this.renderer.domElement);
    }
    
    setupControls() {
        this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.screenSpacePanning = false;
        this.controls.minDistance = 50;
        this.controls.maxDistance = 500;
        this.controls.maxPolarAngle = Math.PI / 2;
    }
    
    setupLighting() {
        // Luz ambiente
        const ambientLight = new THREE.AmbientLight(0x404040, 0.6);
        this.scene.add(ambientLight);
        
        // Luz direcional principal
        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(100, 100, 50);
        directionalLight.castShadow = true;
        directionalLight.shadow.mapSize.width = 2048;
        directionalLight.shadow.mapSize.height = 2048;
        directionalLight.shadow.camera.near = 0.5;
        directionalLight.shadow.camera.far = 500;
        directionalLight.shadow.camera.left = -100;
        directionalLight.shadow.camera.right = 100;
        directionalLight.shadow.camera.top = 100;
        directionalLight.shadow.camera.bottom = -100;
        this.scene.add(directionalLight);
        
        // Luz de preenchimento
        const fillLight = new THREE.DirectionalLight(0xffffff, 0.3);
        fillLight.position.set(-50, 50, 100);
        this.scene.add(fillLight);
        
        // Luz de destaque
        const rimLight = new THREE.DirectionalLight(0xffffff, 0.2);
        rimLight.position.set(0, 50, -100);
        this.scene.add(rimLight);
    }
    
    setupInteraction() {
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();
        
        this.renderer.domElement.addEventListener('click', (event) => {
            this.onMouseClick(event);
        });
        
        this.renderer.domElement.addEventListener('mousemove', (event) => {
            this.onMouseMove(event);
        });
    }
    
    setupGrid() {
        const gridHelper = new THREE.GridHelper(200, 20, 0x888888, 0xcccccc);
        gridHelper.material.opacity = 0.3;
        gridHelper.material.transparent = true;
        this.scene.add(gridHelper);
        
        // Eixos com legenda
        const axesHelper = new THREE.AxesHelper(60);
        this.scene.add(axesHelper);
        
        // Adicionar labels dos eixos
        this.addAxisLabels();
    }
    
    addAxisLabels() {
        // Função para criar texture de texto (canvas separado para cada)
        const createTextTexture = (text, color) => {
            const canvas = document.createElement('canvas');
            const context = canvas.getContext('2d');
            canvas.width = 64;
            canvas.height = 64;
            
            context.clearRect(0, 0, 64, 64);
            context.font = 'Bold 48px Arial';
            context.fillStyle = color;
            context.textAlign = 'center';
            context.textBaseline = 'middle';
            context.fillText(text, 32, 32);
            
            const texture = new THREE.CanvasTexture(canvas);
            return texture;
        };
        
        // Label X (vermelho)
        const textureX = createTextTexture('X', '#ff0000');
        const spriteX = new THREE.Sprite(new THREE.SpriteMaterial({ map: textureX }));
        spriteX.position.set(70, 0, 0);
        spriteX.scale.set(20, 20, 1);
        this.scene.add(spriteX);
        
        // Label Y (verde) 
        const textureY = createTextTexture('Y', '#00ff00');
        const spriteY = new THREE.Sprite(new THREE.SpriteMaterial({ map: textureY }));
        spriteY.position.set(0, 70, 0);
        spriteY.scale.set(20, 20, 1);
        this.scene.add(spriteY);
        
        // Label Z (azul)
        const textureZ = createTextTexture('Z', '#0000ff');
        const spriteZ = new THREE.Sprite(new THREE.SpriteMaterial({ map: textureZ }));
        spriteZ.position.set(0, 0, 70);
        spriteZ.scale.set(20, 20, 1);
        this.scene.add(spriteZ);
    }
    
    onMouseClick(event) {
        // Calcular coordenadas do mouse normalizadas
        const rect = this.renderer.domElement.getBoundingClientRect();
        this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
        
        // Realizar raycast
        this.raycaster.setFromCamera(this.mouse, this.camera);
        
        if (this.currentModel) {
            const intersects = this.raycaster.intersectObject(this.currentModel, true);
            
            if (intersects.length > 0) {
                const intersection = intersects[0];
                this.selectGeometry(intersection);
            } else {
                this.clearSelection();
            }
        }
    }
    
    onMouseMove(event) {
        // Atualizar cursor baseado no hover
        const rect = this.renderer.domElement.getBoundingClientRect();
        this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
        
        this.raycaster.setFromCamera(this.mouse, this.camera);
        
        if (this.currentModel) {
            const intersects = this.raycaster.intersectObject(this.currentModel, true);
            this.renderer.domElement.style.cursor = intersects.length > 0 ? 'pointer' : 'default';
        }
    }
    
    selectGeometry(intersection) {
        // Limpar seleção anterior
        this.clearSelection();
        
        // Destacar geometria selecionada
        const mesh = intersection.object;
        if (mesh.material) {
            // Salvar material original
            mesh.userData.originalMaterial = mesh.material;
            
            // Aplicar material de seleção
            mesh.material = new THREE.MeshBasicMaterial({
                color: 0x00ff00,
                transparent: true,
                opacity: 0.7,
                wireframe: true
            });
        }
        
        // Salvar informações da seleção
        this.selectedGeometry = {
            element_type: 'face', // Simplificado por enquanto
            element_id: mesh.uuid,
            coordinates: [intersection.point.x, intersection.point.y, intersection.point.z],
            normal: intersection.face ? [intersection.face.normal.x, intersection.face.normal.y, intersection.face.normal.z] : null
        };
        
        console.log('🎯 Geometria selecionada:', this.selectedGeometry);
    }
    
    clearSelection() {
        if (this.currentModel) {
            this.currentModel.traverse((child) => {
                if (child.userData.originalMaterial) {
                    child.material = child.userData.originalMaterial;
                    delete child.userData.originalMaterial;
                }
            });
        }
        
        this.selectedGeometry = null;
    }
    
    getSelectedGeometry() {
        return this.selectedGeometry;
    }
    
    // 🚀 EXECUTAR GROUND TRUTH CODE E RENDERIZAR RESULTADO REAL
    async executeGroundTruthCode(testCase) {
        console.log(`🚀 Executando groundTruthCode para: ${testCase.name}`);
        
        try {
            // Fazer requisição para o backend executar o código CadQuery
            const response = await fetch('/api/execute_groundtruth', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    case_id: testCase.id,
                    ground_truth_code: testCase.groundTruthCode
                })
            });
            
            if (!response.ok) {
                throw new Error(`Erro HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            if (result.success && result.mesh_data) {
                console.log('✅ Ground truth executado com sucesso');
                return this.renderRealMesh(result.mesh_data);
            } else {
                console.error('❌ Erro ao executar ground truth:', result.error);
                throw new Error(result.error || 'Erro desconhecido');
            }
            
        } catch (error) {
            console.error('❌ Erro ao executar groundTruthCode:', error);
            // Fallback para modelo placeholder se executar falhar
            return this.createSpecificModel(testCase.id, {});
        }
    }
    
    // 🎨 Renderizar mesh real a partir dos dados do CadQuery
    renderRealMesh(meshData) {
        console.log('🎨 Renderizando mesh real:', meshData);
        
        try {
            // Criar geometria a partir dos dados de vértices e faces
            const geometry = new THREE.BufferGeometry();
            
            // Vértices
            if (meshData.vertices && meshData.vertices.length > 0) {
                const vertices = new Float32Array(meshData.vertices);
                geometry.setAttribute('position', new THREE.BufferAttribute(vertices, 3));
            }
            
            // Faces (índices)
            if (meshData.faces && meshData.faces.length > 0) {
                const indices = new Uint32Array(meshData.faces);
                geometry.setIndex(new THREE.BufferAttribute(indices, 1));
            }
            
            // Calcular normais automaticamente
            geometry.computeVertexNormals();
            
            // Material baseado no caso
            const material = new THREE.MeshLambertMaterial({ 
                color: 0x4a90e2,
                side: THREE.DoubleSide,
                transparent: false,
                opacity: 1.0
            });
            
            // Criar mesh
            const mesh = new THREE.Mesh(geometry, material);
            mesh.castShadow = true;
            mesh.receiveShadow = true;
            
            console.log('✅ Mesh real renderizada com sucesso');
            return mesh;
            
        } catch (error) {
            console.error('❌ Erro ao renderizar mesh real:', error);
            // Fallback para geometria simples
            const geometry = new THREE.BoxGeometry(30, 30, 30);
            const material = new THREE.MeshLambertMaterial({ color: 0xff6b6b });
            const mesh = new THREE.Mesh(geometry, material);
            mesh.castShadow = true;
            mesh.receiveShadow = true;
            return mesh;
        }
    }
    
    // Modificar updateModel para usar groundTruthCode quando disponível
    async updateModel(modelData) {
        console.log('🔄 Atualizando modelo:', modelData);
        console.log('🔍 Verificando condições:');
        console.log('  - modelData existe?', !!modelData);
        console.log('  - modelData.mesh_data existe?', !!(modelData && modelData.mesh_data));
        console.log('  - modelData.mesh_data.data_base64 existe?', !!(modelData && modelData.mesh_data && modelData.mesh_data.data_base64));
        if (modelData && modelData.mesh_data) {
            console.log('  - Chaves do mesh_data:', Object.keys(modelData.mesh_data));
            console.log('  - Tamanho do data_base64:', modelData.mesh_data.data_base64?.length || 'N/A');
        }
        
        // Remover modelo atual
        if (this.currentModel) {
            this.scene.remove(this.currentModel);
            this.currentModel = null;
        }
        
        let newModel;
        
        // Se temos um caso de teste com groundTruthCode, executar ele
        if (modelData && modelData.testCase && modelData.testCase.groundTruthCode) {
            newModel = await this.executeGroundTruthCode(modelData.testCase);
        }
        // Senão usar mesh real se disponível (STL do CadQuery)
        else if (modelData && modelData.mesh_data && modelData.mesh_data.data_base64) {
            console.log('🎯 Detectado mesh_data STL do CadQuery, carregando mesh real...');
            newModel = this.loadRealMesh(modelData);
        }
        // Senão usar mesh real se disponível (formato antigo)
        else if (modelData && modelData.vertices && modelData.faces) {
            newModel = this.loadRealMesh(modelData);
        }
        // Senão usar modelo placeholder
        else {
            console.log('📦 Usando modelo placeholder');
            console.log('📋 Dados recebidos:', Object.keys(modelData || {}));
            newModel = this.createPlaceholderModel(modelData);
        }
        
        // Adicionar novo modelo à cena
        if (newModel) {
            this.scene.add(newModel);
            this.currentModel = newModel;
            
            // Ajustar visualização
            this.fitView();
            
            console.log('✅ Modelo atualizado');
        }
    }
    
    /**
     * SISTEMA GENÉRICO: Carregar mesh real diretamente do CadQuery (STL em base64)
     * Este método funciona para QUALQUER geometria gerada pelo CadQuery
     */
    loadRealMesh(modelData) {
        console.log('🔄 Processando mesh real STL GENÉRICO...');
        console.log('📋 Dados do modelo:', Object.keys(modelData));
        
        try {
            // Verificar se temos dados STL do CadQuery
            if (modelData.mesh_data && modelData.mesh_data.data_base64) {
                console.log('✅ Encontrado mesh_data.data_base64, processando STL...');
                // Decodificar base64 para ArrayBuffer
                const base64Data = modelData.mesh_data.data_base64;
                const binaryString = atob(base64Data);
                const len = binaryString.length;
                const bytes = new Uint8Array(len);
                
                for (let i = 0; i < len; i++) {
                    bytes[i] = binaryString.charCodeAt(i);
                }
                
                // Carregar STL usando STLLoader do Three.js
                const loader = new THREE.STLLoader();
                const geometry = loader.parse(bytes.buffer);
                
                // Configurar geometria
                geometry.computeBoundingBox();
                geometry.computeVertexNormals();
                
                // Centralizar geometria
                const center = new THREE.Vector3();
                geometry.boundingBox.getCenter(center);
                geometry.translate(-center.x, -center.y, -center.z);
                
                // Criar material
                const material = new THREE.MeshLambertMaterial({ 
                    color: 0x3498db,
                    transparent: true,
                    opacity: 0.8
                });
                
                // Criar mesh
                const mesh = new THREE.Mesh(geometry, material);
                mesh.castShadow = true;
                mesh.receiveShadow = true;
                
                // Adicionar wireframe para melhor visualização
                const wireframe = new THREE.WireframeGeometry(geometry);
                const wireframeMaterial = new THREE.LineBasicMaterial({ 
                    color: 0x2c3e50, 
                    linewidth: 1 
                });
                const wireframeMesh = new THREE.LineSegments(wireframe, wireframeMaterial);
                
                // Criar grupo
                const group = new THREE.Group();
                group.add(mesh);
                group.add(wireframeMesh);
                
                // Atualizar bounds do modelo
                const bbox = modelData.bounding_box;
                this.modelBounds = { min: bbox.min, max: bbox.max };
                
                console.log('✅ MESH REAL GENÉRICO CARREGADO!', {
                    vertices: geometry.attributes.position.count,
                    faces: geometry.attributes.position.count / 3,
                    bounds: this.modelBounds
                });
                
                return group;
            } else {
                console.log('❌ Não encontrado mesh_data.data_base64, usando fallback');
                throw new Error('Dados STL não encontrados');
            }
            
        } catch (error) {
            console.error('❌ Erro ao carregar mesh real:', error);
            console.log('🔄 Fallback para placeholder...');
            return this.createPlaceholderModel();
        }
    }

    createPlaceholderModel(modelData = null) {
        console.log('🎨 createPlaceholderModel chamado com:', modelData);
        
        // 🎨 PERSONALIZAÇÃO: Criar modelos específicos para benchmark
        if (modelData && modelData.test_case_id) {
            console.log(`🎯 Criando modelo específico para: ${modelData.test_case_id}`);
            return this.createSpecificModel(modelData.test_case_id, modelData.parameters);
        }
        
        console.log('📦 Usando modelo padrão (caixa cinza)');
        // Modelo padrão
        const geometry = new THREE.BoxGeometry(50, 30, 20);
        const material = new THREE.MeshLambertMaterial({ color: 0xcccccc });
        const mesh = new THREE.Mesh(geometry, material);
        mesh.castShadow = true;
        mesh.receiveShadow = true;
        
        return mesh;
    }
    
    // 🎯 Criar modelos específicos para cada caso de teste
    createSpecificModel(testCaseId, parameters) {
        console.log(`🎨 createSpecificModel: ${testCaseId}`, parameters);
        let geometry, material, mesh;
        
        switch (testCaseId) {
            case 'case-01-cylinder-hex-hole':
                // Cilindro azul com torus hexagonal simulando furo
                const cylinder = new THREE.CylinderGeometry(25, 25, 40, 32);
                const cylinderMesh = new THREE.Mesh(cylinder, new THREE.MeshLambertMaterial({ color: 0x4a90e2 }));
                
                const hexTorus = new THREE.TorusGeometry(8, 2, 6, 6);
                const hexMesh = new THREE.Mesh(hexTorus, new THREE.MeshLambertMaterial({ color: 0x2c3e50 }));
                hexMesh.rotation.x = Math.PI / 2;
                
                const group1 = new THREE.Group();
                cylinderMesh.castShadow = true;
                cylinderMesh.receiveShadow = true;
                hexMesh.castShadow = true;
                hexMesh.receiveShadow = true;
                group1.add(cylinderMesh);
                group1.add(hexMesh);
                return group1;
                
            case 'case-02-block-semicylinder-channel':
                // Bloco verde com canal semicilíndrico
                const block = new THREE.BoxGeometry(60, 40, 20);
                const blockMesh = new THREE.Mesh(block, new THREE.MeshLambertMaterial({ color: 0x7fb069 }));
                
                const channel = new THREE.CylinderGeometry(8, 8, 65, 16, 1, false, 0, Math.PI);
                const channelMesh = new THREE.Mesh(channel, new THREE.MeshLambertMaterial({ color: 0x2c3e50 }));
                channelMesh.rotation.z = Math.PI / 2;
                channelMesh.position.y = 10;
                
                const group2 = new THREE.Group();
                blockMesh.castShadow = true;
                blockMesh.receiveShadow = true;
                channelMesh.castShadow = true;
                channelMesh.receiveShadow = true;
                group2.add(blockMesh);
                group2.add(channelMesh);
                return group2;
                
            case 'case-03-half-pipe':
                // Half-pipe vermelho
                geometry = new THREE.CylinderGeometry(20, 20, 80, 32, 1, false, 0, Math.PI);
                material = new THREE.MeshLambertMaterial({ color: 0xe74c3c });
                mesh = new THREE.Mesh(geometry, material);
                mesh.rotation.z = Math.PI / 2;
                mesh.castShadow = true;
                mesh.receiveShadow = true;
                return mesh;
                
            case 'case-04-hexagonal-plate':
                // Placa hexagonal roxa
                geometry = new THREE.CylinderGeometry(30, 30, 5, 6);
                material = new THREE.MeshLambertMaterial({ color: 0x9b59b6 });
                mesh = new THREE.Mesh(geometry, material);
                mesh.castShadow = true;
                mesh.receiveShadow = true;
                return mesh;
                
            case 'case-05-drop-shape-holes':
                // Formato de gota turquesa com furos
                const drop = new THREE.SphereGeometry(25, 32, 16, 0, Math.PI * 2, 0, Math.PI / 1.5);
                const dropMesh = new THREE.Mesh(drop, new THREE.MeshLambertMaterial({ color: 0x1abc9c }));
                
                const holes = [];
                for (let i = 0; i < 2; i++) {
                    const hole = new THREE.SphereGeometry(i === 0 ? 4 : 2, 16, 8);
                    const holeMesh = new THREE.Mesh(hole, new THREE.MeshLambertMaterial({ color: 0x2c3e50 }));
                    holeMesh.position.set(i === 0 ? 15 : -15, 0, 0);
                    holes.push(holeMesh);
                }
                
                const group3 = new THREE.Group();
                dropMesh.castShadow = true;
                dropMesh.receiveShadow = true;
                holes.forEach(hole => {
                    hole.castShadow = true;
                    hole.receiveShadow = true;
                    group3.add(hole);
                });
                group3.add(dropMesh);
                return group3;
                
            case 'case-06-cylinder-square-hole':
                // Cilindro laranja com furo quadrado
                const cylinder2 = new THREE.CylinderGeometry(12.5, 12.5, 15, 32);
                const cylinderMesh2 = new THREE.Mesh(cylinder2, new THREE.MeshLambertMaterial({ color: 0xf39c12 }));
                
                const squareHole = new THREE.BoxGeometry(6, 6, 18);
                const squareMesh = new THREE.Mesh(squareHole, new THREE.MeshLambertMaterial({ color: 0x2c3e50 }));
                
                const group4 = new THREE.Group();
                cylinderMesh2.castShadow = true;
                cylinderMesh2.receiveShadow = true;
                squareMesh.castShadow = true;
                squareMesh.receiveShadow = true;
                group4.add(cylinderMesh2);
                group4.add(squareMesh);
                return group4;
                
            case 'case-07-four-cylinders-corners':
                // Quatro cilindros roxos nos cantos (DISTRIBUIÇÃO DESIGUAL)
                const group5 = new THREE.Group();
                const positions = [
                    [18, 12, 0], [-10, 14, 0], [-16, -8, 0], [20, -15, 0]  // Distribuição irregular
                ];
                
                positions.forEach(pos => {
                    const cyl = new THREE.CylinderGeometry(4, 4, 20, 16);
                    const cylMesh = new THREE.Mesh(cyl, new THREE.MeshLambertMaterial({ color: 0x8e44ad }));
                    cylMesh.position.set(pos[0], pos[1], pos[2]);
                    cylMesh.castShadow = true;
                    cylMesh.receiveShadow = true;
                    group5.add(cylMesh);
                });
                return group5;
                
            case 'case-08-trapezoidal-prism':
                // Prisma trapezoidal FINO marrom (atualizado com parâmetros corretos)
                const shape = new THREE.Shape();
                // Usar parâmetros corretos: base_maior=30, base_menor=15, altura=20
                shape.moveTo(-15, -10);  // base maior/2 = 30/2 = 15
                shape.lineTo(15, -10);   // base maior/2 = 30/2 = 15
                shape.lineTo(7.5, 10);   // base menor/2 = 15/2 = 7.5
                shape.lineTo(-7.5, 10);  // base menor/2 = 15/2 = 7.5
                shape.lineTo(-15, -10);
                
                // Espessura FINA = 3mm (não 12mm)
                const extrudeSettings = { depth: 3, bevelEnabled: false };
                geometry = new THREE.ExtrudeGeometry(shape, extrudeSettings);
                material = new THREE.MeshLambertMaterial({ color: 0xd35400 });
                mesh = new THREE.Mesh(geometry, material);
                mesh.castShadow = true;
                mesh.receiveShadow = true;
                return mesh;
                
            case 'case-09-three-parallel-sheets':
                // Três chapas paralelas VERTICAIS (em pé)
                const group6 = new THREE.Group();
                const spacing = 8;
                const thickness = 3;
                
                // Posições das chapas conforme o código CadQuery
                const yPositions = [
                    -spacing - thickness/2,  // chapa 1
                    0,                       // chapa 2 (centro)
                    spacing + thickness/2    // chapa 3
                ];
                
                for (let i = 0; i < 3; i++) {
                    // Geometria VERTICAL: largura=25, espessura=3, altura=40
                    const sheet = new THREE.BoxGeometry(25, thickness, 40);
                    const sheetMesh = new THREE.Mesh(sheet, new THREE.MeshLambertMaterial({ color: 0x34495e }));
                    sheetMesh.position.set(0, yPositions[i], 0);
                    sheetMesh.castShadow = true;
                    sheetMesh.receiveShadow = true;
                    group6.add(sheetMesh);
                }
                return group6;
                
            case 'case-10-cylindrical-band-cut':
                // Banda cilíndrica oca com setor removido (como tubo com corte)
                const group7 = new THREE.Group();
                
                // Anel exterior com setor de 60° removido
                const outerRadius = 15; // 30mm diâmetro / 2
                const innerRadius = 10; // 20mm diâmetro / 2 
                const height = 15;
                const cutAngle = 60 * Math.PI / 180; // 60 graus em radianos
                
                // Geometria do anel com abertura
                const ringGeometry = new THREE.RingGeometry(innerRadius, outerRadius, 32, 1, 0, 2 * Math.PI - cutAngle);
                
                // Extrudar manualmente criando um cilindro oco com abertura
                const bandGeometry = new THREE.CylinderGeometry(outerRadius, outerRadius, height, 32, 1, true, 0, 2 * Math.PI - cutAngle);
                const bandMesh = new THREE.Mesh(bandGeometry, new THREE.MeshLambertMaterial({ color: 0x16a085 }));
                
                // Cilindro interno para criar furo
                const innerGeometry = new THREE.CylinderGeometry(innerRadius, innerRadius, height + 1, 32);
                const innerMesh = new THREE.Mesh(innerGeometry, new THREE.MeshLambertMaterial({ 
                    color: 0x2c3e50,
                    transparent: true,
                    opacity: 0.3
                }));
                
                bandMesh.castShadow = true;
                bandMesh.receiveShadow = true;
                innerMesh.castShadow = true;
                innerMesh.receiveShadow = true;
                
                group7.add(bandMesh);
                group7.add(innerMesh);
                return group7;

                
            default:
                // Modelo padrão cinza
                geometry = new THREE.BoxGeometry(30, 30, 30);
                material = new THREE.MeshLambertMaterial({ color: 0x95a5a6 });
                mesh = new THREE.Mesh(geometry, material);
                mesh.castShadow = true;
                mesh.receiveShadow = true;
                return mesh;
        }
    }
    
    resetView() {
        // Posição para mostrar plano XY (olhando de cima com ângulo)
        this.camera.position.set(80, 80, 120);
        this.camera.lookAt(0, 0, 0);
        this.controls.reset();
    }
    
    fitView() {
        if (!this.currentModel) return;
        
        // Calcular bounding box do modelo
        const box = new THREE.Box3().setFromObject(this.currentModel);
        const size = box.getSize(new THREE.Vector3());
        const center = box.getCenter(new THREE.Vector3());
        
        // Ajustar câmera para enquadrar o modelo
        const maxDim = Math.max(size.x, size.y, size.z);
        const fov = this.camera.fov * (Math.PI / 180);
        const cameraDistance = Math.abs(maxDim / 2 / Math.sin(fov / 2)) * 1.5;
        
        this.camera.position.copy(center);
        this.camera.position.z += cameraDistance;
        this.camera.lookAt(center);
        
        this.controls.target.copy(center);
        this.controls.update();
    }
    
    animate() {
        requestAnimationFrame(() => this.animate());
        
        if (this.controls) {
            this.controls.update();
        }
        
        this.renderer.render(this.scene, this.camera);
    }
    
    onWindowResize() {
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;
        
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        
        this.renderer.setSize(width, height);
    }
    
    dispose() {
        console.log('🧹 Limpando recursos Three.js');
        
        // Limpar geometrias e materiais da cena
        if (this.scene) {
            this.scene.traverse((object) => {
                if (object.geometry) {
                    object.geometry.dispose();
                }
                if (object.material) {
                    if (Array.isArray(object.material)) {
                        object.material.forEach(material => material.dispose());
                    } else {
                        object.material.dispose();
                    }
                }
            });
            
            // Limpar cena
            while (this.scene.children.length > 0) {
                this.scene.remove(this.scene.children[0]);
            }
        }
        
        // Limpar renderer
        if (this.renderer) {
            this.renderer.dispose();
            
            // Remover canvas do DOM
            if (this.container && this.renderer.domElement) {
                this.container.removeChild(this.renderer.domElement);
            }
        }
        
        // Limpar controles
        if (this.controls) {
            this.controls.dispose();
        }
        
        // Remover event listeners
        window.removeEventListener('resize', this.onWindowResize);
    }
} 