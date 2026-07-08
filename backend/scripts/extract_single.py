import sys
import os

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_dir)
os.chdir(backend_dir)

from app.nlp.scraper import parsear_entrada, extraer_texto_auditable
from app.core.database import SessionLocal, ahora_utc
from app.models import ControlExtraccionLema, RegistroLexicoCrudo, ESTADO_COMPLETA
import uuid
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

def extract(id_entrada: int, lema: str):
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
            print(f"Error: {e}")
            sys.exit(1)
        browser.close()
        
    rlc = parsear_entrada(html, id_entrada, lema)
    texto = extraer_texto_auditable(html)
    
    if not rlc or (not rlc.get("acepciones") and not rlc.get("sublemas")):
        print("Error: No se encontraron acepciones parseables en el HTML")
        sys.exit(1)
        
    with SessionLocal() as db:
        control = db.query(ControlExtraccionLema).filter_by(url_origen=url).first()
        if not control:
            control = ControlExtraccionLema(
                id_lema=uuid.uuid4(),
                lema=lema,
                url_origen=url
            )
            db.add(control)
            db.commit()
            
        rlc_db = db.query(RegistroLexicoCrudo).filter_by(id_entrada=id_entrada).first()
        if not rlc_db:
            rlc_db = RegistroLexicoCrudo(
                id_rlc=uuid.uuid4(),
                id_lema=control.id_lema,
                id_entrada=id_entrada,
                lema=lema
            )
            db.add(rlc_db)
            
        rlc_db.num_acepciones = rlc["conteo"]["acepciones_lema"]
        rlc_db.rlc_json = rlc
        rlc_db.texto_plano = texto
        rlc_db.fecha_extraccion = ahora_utc()
        
        control.estado_seci = ESTADO_COMPLETA
        control.ultima_actualizacion = ahora_utc()
        db.commit()
        print("SUCCESS")

if __name__ == "__main__":
    id_entrada = int(sys.argv[1])
    lema = sys.argv[2]
    extract(id_entrada, lema)
