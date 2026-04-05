"""Record comprehensive getting-started tutorial video (~4-5 minutes) with AI voiceover.

Revised scene order:
  1. Landing page — browse estimates
  2. Help & Documentation (early, per user request)
  3. Create new estimate (with visible dropdown selections)
  4. Add two workloads manually with full configuration
  5. View cost summary / calculations
  6. AI Assistant — configure a workload via chat
  7. Export to Excel
  8. Closing
"""
import asyncio
import subprocess
import sys
import os
import tempfile
import edge_tts
from playwright.async_api import async_playwright

sys.path.insert(0, os.path.dirname(__file__))
from cursor import (
    CURSOR_INJECT, SUBTITLE_INJECT,
    inject_cursor, inject_subtitle,
    smooth_move, move_to, click_on,
    show_subtitle, hide_subtitle,
    visual_select,
)

APP_URL = "http://localhost:8000"
# Pre-seeded estimate with workloads for AI scene
ESTIMATE_URL = f"{APP_URL}/calculator/2fc50a70-060d-49e2-b845-eb8c055f4aeb"
VIDEO_DIR = os.path.dirname(__file__)
VOICE = "en-US-GuyNeural"  # Natural male US English voice
AUDIO_DIR = os.path.join(VIDEO_DIR, "_audio_clips")


# ─── TTS helpers ───

async def generate_voiceover_clips(narrations: list[tuple[str, str]]):
    """Pre-generate all voiceover audio clips using edge-tts.

    Args:
        narrations: list of (clip_id, text) tuples
    """
    os.makedirs(AUDIO_DIR, exist_ok=True)
    for clip_id, text in narrations:
        path = os.path.join(AUDIO_DIR, f"{clip_id}.mp3")
        if os.path.exists(path):
            continue
        communicate = edge_tts.Communicate(text, VOICE, rate="-5%")
        await communicate.save(path)
        print(f"    [tts] {clip_id}: {text[:50]}...")


def get_clip_duration(clip_id: str) -> float:
    """Get duration of an audio clip in seconds."""
    path = os.path.join(AUDIO_DIR, f"{clip_id}.mp3")
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


def get_clip_duration_ms(clip_id: str) -> int:
    """Get duration of an audio clip in milliseconds."""
    return int(get_clip_duration(clip_id) * 1000) + 300  # add 300ms buffer


async def setup_page(page):
    """Inject cursor + subtitle overlays and reset mouse position."""
    await inject_cursor(page)
    await inject_subtitle(page)
    await page.mouse.move(0, 400)
    await page.wait_for_timeout(300)


async def wait_for_regions(page):
    """Wait for region dropdown to load options asynchronously."""
    for _ in range(30):
        opt_count = await page.locator('select').first.evaluate(
            '(el) => el.options.length'
        )
        if opt_count > 5:
            break
        await page.wait_for_timeout(500)
    await page.wait_for_timeout(500)


