"""Record comprehensive getting-started tutorial video using Playwright with visible cursor.

Full end-to-end flow:
  1. Landing page → browse estimates
  2. Create new estimate (with visible dropdown selections)
  3. Add workload manually
  4. View cost summary
  5. Use AI Assistant
  6. Export to Excel
  7. Click Help → Documentation
  8. Show docs site
"""
import asyncio
import subprocess
import sys
import os
from playwright.async_api import async_playwright

sys.path.insert(0, os.path.dirname(__file__))
from cursor import CURSOR_INJECT, inject_cursor, smooth_move, move_to, click_on

APP_URL = "http://localhost:8000"
ESTIMATE_URL = f"{APP_URL}/calculator/2fc50a70-060d-49e2-b845-eb8c055f4aeb"
VIDEO_DIR = os.path.dirname(__file__)


async def visible_select(page, select_locator, label=None, index=None):
    """Select an option with visible interaction: click to focus, pause, then select."""
    await move_to(page, select_locator, pause=300)
    await select_locator.click()
    await page.wait_for_timeout(400)
    if label:
        await select_locator.select_option(label=label)
    elif index is not None:
        await select_locator.select_option(index=index)
    await page.wait_for_timeout(600)


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

        # ─── Scene 1: Landing page — browse estimates ───
        print("  Scene 1: Landing page")
        await page.goto(APP_URL, wait_until="load", timeout=60000)
        await page.wait_for_timeout(3000)
        await inject_cursor(page)
        await page.mouse.move(0, 400)
        await page.wait_for_timeout(300)

        # Pan across the page
        await smooth_move(page, 640, 300)
        await page.wait_for_timeout(800)

        # Hover over estimate cards/rows if visible
        try:
            est_link = page.locator('a:has-text("Estimates")').first
            await move_to(page, est_link, pause=500)
        except:
            pass

        # ─── Scene 2: Navigate to create estimate ───
        print("  Scene 2: Create estimate")
        new_est_link = page.locator('a:has-text("New Estimate")').first
        await move_to(page, new_est_link, pause=400)
        await new_est_link.click()
        await page.wait_for_timeout(2500)
        await inject_cursor(page)
        await page.mouse.move(0, 400)
        await page.wait_for_timeout(300)

        # Wait for calculator page
        try:
            await page.wait_for_selector('select', timeout=10000)
        except:
            pass
        await page.wait_for_timeout(1000)

        # Type estimate name
        name_field = page.get_by_role("textbox").first
        await move_to(page, name_field, pause=400)
        await name_field.click(click_count=3)
        await page.keyboard.type("Q4 Data Platform Estimate", delay=40)
        await page.wait_for_timeout(500)

        # Select region with visible dropdown focus
        region_select = page.locator('select').first
        await move_to(page, region_select, pause=300)
        await region_select.click()
        await page.wait_for_timeout(400)
        await region_select.select_option(value="us-east-1")
        await page.wait_for_timeout(600)

        # Select tier with visible dropdown focus
        tier_select = page.locator('select').nth(1)
        await move_to(page, tier_select, pause=300)
        await tier_select.click()
        await page.wait_for_timeout(400)
        await tier_select.select_option(value="premium")
        await page.wait_for_timeout(600)

        # Click Create Estimate
        create_btn = page.locator('button:has-text("Create Estimate")').first
        await click_on(page, create_btn, pause=2500)
        await inject_cursor(page)
        await page.mouse.move(0, 400)
        await page.wait_for_timeout(500)

        # ─── Scene 3: Add workload ───
        print("  Scene 3: Add workload")
        try:
            await page.wait_for_selector('button:has-text("Add Workload")', timeout=15000)
        except:
            pass
        await page.wait_for_timeout(2000)

        add_btn = page.locator('button:has-text("Add Workload")').first
        await click_on(page, add_btn, pause=1000)

        # Fill workload name
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
                    await page.keyboard.type("ML Training Pipeline", delay=40)
                    await page.wait_for_timeout(400)
                    break
            except:
                continue

        # Select workload type
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

        await page.wait_for_timeout(1500)

        # ─── Scene 4: View cost summary ───
        print("  Scene 4: Cost summary")
        try:
            monthly = page.locator('text=Monthly Estimate').first
            await move_to(page, monthly, pause=600)
        except:
            pass

        try:
            dbu = page.locator('text=DBU COST').first
            await move_to(page, dbu, pause=600)
        except:
            pass

        try:
            vm = page.locator('text=VM COST').first
            await move_to(page, vm, pause=600)
        except:
            pass

        await page.wait_for_timeout(800)

        # ─── Scene 5: AI Assistant ───
        print("  Scene 5: AI Assistant")
        chat_input = page.locator('textarea').last
        try:
            await move_to(page, chat_input, pause=400, timeout=5000)
            await chat_input.click()
            await page.keyboard.type("Summarize this estimate", delay=45)
            await page.wait_for_timeout(500)
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(5000)
        except Exception as e:
            print(f"  [skip] AI: {e}")
            await page.wait_for_timeout(1000)

        # ─── Scene 6: Export to Excel ───
        print("  Scene 6: Export to Excel")
        excel_btn = page.locator('button:has-text("Excel")').first
        try:
            await move_to(page, excel_btn, pause=500)
            await excel_btn.click()
            await page.wait_for_timeout(1500)
        except:
            pass

        # ─── Scene 7: Help → Documentation ───
        print("  Scene 7: Help → Documentation")
        help_btn = page.locator('button[title="Help & Feedback"], button:has-text("Help")').first
        try:
            await click_on(page, help_btn, pause=800, timeout=5000)

            # Click Documentation link
            doc_link = page.locator('a[href="/docs/"]').first
            await move_to(page, doc_link, pause=500, timeout=3000)
            # Don't actually click (opens new tab) — just hover to show the link
            await page.wait_for_timeout(1000)
        except Exception as e:
            print(f"  [skip] Help: {e}")

        await page.wait_for_timeout(1000)

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
    size = os.path.getsize(mp4_path) / 1024
    print(f"  → getting-started-tutorial.mp4 ({size:.0f}KB)")

    # Also save as WebM
    webm_path = os.path.join(VIDEO_DIR, "getting-started-tutorial.webm")
    subprocess.run([
        "ffmpeg", "-y", "-i", video_path,
        "-c:v", "libvpx-vp9", "-crf", "30", "-b:v", "0",
        "-vf", "scale=1280:800",
        "-an",
        webm_path
    ], capture_output=True)
    size = os.path.getsize(webm_path) / 1024
    print(f"  → getting-started-tutorial.webm ({size:.0f}KB)")

    # Clean temp webm
    if os.path.exists(video_path) and video_path != webm_path:
        os.remove(video_path)

    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
