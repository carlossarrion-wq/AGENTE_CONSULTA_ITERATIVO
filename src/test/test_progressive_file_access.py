#!/usr/bin/env python3
"""
Pruebas unitarias para las herramientas de acceso progresivo a archivos.
Prueba DocumentStructureAnalyzer y GetFileSection.
"""

import unittest
import sys
import os
import tempfile
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))

# Importar directamente los módulos sin pasar por __init__.py
import importlib.util

# Cargar document_structure_analyzer
spec1 = importlib.util.spec_from_file_location(
    "document_structure_analyzer",
    os.path.join(os.path.dirname(__file__), '..', 'tools', 'document_structure_analyzer.py')
)
doc_analyzer_module = importlib.util.module_from_spec(spec1)
spec1.loader.exec_module(doc_analyzer_module)

DocumentStructureAnalyzer = doc_analyzer_module.DocumentStructureAnalyzer
DocumentSection = doc_analyzer_module.DocumentSection
DocumentStructure = doc_analyzer_module.DocumentStructure

# Cargar tool_get_file_section
spec2 = importlib.util.spec_from_file_location(
    "tool_get_file_section",
    os.path.join(os.path.dirname(__file__), '..', 'tools', 'tool_get_file_section.py')
)
file_section_module = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(file_section_module)

GetFileSection = file_section_module.GetFileSection


class TestDocumentStructureAnalyzer(unittest.TestCase):
    """Pruebas para DocumentStructureAnalyzer"""
    
    def setUp(self):
        """Configuración antes de cada prueba"""
        self.analyzer = DocumentStructureAnalyzer()
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Limpieza después de cada prueba"""
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_analyzer_initialization(self):
        """Prueba que el analizador se inicializa correctamente"""
        self.assertIsNotNone(self.analyzer)
        self.assertIsNotNone(self.analyzer.logger)
    
    def test_analyze_nonexistent_file(self):
        """Prueba que se lanza error con archivo inexistente"""
        with self.assertRaises(FileNotFoundError):
            self.analyzer.analyze("/path/to/nonexistent/file.pdf")
    
    def test_analyze_unsupported_format(self):
        """Prueba que se lanza error con formato no soportado"""
        # Crear archivo temporal con extensión no soportada
        test_file = os.path.join(self.test_dir, "test.xyz")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        with self.assertRaises(ValueError):
            self.analyzer.analyze(test_file)
    
    def test_analyze_text_file(self):
        """Prueba análisis de archivo de texto simple"""
        # Crear archivo de texto con secciones
        test_file = os.path.join(self.test_dir, "test.txt")
        content = """1. Introducción
Este es el contenido de la introducción.

2. Desarrollo
Este es el contenido del desarrollo.

