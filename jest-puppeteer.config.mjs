// jest-puppeteer.config.mjs
module.exports = {
    launch: {
        headless: false,
        // `headless: true` (default) enables old Headless;
        // `headless: 'new'` enables new Headless;
        // `headless: false` enables “headful” mode.
        product: 'chrome',
        args: ['--start-maximized'],
        defaultViewport: { width: 1700, height: 800 }

    },
    browserContext: 'default',
}
