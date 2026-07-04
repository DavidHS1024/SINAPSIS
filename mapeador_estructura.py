import os
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter


class MapeadorProyecto:
    """
    Generador de radiografías arquitectónicas para proyectos de software.
    Recorre el árbol de directorios local y plasma su topología en Markdown.
    """

    def __init__(self, archivo_salida: str = "ARQUITECTURA_PROYECTO.md"):
        self.raiz = Path.cwd()
        self.nombre_proyecto = self.raiz.name
        self.archivo_salida = archivo_salida

        # Directorios de entorno, compilación o metadatos que contaminan el mapa visual
        self.excluir_directorios = {
            ".git", ".vscode", ".idea", "__pycache__", 
            "venv", "env", ".pytest_cache", "node_modules"
        }

        # Archivos generados dinámicamente o basura del SO
        self.excluir_archivos = {
            ".DS_Store", "Thumbs.db", "mapeador_estructura.py", self.archivo_salida
        }

        # Catálogo semántico para enriquecer la tabla volumétrica de la tesis
        self.diccionario_extensiones = {
            ".py": "Código fuente Python (Lógica de negocio / Scripts)",
            ".csv": "Conjuntos de datos estructurados (Respaldos léxicos)",
            ".md": "Documentación y reportes de ejecución",
            ".yml": "Orquestación de contenedores (Docker)",
            ".yaml": "Archivos de configuración estructurada",
            ".txt": "Manifiestos de dependencias y texto plano",
            ".env": "Variables de entorno locales (Secretos)",
            ".gitignore": "Reglas de exclusión de control de versiones",
            ".json": "Estructuras de intercambio de datos JSON",
            ".sql": "Consultas y esquemas DDL de Base de Datos",
            "[sin extensión]": "Archivos binarios, manifiestos o de sistema"
        }

    def _es_entrada_valida(self, item: Path) -> bool:
        """Filtro de inclusión/exclusíón de nodos del sistema de archivos."""
        nombre = item.name

        if item.is_dir():
            if nombre in self.excluir_directorios or nombre.startswith('.'):
                return False
            return True

        if item.is_file():
            if nombre in self.excluir_archivos:
                return False
            # Permite dotfiles vitales del proyecto (.env, .gitignore), bloquea los del SO (.DS_Store)
            if nombre.startswith('.') and nombre not in {'.env', '.gitignore', '.dockerignore'}:
                return False
            return True

        return False

    def _obtener_entradas_ordenadas(self, directorio: Path) -> list[Path]:
        """Obtiene el contenido de una carpeta: primero directorios (A-Z), luego archivos (A-Z)."""
        entradas = []
        try:
            for item in directorio.iterdir():
                if self._es_entrada_valida(item):
                    entradas.append(item)
        except PermissionError:
            pass

        directorios = sorted([e for e in entradas if e.is_dir()], key=lambda x: x.name.lower())
        archivos = sorted([e for e in entradas if e.is_file()], key=lambda x: x.name.lower())
        
        return directorios + archivos

    def _generar_rama_ascii(self, directorio: Path, prefijo: str = "") -> list[str]:
        """Motor recursivo de renderizado tipográfico tipificado."""
        lineas = []
        entradas = self._obtener_entradas_ordenadas(directorio)
        total = len(entradas)

        for i, item in enumerate(entradas):
            es_ultimo = (i == total - 1)
            conector = "└── " if es_ultimo else "├── "

            if item.is_dir():
                lineas.append(f"{prefijo}{conector}{item.name}/")
                extension_prefijo = "    " if es_ultimo else "│   "
                lineas.extend(self._generar_rama_ascii(item, prefijo + extension_prefijo))
            else:
                lineas.append(f"{prefijo}{conector}{item.name}")

        return lineas

    def _recolectar_metadatos_volumetricos(self) -> tuple[int, int, Counter]:
        """Realiza un barrido contable de elementos para el anexo cuantitativo."""
        total_dirs = 0
        total_archivos = 0
        conteo_extensiones = Counter()

        for raiz_dir, subdirs, archivos in os.walk(self.raiz):
            # Podar el árbol de os.walk in situ para no procesar carpetas prohibidas
            subdirs[:] = [
                d for d in subdirs 
                if d not in self.excluir_directorios and not d.startswith('.')
            ]

            total_dirs += len(subdirs)

            for archivo in archivos:
                ruta_simulada = Path(raiz_dir) / archivo
                if not self._es_entrada_valida(ruta_simulada):
                    continue

                total_archivos += 1

                if archivo.startswith('.'):
                    ext = archivo
                else:
                    sufijo = Path(archivo).suffix.lower()
                    ext = sufijo if sufijo else "[sin extensión]"

                conteo_extensiones[ext] += 1

        return total_dirs, total_archivos, conteo_extensiones

    def exportar_mapa(self):
        """Orquesta la recolección, el ensamblaje sintáctico y la escritura del Markdown."""
        print(f"\n🗺️  Indexando topología del proyecto [{self.nombre_proyecto}]...")

        arbol_visual = [f"{self.nombre_proyecto}/"] + self._generar_rama_ascii(self.raiz)
        c_dirs, c_archivos, conteo_ext = self._recolectar_metadatos_volumetricos()

        timestamp_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        md = [
            f"# 🗺️ Radiografía Estructural del Proyecto: `{self.nombre_proyecto}`\n",
            f"> **Fecha de escaneo:** {timestamp_utc} UTC  \n"
            f"> **Módulo generador:** `mapeador_estructura.py`  \n"
            f"> **Exclusiones aplicadas:** `venv/`, `.git/`, `__pycache__/`\n",
            "---\n",
            "## 1. Árbol Arquitectónico\n",
            "```text",
            *arbol_visual,
            "```\n",
            "## 2. Balance Volumétrico del Repositorio\n",
            "| Métricas de Estructura | Cantidad |",
            "| :--- | :---: |",
            f"| **Submódulos / Directorios** | {c_dirs:,} |",
            f"| **Archivos de proyecto** | {c_archivos:,} |",
            f"| **Total Nodos indexados** | {c_dirs + c_archivos:,} |\n",
            "### Desglose Tecnológico (Por extensión)\n",
            "| Extensión | Naturaleza del archivo dentro del sistema | Cantidad |",
            "| :---: | :--- | :---: |"
        ]

        for ext, cantidad in conteo_ext.most_common():
            descripcion = self.diccionario_extensiones.get(ext, "Archivo genérico / de recurso secundario")
            md.append(f"| `{ext}` | {descripcion} | {cantidad} |")

        md.append("\n---\n*Generado automáticamente para el control de trazabilidad del SGC.*")

        ruta_destino = self.raiz / self.archivo_salida
        with open(ruta_destino, "w", encoding="utf-8") as f:
            f.write("\n".join(md))

        print(f"✅ Mapa estructural generado exitosamente en: -> [ {self.archivo_salida} ]\n")


if __name__ == "__main__":
    mapeador = MapeadorProyecto()
    mapeador.exportar_mapa()