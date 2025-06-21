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
        this.camera.position.set(100, 100, 100);
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
        
        // Eixos
        const axesHelper = new THREE.AxesHelper(50);
        this.scene.add(axesHelper);
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
    
    updateModel(modelData) {
        console.log('🎨 Atualizando modelo 3D:', modelData);
        
        // Remover modelo anterior
        if (this.currentModel) {
            this.scene.remove(this.currentModel);
        }

        // SISTEMA 100% GENÉRICO: Carregar APENAS mesh real do CadQuery
        if (modelData && modelData.mesh_data && modelData.mesh_data.data_base64) {
            console.log('🎯 CARREGANDO MESH REAL GENÉRICO do CadQuery!');
            this.currentModel = this.loadRealMesh(modelData);
        } else {
            console.warn('⚠️ Nenhum mesh real disponível - usando placeholder');
            this.currentModel = this.createPlaceholderModel();
        }

        if (this.currentModel) {
            this.scene.add(this.currentModel);
            this.fitView();
        }
    }

    /**
     * SISTEMA GENÉRICO: Carregar mesh real diretamente do CadQuery (STL em base64)
     * Este método funciona para QUALQUER geometria gerada pelo CadQuery
     */
    loadRealMesh(modelData) {
        console.log('🔄 Processando mesh real STL GENÉRICO...');
        
        try {
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
            
        } catch (error) {
            console.error('❌ Erro ao carregar mesh real:', error);
            console.log('🔄 Fallback para placeholder...');
            return this.createPlaceholderModel();
        }
    }

    createPlaceholderModel() {
        const geometry = new THREE.BoxGeometry(50, 30, 20);
        const material = new THREE.MeshLambertMaterial({ color: 0xcccccc });
        const mesh = new THREE.Mesh(geometry, material);
        mesh.castShadow = true;
        mesh.receiveShadow = true;
        
        return mesh;
    }
    
    resetView() {
        this.camera.position.set(100, 100, 100);
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
        if (this.renderer) {
            this.renderer.dispose();
        }
        
        if (this.controls) {
            this.controls.dispose();
        }
        
        window.removeEventListener('resize', this.onWindowResize);
    }
} 