import sys
import os

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_dir)
os.chdir(backend_dir)

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

def fetch_html(id_entrada: int):
    url = f"https://diperu.apl.org.pe/buscar?entrada={id_entrada}"
    html = ""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="es-PE"
        )
        page = context.new_page()
        try:
            page.goto(url, wait_until="commit", timeout=30000)
            try:
                page.wait_for_selector("div#ListaEntradaIndex h4.text-red b", state="attached", timeout=15000)
            except PlaywrightTimeout:
                page.reload(wait_until="commit", timeout=30000)
                page.wait_for_selector("div#ListaEntradaIndex h4.text-red b", state="attached", timeout=15000)
            try:
                page.wait_for_selector("div#ListaEntradaIndex a h5.text-red", state="attached", timeout=4000)
            except:
                pass
            page.wait_for_timeout(250)
            html = page.content()
        except Exception as e:
            browser.close()
            print(f"Error_Nav: {e}", file=sys.stderr)
            sys.exit(1)
        browser.close()
        
    soup = BeautifulSoup(html, "html.parser")
    cont = soup.find(id="ListaEntradaIndex")
    if cont is None:
        print("Error_Parse: No se encontró el contenedor div#ListaEntradaIndex", file=sys.stderr)
        sys.exit(1)
        
    # Eliminar botones de navegación/compartir para dejar solo el contenido limpio
    for nav in cont.find_all("div", class_="row", style=lambda s: s and "margin-top" in s):
        nav.decompose()
    for nav in cont.find_all("div", class_="col-sm-2 text-right"):
        nav.decompose()
    for a in cont.find_all("a"):
        if not a.get("href") or "buscar?entrada=" not in a.get("href"):
            if a.parent:
                a.decompose()
            
    # Imprimir el HTML interno o externo del contenedor
    print(str(cont))

if __name__ == "__main__":
    id_entrada = int(sys.argv[1])
    fetch_html(id_entrada)
