"""Shared cursor injection and mouse movement utilities for Playwright recordings."""

# Custom cursor: large arrow with drop shadow, plus click ring animation
CURSOR_INJECT = """
(() => {
  if (document.getElementById('pw-cursor')) return;

  // Cursor container
  const cursor = document.createElement('div');
  cursor.id = 'pw-cursor';
  cursor.style.cssText = 'position:fixed;top:0;left:0;z-index:999999;pointer-events:none;will-change:transform;filter:drop-shadow(1px 2px 2px rgba(0,0,0,0.3));';

  // Highlight dot behind cursor + Arrow SVG (40x40) + click ring
  cursor.innerHTML = `
    <div style="position:absolute;top:4px;left:4px;width:28px;height:28px;border-radius:50%;background:rgba(59,130,246,0.25);filter:blur(4px);"></div>
    <svg width="40" height="40" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M8 5L32 20L20 22L15 33L8 5Z" fill="white" stroke="black" stroke-width="2.5" stroke-linejoin="round"/>
    </svg>
    <div id="pw-click-ring" style="position:absolute;top:-16px;left:-16px;width:72px;height:72px;border-radius:50%;border:3px solid rgba(239,68,68,0.9);background:rgba(239,68,68,0.2);opacity:0;transform:scale(0.3);pointer-events:none;"></div>
  `;
  document.body.appendChild(cursor);

  // Follow mouse
  let curX = 0, curY = 0;
  document.addEventListener('mousemove', e => {
    curX = e.clientX; curY = e.clientY;
    cursor.style.transform = `translate(${curX}px, ${curY}px)`;
  });

  // Click animation
  document.addEventListener('mousedown', () => {
    const ring = document.getElementById('pw-click-ring');
    if (!ring) return;
    ring.style.transition = 'none';
    ring.style.opacity = '1';
    ring.style.transform = 'scale(0.3)';
    requestAnimationFrame(() => {
      ring.style.transition = 'all 0.4s ease-out';
      ring.style.opacity = '0';
      ring.style.transform = 'scale(1.2)';
    });
  });
})();
"""


async def inject_cursor(page):
    """Inject cursor overlay into the page."""
    await page.evaluate(CURSOR_INJECT)


async def smooth_move(page, x, y, steps=30):
    """Move mouse smoothly to (x, y)."""
    await page.mouse.move(x, y, steps=steps)
    await page.wait_for_timeout(30)


async def move_to(page, locator, pause=400, timeout=5000):
    """Move mouse smoothly to center of element, return bounding box."""
    try:
        await locator.wait_for(state="visible", timeout=timeout)
        box = await locator.bounding_box(timeout=timeout)
        if box:
            await smooth_move(page, box["x"] + box["width"]/2, box["y"] + box["height"]/2)
            await page.wait_for_timeout(pause)
        return box
    except Exception as e:
        print(f"  [skip] move_to failed: {e}")
        return None


async def click_on(page, locator, pause=500, timeout=5000):
    """Move to element, then click it."""
    box = await move_to(page, locator, pause=200, timeout=timeout)
    if box:
        await locator.click(timeout=timeout)
        await page.wait_for_timeout(pause)
    return box