3. Conclusión
Este es el contenido de la conclusión.
"""
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Analizar
        structure = self.analyzer.analyze(test_file)
        
        # Verificaciones
        self.assertIsInstance(structure, DocumentStructure)
        self.assertEqual(structure.file_type, "txt")
        self.assertEqual(structure.file_name, "test.txt")
        self.assertEqual(structure.total_chars, len(content))
        self.assertGreater(len(structure.sections), 0)
    
    def test_document_section_dataclass(self):
        """Prueba la clase DocumentSection"""
        section = DocumentSection(
            id="section_1",
            title="Test Section",
            level=1,
            start_page=1,
            end_page=5,
            start_char=0,
            end_char=1000,
            char_count=1000
        )
        
        self.assertEqual(section.id, "section_1")
        self.assertEqual(section.title, "Test Section")
        self.assertEqual(section.level, 1)
        self.assertEqual(section.char_count, 1000)
        self.assertIsInstance(section.children_ids, list)
        self.assertEqual(len(section.children_ids), 0)
    
    def test_document_structure_dataclass(self):
        """Prueba la clase DocumentStructure"""
        sections = [
            DocumentSection(
                id="section_1",
                title="Section 1",
                level=1,
                start_page=1,
                end_page=2,
                char_count=500
            ),
            DocumentSection(
                id="section_2",
                title="Section 2",
                level=1,
                start_page=3,
                end_page=4,
                char_count=600
            )
        ]
        
        structure = DocumentStructure(
            file_path="/test/file.txt",
            file_name="file.txt",
            file_type="txt",
            total_pages=4,
            total_chars=1100,
            sections=sections,
            extraction_method="text_analysis"
        )
        
        self.assertEqual(structure.file_name, "file.txt")
        self.assertEqual(structure.total_pages, 4)
        self.assertEqual(len(structure.sections), 2)
        self.assertEqual(structure.extraction_method, "text_analysis")
    
    def test_document_structure_to_dict(self):
        """Prueba conversión de DocumentStructure a diccionario"""
        sections = [
            DocumentSection(
                id="section_1",
                title="Section 1",
                level=1,
                start_page=1,
                end_page=2,
                char_count=500
            )
        ]
        
        structure = DocumentStructure(
            file_path="/test/file.txt",
            file_name="file.txt",
            file_type="txt",
            total_pages=2,
            total_chars=500,
            sections=sections,
            extraction_method="text_analysis"
        )
        
        result = structure.to_dict()
        
        self.assertIsInstance(result, dict)
        self.assertIn("file_name", result)
        self.assertIn("sections", result)
        self.assertIn("table_of_contents", result)
        self.assertIsInstance(result["sections"], list)
        self.assertIsInstance(result["table_of_contents"], list)
    
    def test_document_structure_get_section_by_id(self):
        """Prueba búsqueda de sección por ID"""
        sections = [
            DocumentSection(
                id="section_1",
                title="Section 1",
                level=1,
                start_page=1,
                end_page=2,
                char_count=500
            ),
            DocumentSection(
                id="section_2",
                title="Section 2",
                level=1,
                start_page=3,
                end_page=4,
                char_count=600
            )
        ]
        
        structure = DocumentStructure(
            file_path="/test/file.txt",
            file_name="file.txt",
            file_type="txt",
            total_pages=4,
            total_chars=1100,
            sections=sections,
            extraction_method="text_analysis"
        )
        
        # Buscar sección existente
        section = structure.get_section_by_id("section_1")
        self.assertIsNotNone(section)
        self.assertEqual(section.title, "Section 1")
        
        # Buscar sección inexistente
        section = structure.get_section_by_id("section_999")
        self.assertIsNone(section)
    
    def test_generate_toc(self):
        """Prueba generación de tabla de contenidos"""
        sections = [
            DocumentSection(
                id="section_1",
                title="Introduction",
                level=1,
                start_page=1,
                end_page=3,
                char_count=1500
            ),
            DocumentSection(
                id="section_2",
                title="Development",
                level=1,
                start_page=4,
                end_page=10,
                char_count=3500
            )
        ]
        
        structure = DocumentStructure(
            file_path="/test/file.txt",
            file_name="file.txt",
            file_type="txt",
            total_pages=10,
            total_chars=5000,
            sections=sections,
            extraction_method="text_analysis"
        )
        
        toc = structure.generate_toc()
        
        self.assertIsInstance(toc, list)
        self.assertEqual(len(toc), 2)
        self.assertIn("id", toc[0])
        self.assertIn("title", toc[0])
        self.assertIn("level", toc[0])
        self.assertIn("pages", toc[0])
        self.assertIn("chars", toc[0])


class TestGetFileSection(unittest.TestCase):
    """Pruebas para GetFileSection"""
    
    def setUp(self):
        """Configuración antes de cada prueba"""
        self.tool = GetFileSection()
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Limpieza después de cada prueba"""
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_tool_initialization(self):
        """Prueba que la herramienta se inicializa correctamente"""
        self.assertIsNotNone(self.tool)
        self.assertIsNotNone(self.tool.analyzer)
        self.assertIsNotNone(self.tool.logger)
    
    def test_get_section_nonexistent_file(self):
        """Prueba con archivo inexistente"""
        result = self.tool.get_section(
            file_path="/path/to/nonexistent/file.pdf",
            section_id="section_1"
        )
        
        self.assertIn("error", result)
        self.assertIn("no encontrado", result["error"].lower())
    
    def test_get_section_from_text_file(self):
        """Prueba obtención de sección de archivo de texto"""
        # Crear archivo de texto con secciones
        test_file = os.path.join(self.test_dir, "test.txt")
        content = """1. Primera Sección
Este es el contenido de la primera sección.
Tiene varias líneas de texto.

2. Segunda Sección
Este es el contenido de la segunda sección.
También tiene varias líneas.

3. Tercera Sección
Este es el contenido de la tercera sección.
"""
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Obtener primera sección
        result = self.tool.get_section(
            file_path=test_file,
            section_id="section_1",
            include_context=False
        )
        
        # Verificaciones
        self.assertNotIn("error", result)
        self.assertIn("section", result)
        self.assertEqual(result["section"]["id"], "section_1")
        self.assertIn("content", result["section"])
        self.assertGreater(len(result["section"]["content"]), 0)
    
    def test_get_section_with_context(self):
        """Prueba obtención de sección con contexto"""
        # Crear archivo de texto
        test_file = os.path.join(self.test_dir, "test_context.txt")
        content = """1. Sección Principal
Contenido principal.

1.1 Subsección A
Contenido de subsección A.

1.2 Subsección B
Contenido de subsección B.

2. Otra Sección
Otro contenido.
"""
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Obtener sección con contexto
        result = self.tool.get_section(
            file_path=test_file,
            section_id="section_1",
            include_context=True
        )
        
        # Verificaciones
        self.assertNotIn("error", result)
        self.assertIn("section", result)
        
        # Verificar que se incluye contexto
        if "context" in result:
            self.assertIsInstance(result["context"], dict)
    
    def test_get_section_invalid_section_id(self):
        """Prueba con ID de sección inválido"""
        # Crear archivo de texto
        test_file = os.path.join(self.test_dir, "test_invalid.txt")
        content = """1. Única Sección
Contenido de la única sección.
"""
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Intentar obtener sección inexistente
        result = self.tool.get_section(
            file_path=test_file,
            section_id="section_999",
            include_context=False
        )
        
        # Verificaciones
        self.assertIn("error", result)
        self.assertIn("no encontrada", result["error"].lower())
        self.assertIn("available_sections", result)
    
    def test_extract_text_section(self):
        """Prueba extracción de sección de texto"""
        # Crear archivo
        test_file = os.path.join(self.test_dir, "test_extract.txt")
        content = "A" * 1000 + "B" * 1000 + "C" * 1000
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Crear sección mock
        section = DocumentSection(
            id="section_1",
            title="Test",
            level=1,
            start_page=1,
            end_page=1,
            start_char=1000,
            end_char=2000,
            char_count=1000
        )
        
        # Extraer contenido
        extracted = self.tool._extract_text_section(test_file, section)
        
        # Verificaciones
        self.assertEqual(len(extracted), 1000)
        self.assertTrue(all(c == 'B' for c in extracted))


