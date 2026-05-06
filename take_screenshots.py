"""Screenshots complets de documentation (equiv. basesecrets style)."""
import asyncio, os
from playwright.async_api import async_playwright

BASE = "http://localhost:8001"
OUT  = os.path.join(os.path.dirname(__file__), "screenshots")
os.makedirs(OUT, exist_ok=True)

W, H = 1280, 800

async def shot(page, name, full=False):
    path = os.path.join(OUT, name)
    await page.wait_for_load_state("networkidle")
    await page.screenshot(path=path, full_page=full)
    print(f"  {name}")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={"width": W, "height": H})
        page = await ctx.new_page()

        # ── 01 Login ───────────────────────────────────────────────────────
        await page.goto(f"{BASE}/login")
        await shot(page, "01_login.png")

        # ── Connexion ──────────────────────────────────────────────────────
        await page.fill("input[name=username]", "admin")
        await page.fill("input[name=password]", "noukiebokosse2026")
        await page.click("button[type=submit]")
        # fallback si mot de passe wrong
        if "/login" in page.url:
            await page.fill("input[name=username]", "admin")
            await page.fill("input[name=password]", "noukiebogosse2026")
            await page.click("button[type=submit]")
        await page.wait_for_url(f"{BASE}/")

        # ── 02 Dashboard ───────────────────────────────────────────────────
        await shot(page, "02_dashboard.png")

        # ── 03 Liste habilitations ─────────────────────────────────────────
        await page.goto(f"{BASE}/habilitations/")
        await shot(page, "03_habilitations_list.png")

        # ── 04 Détail habilitation ─────────────────────────────────────────
        await page.goto(f"{BASE}/habilitations/1")
        await shot(page, "04_habilitation_detail.png")

        # ── 05 Formulaire modification ─────────────────────────────────────
        await page.goto(f"{BASE}/habilitations/1/edit")
        await shot(page, "05_habilitation_edit.png")

        # ── 06 Nouvelle habilitation ───────────────────────────────────────
        await page.goto(f"{BASE}/habilitations/new")
        await shot(page, "06_habilitation_new.png")

        # ── 07 Historique d'une habilitation ──────────────────────────────
        await page.goto(f"{BASE}/habilitations/1/history")
        await shot(page, "07_habilitation_history.png")

        # ── 08 Audit ──────────────────────────────────────────────────────
        await page.goto(f"{BASE}/audit/")
        await shot(page, "08_audit.png")

        # ── 09 Référentiels — statuts ──────────────────────────────────────
        await page.goto(f"{BASE}/admin/referentiels")
        await shot(page, "09_referentiels.png")

        # ── 10 Référentiels — champs perso (dernier onglet) ──────────────
        await page.goto(f"{BASE}/admin/referentiels")
        await page.wait_for_load_state("networkidle")
        await page.evaluate("showTab('filiales')")
        await page.wait_for_timeout(300)
        await shot(page, "10_referentiels_filiales.png")

        # ── 11 Import CSV/Excel ────────────────────────────────────────────
        await page.goto(f"{BASE}/import/")
        await shot(page, "11_import.png")

        # ── 12 Utilisateurs ────────────────────────────────────────────────
        await page.goto(f"{BASE}/users/")
        await shot(page, "12_users.png")

        # ── 13 Journal d'activité ──────────────────────────────────────────
        await page.goto(f"{BASE}/activity/")
        await shot(page, "13_activity.png")

        # ── 14 Paramètres — thème + logo ──────────────────────────────────
        await page.goto(f"{BASE}/admin/settings")
        await shot(page, "14_settings_theme.png")

        # ── 15 Paramètres — LDAP (scroll bas) ─────────────────────────────
        await page.goto(f"{BASE}/admin/settings")
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(300)
        await shot(page, "15_settings_ldap.png")

        # ── 16 Guide ──────────────────────────────────────────────────────
        await page.goto(f"{BASE}/guide")
        await shot(page, "16_guide.png")

        await browser.close()
        print(f"\nDone — {len(os.listdir(OUT))} screenshots dans screenshots/")

asyncio.run(main())
