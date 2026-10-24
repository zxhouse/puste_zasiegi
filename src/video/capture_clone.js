// Zrzuty klonu (Playwright/Chromium): pełna strona bez elementów przypiętych + pasek nawigacji + dok wiadomości, oraz położenia elementów.
// Użycie: node capture_clone.js <states.json> <outdir>
const { chromium } = require('playwright');
const fs = require('fs'); const path = require('path');
(async () => {
  const states = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const out = process.argv[3]; fs.mkdirSync(out, { recursive: true });
  const DPR = parseFloat(process.env.DPR || '1.25');
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: DPR });
  const root = 'file://' + path.resolve(__dirname, '../../linkedin_clone/index.html');
  const meta = {};
  for (const st of states) {
    const qs = new URLSearchParams(Object.assign({ capture: '1' }, st.params)).toString();
    await page.goto(root + '?' + qs);
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(150);
    const rects = await page.evaluate(() => window.__rects());
    // pasek i dok osobno (są przypięte do okna)
    await page.addStyleTag({ content: '.global-nav,.msg-dock{visibility:hidden !important}' });
    await page.screenshot({ path: path.join(out, st.id + '_page.png'), fullPage: true });
    await page.addStyleTag({ content: '.global-nav,.msg-dock{visibility:visible !important}' });
    if (st.nav) await (await page.$('#nav')).screenshot({ path: path.join(out, 'nav.png') });
    const dock = await page.$('#dock');
    const bb = await dock.boundingBox();
    const chat = await page.$('#chat');
    const cb = chat ? await chat.boundingBox() : null;
    const x0 = cb ? Math.min(bb.x, cb.x) : bb.x, y0 = cb ? Math.min(bb.y, cb.y) : bb.y;
    await page.addStyleTag({ content: '.layout{visibility:hidden !important} html,body{background:transparent !important}' });
    await page.screenshot({ path: path.join(out, st.id + '_dock.png'), clip: { x: x0 - 20, y: y0 - 20, width: 1920 - x0 + 20, height: 1080 - y0 + 20 }, omitBackground: true });
    meta[st.id] = { rects, dock_origin: [x0 - 20, y0 - 20], dpr: DPR };
    console.log('captured', st.id, rects.page);
  }
  fs.writeFileSync(path.join(out, 'meta.json'), JSON.stringify(meta));
  await browser.close();
})();