async def main():
    # ─── Pre-generate all voiceover clips ───
    print("Generating voiceover clips...")
    narrations = [
        # Scene 1: Landing
        ("s1_welcome", "Welcome to Lakemeter, the Databricks pricing calculator. "
                       "This tool helps you estimate costs for any Databricks workload across AWS, Azure, and GCP."),
        ("s1_estimates", "The estimates page shows all your saved pricing estimates. "
                         "You can filter by cloud provider, search by name, and drag to reorder."),
        # Scene 2: Help & Docs
        ("s2_help", "Before we create an estimate, let's look at the help and documentation options."),
        ("s2_docs", "The documentation site includes guides for every feature — "
                    "from creating estimates to configuring workloads and using the AI assistant."),
        ("s2_pricing", "You can also access Databricks official pricing directly from here."),
        # Scene 3: Create Estimate
        ("s3_create", "Now let's create a new pricing estimate."),
        ("s3_name", "First, we'll name our estimate. This helps organize multiple scenarios."),
        ("s3_region", "Next, we select the cloud region. The pricing varies by region."),
        ("s3_tier", "Then we choose the Databricks pricing tier — Standard, Premium, or Enterprise."),
        ("s3_done", "Great — the estimate is created. Now let's add some workloads."),
        # Scene 4: Add Workloads
        ("s4_add1", "Let's add our first workload — a Lakeflow Jobs compute cluster for ETL pipelines."),
        ("s4_type1", "We select the workload type from the dropdown."),
        ("s4_config1", "Now we configure the instance type, number of workers, and usage parameters."),
        ("s4_cost1", "The cost is calculated automatically as you configure each parameter."),
        ("s4_add2", "Let's add a second workload — a Databricks SQL warehouse for analytics."),
        ("s4_type2", "This time we'll select Databricks SQL."),
        ("s4_config2", "For SQL warehouses, we configure the warehouse size and type."),
        ("s4_cost2", "Both workloads now show their individual cost breakdowns."),
        # Scene 5: Cost Summary
        ("s5_summary", "The cost summary panel on the right shows the total monthly estimate, "
                       "broken down by DBU cost and VM cost."),
        ("s5_detail", "Each workload's contribution to the total is displayed with a percentage bar, "
                      "making it easy to identify cost drivers."),
        # Scene 6: AI Assistant
        ("s6_intro", "Now let's use the AI assistant to add a workload. "
                     "The assistant can configure complex workloads through natural conversation."),
        ("s6_ask", "We'll ask the AI to help set up a Foundation Model API workload "
                   "using Claude Opus for our application."),
        ("s6_response", "The AI analyzes our request and proposes a complete workload configuration. "
                        "We can review the details and confirm to add it to our estimate."),
        # Scene 7: Export
        ("s7_export", "Finally, you can export any estimate to Excel with a full cost breakdown, "
                      "including SKU details, token rates, and VM pricing."),
        # Scene 8: Closing
        ("s8_close", "That's Lakemeter — start estimating your Databricks costs today. "
                     "Visit the documentation for more detailed guides on every feature."),
    ]
    await generate_voiceover_clips(narrations)

    # ─── Record video ───
    print("Recording video...")
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
        # Scene 1: Landing Page
        # ═══════════════════════════════════════════════════
        print("  Scene 1: Landing page")
        await page.goto(APP_URL, wait_until="load", timeout=60000)
        await page.wait_for_timeout(3000)
        await setup_page(page)

        dur = get_clip_duration_ms("s1_welcome")
        await show_subtitle(page, "Welcome to Lakemeter — Databricks Pricing Calculator", dur)

        # Pan across the page
        await smooth_move(page, 640, 300)
        await page.wait_for_timeout(1500)
        await smooth_move(page, 640, 500)
        await page.wait_for_timeout(1500)

        dur = get_clip_duration_ms("s1_estimates")
        await show_subtitle(page, "Browse and manage all your pricing estimates", dur)

        # Hover estimates nav
        try:
            est_link = page.locator('a:has-text("Estimates")').first
            await move_to(page, est_link, pause=800)
        except:
            pass

        await hide_subtitle(page)
        await page.wait_for_timeout(500)

        # ═══════════════════════════════════════════════════
        # Scene 2: Help & Documentation (moved early)
        # ═══════════════════════════════════════════════════
        print("  Scene 2: Help & Documentation")
        dur = get_clip_duration_ms("s2_help")
        await show_subtitle(page, "Let's explore the help and documentation", dur)

        help_btn = page.locator('button[title="Help & Feedback"], button:has-text("Help")').first
        try:
            await click_on(page, help_btn, pause=1000, timeout=5000)

            dur = get_clip_duration_ms("s2_docs")
            await show_subtitle(page, "Documentation includes guides for every feature", dur)

            # Hover Documentation link
            doc_link = page.locator('a[href="/docs/"]').first
            await move_to(page, doc_link, pause=1500, timeout=3000)

            dur = get_clip_duration_ms("s2_pricing")
            await show_subtitle(page, "Access Databricks official pricing directly", dur)

            # Hover Pricing link
            pricing_link = page.locator('a[href*="databricks.com/product/pricing"]').first
            await move_to(page, pricing_link, pause=1500, timeout=3000)

            # Close help dropdown by clicking elsewhere
            await page.mouse.click(640, 400)
            await page.wait_for_timeout(500)

        except Exception as e:
            print(f"  [skip] Help: {e}")

        await hide_subtitle(page)
        await page.wait_for_timeout(500)

        # ═══════════════════════════════════════════════════
        # Scene 3: Create Estimate
        # ═══════════════════════════════════════════════════
        print("  Scene 3: Create estimate")
        dur = get_clip_duration_ms("s3_create")
        await show_subtitle(page, "Creating a new pricing estimate", dur)

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
        await wait_for_regions(page)

        # Type estimate name
        dur = get_clip_duration_ms("s3_name")
        await show_subtitle(page, "Naming the estimate", dur)
        name_field = page.get_by_role("textbox").first
        await move_to(page, name_field, pause=400)
        await name_field.click(click_count=3)
        await page.keyboard.type("Q4 Data Platform Estimate", delay=60)
        await page.wait_for_timeout(800)

        # Select region with VISIBLE dropdown
        dur = get_clip_duration_ms("s3_region")
        await show_subtitle(page, "Selecting the AWS cloud region", dur)
        region_select = page.locator('select').first
        await visual_select(page, region_select, value="us-east-1")

        # Select tier with VISIBLE dropdown
        dur = get_clip_duration_ms("s3_tier")
        await show_subtitle(page, "Choosing the Premium pricing tier", dur)
        tier_select = page.locator('select').nth(1)
        await visual_select(page, tier_select, value="premium")

        # Click Create Estimate
        create_btn = page.locator('button:has-text("Create Estimate")').first
        await click_on(page, create_btn, pause=500)

        dur = get_clip_duration_ms("s3_done")
        await show_subtitle(page, "Estimate created! Now let's add workloads", dur)
        await page.wait_for_timeout(3000)
        await setup_page(page)
        await hide_subtitle(page)

        # ═══════════════════════════════════════════════════
        # Scene 4: Add Two Workloads Manually
        # ═══════════════════════════════════════════════════
        print("  Scene 4a: Add workload 1 — Jobs Compute")
        try:
            await page.wait_for_selector('button:has-text("Add Workload")', timeout=15000)
        except:
            pass
        await page.wait_for_timeout(2000)

        dur = get_clip_duration_ms("s4_add1")
        await show_subtitle(page, "Adding a Lakeflow Jobs workload for ETL pipelines", dur)

        add_btn = page.locator('button:has-text("Add Workload")').first
        await click_on(page, add_btn, pause=1500)

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
                    await page.keyboard.type("ETL Data Pipeline", delay=50)
                    await page.wait_for_timeout(600)
                    break
            except:
                continue

        # Select workload type with VISIBLE dropdown
        dur = get_clip_duration_ms("s4_type1")
        await show_subtitle(page, "Selecting Lakeflow Jobs as the workload type", dur)
        selects = page.locator('select')
        sel_count = await selects.count()
        for i in range(sel_count):
            try:
                sel = selects.nth(i)
                box = await sel.bounding_box(timeout=1000)
                if box and box["y"] > 100:
                    await visual_select(page, sel, value="JOBS")
                    break
            except:
                continue

        # Configure parameters
        dur = get_clip_duration_ms("s4_config1")
        await show_subtitle(page, "Configuring instance type, workers, and usage", dur)
        await page.wait_for_timeout(2000)

        # Fill number inputs (num_workers, runs_per_day, avg_runtime)
        num_inputs = page.locator('input[type="number"]')
        num_count = await num_inputs.count()
        for i in range(num_count):
            try:
                inp = num_inputs.nth(i)
                box = await inp.bounding_box(timeout=500)
                if box and box["y"] > 200:
                    await move_to(page, inp, pause=200)
                    await inp.click(click_count=3)
                    await page.keyboard.type("4", delay=80)
                    await page.wait_for_timeout(400)
                    break
            except:
                continue

        dur = get_clip_duration_ms("s4_cost1")
        await show_subtitle(page, "Cost is calculated automatically as you configure", dur)
        await page.wait_for_timeout(2000)

        # ── Workload 2: DBSQL ──
        print("  Scene 4b: Add workload 2 — Databricks SQL")
        dur = get_clip_duration_ms("s4_add2")
        await show_subtitle(page, "Adding a second workload — Databricks SQL", dur)

        # Scroll up to find Add Workload button again
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(500)
        add_btn = page.locator('button:has-text("Add Workload")').first
        await click_on(page, add_btn, pause=1500)

        # Fill name
        await page.wait_for_timeout(500)
        all_inputs = page.locator('input[type="text"]')
        count = await all_inputs.count()
        for i in range(count):
            try:
                inp = all_inputs.nth(i)
                box = await inp.bounding_box(timeout=1000)
                if box and box["y"] > 100:
                    val = await inp.input_value()
                    if not val:
                        await move_to(page, inp, pause=300)
                        await inp.click()
                        await page.keyboard.type("Analytics SQL Warehouse", delay=50)
                        await page.wait_for_timeout(600)
                        break
            except:
                continue

        # Select DBSQL type with VISIBLE dropdown
        dur = get_clip_duration_ms("s4_type2")
        await show_subtitle(page, "Selecting Databricks SQL as the workload type", dur)
        selects = page.locator('select')
        sel_count = await selects.count()
        for i in range(sel_count):
            try:
                sel = selects.nth(i)
                box = await sel.bounding_box(timeout=1000)
                if box and box["y"] > 100:
                    # Find the workload type select (first select in the new workload form)
                    opts = await sel.evaluate('(el) => Array.from(el.options).map(o => o.value)')
                    if 'DBSQL' in opts:
                        await visual_select(page, sel, value="DBSQL")
                        break
            except:
                continue

        dur = get_clip_duration_ms("s4_config2")
        await show_subtitle(page, "Configuring SQL warehouse size and type", dur)
        await page.wait_for_timeout(2000)

        dur = get_clip_duration_ms("s4_cost2")
        await show_subtitle(page, "Both workloads now show individual cost breakdowns", dur)
        await page.wait_for_timeout(2000)
        await hide_subtitle(page)

        # ═══════════════════════════════════════════════════
        # Scene 5: Cost Summary (navigate to pre-seeded estimate)
        # ═══════════════════════════════════════════════════
        print("  Scene 5: Cost summary")
        dur = get_clip_duration_ms("s5_summary")
        await show_subtitle(page, "Reviewing the total cost summary", dur)
        await page.goto(ESTIMATE_URL, wait_until="load", timeout=60000)
        await page.wait_for_timeout(5000)
        await setup_page(page)

        try:
            monthly = page.locator('text=Monthly Estimate').first
            await move_to(page, monthly, pause=1200)
        except:
            pass

        try:
            dbu = page.locator('text=DBU Cost').first
            await move_to(page, dbu, pause=1000)
        except:
            pass

        try:
            vm = page.locator('text=VM Cost').first
            await move_to(page, vm, pause=1000)
        except:
            pass

        dur = get_clip_duration_ms("s5_detail")
        await show_subtitle(page, "Each workload's cost contribution is shown with a percentage bar", dur)
        await page.wait_for_timeout(1500)
        await hide_subtitle(page)

        # ═══════════════════════════════════════════════════
        # Scene 6: AI Assistant — Add Workload via Chat
        # ═══════════════════════════════════════════════════
        print("  Scene 6: AI Assistant")
        dur = get_clip_duration_ms("s6_intro")
        await show_subtitle(page, "Using the AI assistant to configure a workload", dur)

        # Type a request to add a workload
        dur = get_clip_duration_ms("s6_ask")
        await show_subtitle(page, "Asking the AI to set up a Foundation Model API workload", dur)

        chat_input = page.locator('textarea').last
        try:
            await move_to(page, chat_input, pause=500, timeout=5000)
            await chat_input.click()
            await page.keyboard.type(
                "Add a Foundation Model Proprietary workload using Claude Opus 4.6 with 10 million input tokens per month on the global endpoint",
                delay=35
            )
            await page.wait_for_timeout(800)
            await page.keyboard.press("Enter")

            # Wait for AI streaming response
            dur = get_clip_duration_ms("s6_response")
            await show_subtitle(page, "AI proposes a complete workload configuration", max(dur, 12000))
            await page.wait_for_timeout(15000)

        except Exception as e:
            print(f"  [skip] AI chat: {e}")
            await page.wait_for_timeout(2000)

        await hide_subtitle(page)
        await page.wait_for_timeout(500)

        # ═══════════════════════════════════════════════════
        # Scene 7: Export to Excel
        # ═══════════════════════════════════════════════════
        print("  Scene 7: Export to Excel")
        dur = get_clip_duration_ms("s7_export")
        await show_subtitle(page, "Exporting the estimate to Excel with full cost breakdown", dur)

        excel_btn = page.locator('button:has-text("Excel")').first
        try:
            await move_to(page, excel_btn, pause=600)
            await excel_btn.click()
            await page.wait_for_timeout(2500)
        except:
            pass

        await hide_subtitle(page)
        await page.wait_for_timeout(500)

        # ═══════════════════════════════════════════════════
        # Scene 8: Closing
        # ═══════════════════════════════════════════════════
        print("  Scene 8: Closing")
        dur = get_clip_duration_ms("s8_close")
        await show_subtitle(page, "That's Lakemeter — start estimating your Databricks costs today!", dur)
        await hide_subtitle(page)
        await page.wait_for_timeout(2000)

        # ─── Finish recording ───
        video_path = await page.video.path()
        await context.close()
        await browser.close()

    # ─── Post-processing: merge video + voiceover ───
    print("Post-processing...")

    # Step 1: Convert raw WebM to MP4 (no audio)
    silent_mp4 = os.path.join(VIDEO_DIR, "_silent.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-i", video_path,
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-vf", "scale=1280:800",
        "-movflags", "+faststart",
        "-an",
        silent_mp4
    ], capture_output=True)

    # Step 2: Get video duration
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", silent_mp4],
        capture_output=True, text=True
    )
    video_duration = float(result.stdout.strip())
    print(f"  Video duration: {video_duration:.1f}s")

    # Step 3: Build a combined voiceover track aligned to approximate timestamps
    # We concatenate all clips with silence gaps to roughly match scene timing
    clip_order = [
        "s1_welcome", "s1_estimates",
        "s2_help", "s2_docs", "s2_pricing",
        "s3_create", "s3_name", "s3_region", "s3_tier", "s3_done",
        "s4_add1", "s4_type1", "s4_config1", "s4_cost1",
        "s4_add2", "s4_type2", "s4_config2", "s4_cost2",
        "s5_summary", "s5_detail",
        "s6_intro", "s6_ask", "s6_response",
        "s7_export",
        "s8_close",
    ]

    # Concatenate all clips with short silence between them
    concat_list = os.path.join(AUDIO_DIR, "concat.txt")
    silence_path = os.path.join(AUDIO_DIR, "silence_500ms.mp3")
    # Generate a short silence clip
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
        "-t", "0.5", "-c:a", "libmp3lame", "-q:a", "9", silence_path
    ], capture_output=True)

    with open(concat_list, "w") as f:
        for i, clip_id in enumerate(clip_order):
            clip_path = os.path.join(AUDIO_DIR, f"{clip_id}.mp3")
            if os.path.exists(clip_path):
                f.write(f"file '{clip_path}'\n")
                # Add silence between clips (not after last)
                if i < len(clip_order) - 1:
                    f.write(f"file '{silence_path}'\n")

    combined_audio = os.path.join(AUDIO_DIR, "combined.mp3")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list,
        "-c:a", "libmp3lame", "-q:a", "2",
        combined_audio
    ], capture_output=True)

    # Step 4: Merge video + audio (keep full video duration, audio ends naturally)
    final_mp4 = os.path.join(VIDEO_DIR, "getting-started-tutorial.mp4")
    subprocess.run([
        "ffmpeg", "-y",
        "-i", silent_mp4,
        "-i", combined_audio,
        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        final_mp4
    ], capture_output=True)

    size = os.path.getsize(final_mp4) / (1024 * 1024)
    print(f"  → getting-started-tutorial.mp4 ({size:.1f}MB)")

    # Step 5: Also save WebM version
    webm_path = os.path.join(VIDEO_DIR, "getting-started-tutorial.webm")
    subprocess.run([
        "ffmpeg", "-y", "-i", final_mp4,
        "-c:v", "libvpx-vp9", "-crf", "30", "-b:v", "0",
        "-c:a", "libopus", "-b:a", "96k",
        webm_path
    ], capture_output=True)
    size = os.path.getsize(webm_path) / (1024 * 1024)
    print(f"  → getting-started-tutorial.webm ({size:.1f}MB)")

    # Clean temp files
    for f in [silent_mp4, video_path]:
        if os.path.exists(f) and f != final_mp4:
            try:
                os.remove(f)
            except:
                pass

    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