class TestIntegration(unittest.TestCase):
    """Pruebas de integración entre componentes"""
    
    def setUp(self):
        """Configuración antes de cada prueba"""
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Limpieza después de cada prueba"""
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_full_workflow_text_file(self):
        """Prueba flujo completo: analizar estructura y obtener sección"""
        # Crear archivo de texto estructurado
        test_file = os.path.join(self.test_dir, "workflow_test.txt")
        content = """1. Introducción
Esta es la introducción del documento.
Contiene información preliminar importante.

2. Desarrollo
Este es el desarrollo del documento.
Aquí se presenta el contenido principal.
Incluye varios párrafos de información.

3. Conclusión
Esta es la conclusión del documento.
Resume los puntos principales.
"""
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Paso 1: Analizar estructura
        analyzer = DocumentStructureAnalyzer()
        structure = analyzer.analyze(test_file)
        
        # Verificar estructura
        self.assertIsNotNone(structure)
        self.assertGreater(len(structure.sections), 0)
        
        # Paso 2: Obtener sección específica
        tool = GetFileSection()
        result = tool.get_section(
            file_path=test_file,
            section_id=structure.sections[0].id,
            include_context=True
        )
        
        # Verificar resultado
        self.assertNotIn("error", result)
        self.assertIn("section", result)
        self.assertIn("content", result["section"])
        self.assertGreater(len(result["section"]["content"]), 0)


def run_tests():
    """Ejecuta todas las pruebas y genera reporte"""
    # Crear suite de pruebas
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Agregar todas las clases de prueba
    suite.addTests(loader.loadTestsFromTestCase(TestDocumentStructureAnalyzer))
    suite.addTests(loader.loadTestsFromTestCase(TestGetFileSection))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Ejecutar pruebas con verbosidad
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Generar resumen
    print("\n" + "=" * 80)
    print("RESUMEN DE PRUEBAS")
    print("=" * 80)
    print(f"Total de pruebas ejecutadas: {result.testsRun}")
    print(f"✅ Exitosas: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Fallidas: {len(result.failures)}")
    print(f"⚠️  Errores: {len(result.errors)}")
    print(f"⏭️  Omitidas: {len(result.skipped)}")
    
    if result.wasSuccessful():
        print("\n🎉 ¡Todas las pruebas pasaron exitosamente!")
        return 0
    else:
        print("\n⚠️  Algunas pruebas fallaron. Revisa los detalles arriba.")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
