"""Record comprehensive getting-started tutorial video (~3-4 minutes).

Full end-to-end flow with subtitles describing each action:
  1. Landing page — browse estimates
  2. Create new estimate (with visible dropdown selections)
  3. Add workload manually
  4. View cost summary
  5. Use AI Assistant
  6. Export to Excel
  7. Drag and drop reorder
  8. Help & Documentation
"""
import asyncio
import subprocess
import sys
import os
from playwright.async_api import async_playwright

sys.path.insert(0, os.path.dirname(__file__))
from cursor import (
    CURSOR_INJECT, SUBTITLE_INJECT,
    inject_cursor, inject_subtitle,
    smooth_move, move_to, click_on,
    show_subtitle, hide_subtitle,
)

APP_URL = "http://localhost:8000"
# Pre-seeded estimate with workloads for scenes 4-8
ESTIMATE_URL = f"{APP_URL}/calculator/2fc50a70-060d-49e2-b845-eb8c055f4aeb"
VIDEO_DIR = os.path.dirname(__file__)


async def visible_select(page, select_locator, label=None, value=None, index=None):
    """Select an option with visible interaction: click to focus, pause, then select."""
    await move_to(page, select_locator, pause=300)
    await select_locator.click()
    await page.wait_for_timeout(500)
    if label:
        await select_locator.select_option(label=label)
    elif value:
        await select_locator.select_option(value=value)
    elif index is not None:
        await select_locator.select_option(index=index)
    await page.wait_for_timeout(800)


