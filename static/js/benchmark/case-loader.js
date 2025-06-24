// Sistema de carregamento de casos de teste
class BenchmarkCaseLoader {
    constructor() {
        this.cases = [];
        this.loadedCases = new Map();
    }

    // Carregar todos os casos disponíveis
    async loadAllCases() {
        const caseFiles = [
            'case-01-cylinder-hex-hole.js',
            'case-02-block-semicylinder-channel.js', 
            'case-03-half-pipe.js',
            'case-04-hexagonal-plate.js',
            'case-05-drop-shape-holes.js',
            'case-06-cylinder-square-hole.js',
            'case-07-four-cylinders-corners.js',
            'case-08-trapezoidal-prism.js',
            'case-09-three-parallel-sheets.js',
            'case-10-cylindrical-band-cut.js'
        ];

        for (const file of caseFiles) {
            try {
                await this.loadCase(file);
            } catch (error) {
                console.warn(`⚠️ Erro ao carregar caso ${file}:`, error);
            }
        }

        console.log(`✅ ${this.cases.length} casos carregados`);
        return this.cases;
    }

    // Carregar um caso específico
    async loadCase(fileName) {
        const caseId = fileName.replace('.js', '');
        
        if (this.loadedCases.has(caseId)) {
            return this.loadedCases.get(caseId);
        }

        try {
            // Carregar o arquivo do caso
            const script = document.createElement('script');
            script.src = `/static/benchmark/cases/${fileName}`;
            
            return new Promise((resolve, reject) => {
                script.onload = () => {
                    if (window.testCase) {
                        const testCase = { ...window.testCase };
                        
                        // Validar caso
                        if (this.validateCase(testCase)) {
                            this.cases.push(testCase);
                            this.loadedCases.set(caseId, testCase);
                            console.log(`✅ Caso carregado: ${testCase.name}`);
                            resolve(testCase);
                        } else {
                            reject(new Error(`Caso inválido: ${caseId}`));
                        }
                        
                        // Limpar variável global
                        delete window.testCase;
                    } else {
                        reject(new Error(`Caso não encontrado no arquivo: ${fileName}`));
                    }
                    
                    document.head.removeChild(script);
                };
                
                script.onerror = () => {
                    document.head.removeChild(script);
                    reject(new Error(`Erro ao carregar arquivo: ${fileName}`));
                };
                
                document.head.appendChild(script);
            });
        } catch (error) {
            console.error(`❌ Erro ao carregar caso ${fileName}:`, error);
            throw error;
        }
    }

    // Validar estrutura do caso
    validateCase(testCase) {
        const requiredFields = ['id', 'name', 'description', 'prompt', 'groundTruthCode'];
        
        for (const field of requiredFields) {
            if (!testCase[field]) {
                console.error(`❌ Campo obrigatório ausente: ${field}`);
                return false;
            }
        }
        
        return true;
    }

    // Obter caso por ID
    getCaseById(caseId) {
        return this.cases.find(testCase => testCase.id === caseId);
    }

    // Obter todos os casos
    getAllCases() {
        return this.cases;
    }

    // Filtrar casos
    filterCases(criteria) {
        return this.cases.filter(testCase => {
            return Object.keys(criteria).every(key => {
                return testCase[key] && testCase[key].toString().toLowerCase().includes(criteria[key].toLowerCase());
            });
        });
    }

    // Obter lista de casos disponíveis
    getAvailableCases() {
        return this.cases.map(testCase => ({
            id: testCase.id,
            name: testCase.name,
            description: testCase.description
        }));
    }
}

// Instância global
window.benchmarkLoader = new BenchmarkCaseLoader();

 