"""Record getting-started tutorial video using Playwright with visible cursor."""
import asyncio
import subprocess
import sys
import os
from playwright.async_api import async_playwright

sys.path.insert(0, os.path.dirname(__file__))
from cursor import CURSOR_INJECT, inject_cursor, smooth_move, move_to, click_on

APP_URL = "http://localhost:8000"
VIDEO_DIR = os.path.dirname(__file__)


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

        # ─── Scene 1: Landing page ───
        print("  Scene 1: Landing page")
        await page.goto(APP_URL, wait_until="load", timeout=60000)
        await page.wait_for_timeout(3000)
        await inject_cursor(page)
        await page.mouse.move(0, 400)
        await page.wait_for_timeout(300)

        # Pan across the landing page
        await smooth_move(page, 640, 300)
        await page.wait_for_timeout(800)

        # Move to Estimates nav
        estimates_link = page.locator('a:has-text("Estimates")').first
        await move_to(page, estimates_link, pause=600)

        # Move to New Estimate
        new_est_link = page.locator('a:has-text("New Estimate")').first
        await move_to(page, new_est_link, pause=400)
        await new_est_link.click()
        await page.wait_for_timeout(2000)
        await inject_cursor(page)
        await page.mouse.move(0, 400)
        await page.wait_for_timeout(300)

        # ─── Scene 2: Create Estimate ───
        print("  Scene 2: Create estimate")
        # Wait for calculator page to load
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

        # Select region
        region_select = page.locator('select').first
        await move_to(page, region_select, pause=300)
        await region_select.select_option(label="us-east-1 (US_EAST_N_VIRGINIA)")
        await page.wait_for_timeout(500)

        # Select tier
        tier_select = page.locator('select').nth(1)
        await move_to(page, tier_select, pause=300)
        await tier_select.select_option(label="Premium")
        await page.wait_for_timeout(500)

        # Click Create Estimate
        create_btn = page.locator('button:has-text("Create Estimate")').first
        await click_on(page, create_btn, pause=2000)
        await inject_cursor(page)
        await page.mouse.move(0, 400)
        await page.wait_for_timeout(500)

        # ─── Scene 3: Add Workload ───
        print("  Scene 3: Add workload")
        # Wait for estimate page to load
        try:
            await page.wait_for_selector('button:has-text("Add Workload")', timeout=15000)
        except:
            pass
        await page.wait_for_timeout(2000)

        # Click Add Workload
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
                        await move_to(page, sel, pause=300)
                        await sel.select_option(index=2)
                        await page.wait_for_timeout(500)
                        break
                except:
                    continue

        await page.wait_for_timeout(1500)

        # ─── Scene 4: View Cost Summary ───
        print("  Scene 4: Cost summary")
        # Hover over cost breakdown elements
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

        await page.wait_for_timeout(1000)

        # ─── Scene 5: Export to Excel ───
        print("  Scene 5: Export")
        excel_btn = page.locator('button:has-text("Excel")').first
        try:
            await move_to(page, excel_btn, pause=600)
            await excel_btn.click()
            await page.wait_for_timeout(1500)
        except:
            pass

        await page.wait_for_timeout(1000)

        # ─── Finish ───
        video_path = await page.video.path()
        await context.close()
        await browser.close()

    # Convert WebM to MP4
    mp4_path = os.path.join(VIDEO_DIR, "getting-started-tutorial.mp4")
    print(f"  Converting {video_path} → MP4...")
    subprocess.run([
        "ffmpeg", "-y", "-i", video_path,
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-vf", "scale=1280:800",
        "-movflags", "+faststart",
        "-an",  # no audio
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