async def setup_page(page):
    """Inject cursor + subtitle overlays and reset mouse position."""
    await inject_cursor(page)
    await inject_subtitle(page)
    await page.mouse.move(0, 400)
    await page.wait_for_timeout(300)


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            record_video_dir=VIDEO_DIR,
            record_video_size={"width": 1280, "height": 800},
        )
        page = await context.new_page()
        await page.add_init_script(CURSOR_INJECT)
        await page.add_init_script(SUBTITLE_INJECT)

        # ═══════════════════════════════════════════════════
        # Scene 1: Landing Page (~15s)
        # ═══════════════════════════════════════════════════
        print("  Scene 1: Landing page")
        await page.goto(APP_URL, wait_until="load", timeout=60000)
        await page.wait_for_timeout(3000)
        await setup_page(page)

        await show_subtitle(page, "Welcome to Lakemeter — Databricks Pricing Calculator", 5000)

        # Pan across the page
        await smooth_move(page, 640, 300)
        await page.wait_for_timeout(2000)
        await smooth_move(page, 640, 500)
        await page.wait_for_timeout(2000)

        # Hover estimates nav
        try:
            est_link = page.locator('a:has-text("Estimates")').first
            await move_to(page, est_link, pause=800)
        except:
            pass

        await show_subtitle(page, "The estimates page shows all your pricing estimates", 5000)
        await hide_subtitle(page)
        await page.wait_for_timeout(1000)

        # ═══════════════════════════════════════════════════
        # Scene 2: Create Estimate (~35s)
        # ═══════════════════════════════════════════════════
        print("  Scene 2: Create estimate")
        await show_subtitle(page, "Let's create a new pricing estimate", 3000)

        new_est_link = page.locator('a:has-text("New Estimate")').first
        await move_to(page, new_est_link, pause=500)
        await new_est_link.click()
        await page.wait_for_timeout(3000)
        await setup_page(page)

        # Wait for calculator page and regions to load
        try:
            await page.wait_for_selector('select', timeout=10000)
        except:
            pass
        # Regions load asynchronously — wait for them
        for _ in range(20):
            opt_count = await page.locator('select').first.evaluate(
                '(el) => el.options.length'
            )
            if opt_count > 5:
                break
            await page.wait_for_timeout(500)
        await page.wait_for_timeout(1000)

        # Type estimate name
        await show_subtitle(page, "Naming the estimate", 1500)
        name_field = page.get_by_role("textbox").first
        await move_to(page, name_field, pause=400)
        await name_field.click(click_count=3)
        await page.keyboard.type("Q4 Data Platform Estimate", delay=50)
        await page.wait_for_timeout(800)

        # Select region with visible dropdown
        await show_subtitle(page, "Selecting the AWS cloud region", 1500)
        region_select = page.locator('select').first
        await visible_select(page, region_select, value="us-east-1")
        await page.wait_for_timeout(500)

        # Select tier with visible dropdown
        await show_subtitle(page, "Choosing the Premium pricing tier", 1500)
        tier_select = page.locator('select').nth(1)
        await visible_select(page, tier_select, value="premium")
        await page.wait_for_timeout(500)

        # Click Create Estimate
        await show_subtitle(page, "Creating the estimate", 1500)
        create_btn = page.locator('button:has-text("Create Estimate")').first
        await click_on(page, create_btn, pause=500)

        await show_subtitle(page, "Estimate created! Now let's add workloads", 5000)
        await page.wait_for_timeout(4000)
        await setup_page(page)
        await hide_subtitle(page)

        # ═══════════════════════════════════════════════════
        # Scene 3: Add Workload (~40s)
        # ═══════════════════════════════════════════════════
        print("  Scene 3: Add workload")
        try:
            await page.wait_for_selector('button:has-text("Add Workload")', timeout=15000)
        except:
            pass
        await page.wait_for_timeout(2000)

        await show_subtitle(page, "Adding a workload manually", 2000)

        add_btn = page.locator('button:has-text("Add Workload")').first
        await click_on(page, add_btn, pause=1500)

        # Fill workload name
        await show_subtitle(page, "Entering the workload name", 1500)
        await page.wait_for_timeout(500)
        all_inputs = page.locator('input[type="text"]')
        count = await all_inputs.count()
        for i in range(count):
            try:
                inp = all_inputs.nth(i)
                box = await inp.bounding_box(timeout=1000)
                if box and box["y"] > 100:
                    await move_to(page, inp, pause=300)
                    await inp.click()
                    await inp.fill("")
                    await page.keyboard.type("ML Training Pipeline", delay=50)
                    await page.wait_for_timeout(600)
                    break
            except:
                continue

        # Select workload type
        await show_subtitle(page, "Selecting the workload type", 1500)
        selects = page.locator('select')
        sel_count = await selects.count()
        if sel_count > 0:
            for i in range(sel_count):
                try:
                    sel = selects.nth(i)
                    box = await sel.bounding_box(timeout=1000)
                    if box and box["y"] > 100:
                        await visible_select(page, sel, index=2)
                        break
                except:
                    continue

        await show_subtitle(page, "Configuring workload parameters", 2000)
        await page.wait_for_timeout(2000)

        await show_subtitle(page, "Cost is calculated automatically as you configure", 4000)
        await page.wait_for_timeout(3000)
        await hide_subtitle(page)

        # ═══════════════════════════════════════════════════
        # Scene 4: Cost Summary (~20s)
        # Navigate to pre-seeded estimate with workloads
        # ═══════════════════════════════════════════════════
        print("  Scene 4: Cost summary")
        await show_subtitle(page, "Now let's look at an estimate with multiple workloads", 4500)
        await page.goto(ESTIMATE_URL, wait_until="load", timeout=60000)
        await page.wait_for_timeout(5000)
        await setup_page(page)
        await show_subtitle(page, "Reviewing the cost breakdown", 3000)

        try:
            monthly = page.locator('text=Monthly Estimate').first
            await move_to(page, monthly, pause=800)
        except:
            pass

        await show_subtitle(page, "Monthly estimate includes DBU and VM costs", 3000)

        try:
            dbu = page.locator('text=DBU COST').first
            await move_to(page, dbu, pause=800)
        except:
            pass

        try:
            vm = page.locator('text=VM COST').first
            await move_to(page, vm, pause=800)
        except:
            pass

        await page.wait_for_timeout(1000)
        await hide_subtitle(page)

        # ═══════════════════════════════════════════════════
        # Scene 5: AI Assistant (~50s)
        # ═══════════════════════════════════════════════════
        print("  Scene 5: AI Assistant")
        await show_subtitle(page, "Using the AI pricing assistant", 2500)

        # Try clicking Optimize quick action
        optimize_btn = page.locator('button:has-text("Optimize")').first
        try:
            await click_on(page, optimize_btn, pause=500, timeout=5000)
            await show_subtitle(page, "Asking for optimization suggestions", 2500)
            # Wait for AI streaming response
            await page.wait_for_timeout(10000)
            await show_subtitle(page, "AI analyzes workloads and provides cost-saving recommendations", 5000)
        except Exception as e:
            print(f"  [skip] Optimize: {e}")
            await page.wait_for_timeout(1000)

        # Type a custom question
        await show_subtitle(page, "You can also ask custom questions", 2000)
        chat_input = page.locator('textarea').last
        try:
            await move_to(page, chat_input, pause=500, timeout=5000)
            await chat_input.click()
            await page.keyboard.type("What is the total monthly cost?", delay=50)
            await page.wait_for_timeout(800)
            await page.keyboard.press("Enter")
            await show_subtitle(page, "The assistant responds with detailed cost information", 4000)
            await page.wait_for_timeout(12000)
        except Exception as e:
            print(f"  [skip] AI chat: {e}")
            await page.wait_for_timeout(1000)

        await hide_subtitle(page)
        await page.wait_for_timeout(500)

        # ═══════════════════════════════════════════════════
        # Scene 6: Export to Excel (~15s)
        # ═══════════════════════════════════════════════════
        print("  Scene 6: Export to Excel")
        await show_subtitle(page, "Exporting the estimate to Excel", 3000)

        excel_btn = page.locator('button:has-text("Excel")').first
        try:
            await move_to(page, excel_btn, pause=600)
            await excel_btn.click()
            await page.wait_for_timeout(2000)
            await show_subtitle(page, "Excel file downloaded with full cost breakdown", 2500)
        except:
            pass

        await hide_subtitle(page)
        await page.wait_for_timeout(500)

        # ═══════════════════════════════════════════════════
        # Scene 7: Drag and Drop (~20s)
        # ═══════════════════════════════════════════════════
        print("  Scene 7: Drag and drop")
        await show_subtitle(page, "Reordering workloads with drag and drop", 3500)

        first_wl = page.locator('[aria-roledescription="sortable"]').first
        try:
            box = await first_wl.bounding_box(timeout=5000)
            if box:
                handle_x = box["x"] + 20
                handle_y = box["y"] + box["height"] / 2
                await smooth_move(page, handle_x, handle_y)
                await page.wait_for_timeout(600)

                await page.mouse.down()
                await page.wait_for_timeout(400)

                # Drag down slowly
                for i in range(50):
                    await page.mouse.move(handle_x, handle_y + (i * 2), steps=1)
                    await page.wait_for_timeout(25)
                await page.wait_for_timeout(500)

                await page.mouse.up()
                await show_subtitle(page, "Workload order saved automatically", 2000)
                await page.wait_for_timeout(1000)
        except Exception as e:
            print(f"  [skip] Drag: {e}")

        await hide_subtitle(page)
        await page.wait_for_timeout(500)

        # ═══════════════════════════════════════════════════
        # Scene 8: Help & Documentation (~15s)
        # ═══════════════════════════════════════════════════
        print("  Scene 8: Help & Documentation")
        await show_subtitle(page, "Accessing help, documentation, and pricing info", 3500)

        help_btn = page.locator('button[title="Help & Feedback"], button:has-text("Help")').first
        try:
            await click_on(page, help_btn, pause=1000, timeout=5000)

            # Hover Documentation link
            doc_link = page.locator('a[href="/docs/"]').first
            await move_to(page, doc_link, pause=1000, timeout=3000)

            await show_subtitle(page, "Documentation includes guides for every feature", 2500)

            # Hover Pricing link
            pricing_link = page.locator('a[href*="databricks.com/product/pricing"]').first
            await move_to(page, pricing_link, pause=1000, timeout=3000)

        except Exception as e:
            print(f"  [skip] Help: {e}")

        await show_subtitle(page, "That's Lakemeter — start estimating your Databricks costs today!", 5000)
        await hide_subtitle(page)
        await page.wait_for_timeout(2000)

        # ─── Finish ───
        video_path = await page.video.path()
        await context.close()
        await browser.close()

    # Convert WebM to MP4
    mp4_path = os.path.join(VIDEO_DIR, "getting-started-tutorial.mp4")
    print(f"  Converting → MP4...")
    subprocess.run([
        "ffmpeg", "-y", "-i", video_path,
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-vf", "scale=1280:800",
        "-movflags", "+faststart",
        "-an",
        mp4_path
    ], capture_output=True)
    size = os.path.getsize(mp4_path) / (1024 * 1024)
    print(f"  → getting-started-tutorial.mp4 ({size:.1f}MB)")

    # Also save as WebM
    webm_path = os.path.join(VIDEO_DIR, "getting-started-tutorial.webm")
    subprocess.run([
        "ffmpeg", "-y", "-i", video_path,
        "-c:v", "libvpx-vp9", "-crf", "30", "-b:v", "0",
        "-vf", "scale=1280:800",
        "-an",
        webm_path
    ], capture_output=True)
    size = os.path.getsize(webm_path) / (1024 * 1024)
    print(f"  → getting-started-tutorial.webm ({size:.1f}MB)")

    # Clean temp webm
    if os.path.exists(video_path) and video_path != webm_path:
        os.remove(video_path)

    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
