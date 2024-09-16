import {test, expect} from '@playwright/test';
import sinon from 'sinon';
import {html} from 'lit';
import { fixture } from '@open-wc/testing';
//import '../js-src/cs-client';
//import {ChromeStatusClient} from '../js-src/cs-client';
import * as cs_Client from './js-src/cs_client';

let csClient;

/* window.csClient and <chromedash-toast> are initialized at spa.html
 * which are not available here, so we initialize them before each test.
 * We also stub out the API calls here so that they return test data. */
test.beforeEach(async () => {
  await fixture(html`<chromedash-toast></chromedash-toast>`);
  csClient = new cs_Client.ChromeStatusClient('fake_token', 1);
  sinon.stub(csClient, 'getStars');
  sinon.stub(csClient, 'searchFeatures');
  csClient.getStars.returns(Promise.resolve([123456]));
});

test.afterEach(() => {
  csClient.getStars.restore();
  csClient.searchFeatures.restore();
});

test('features page test', async ({page}) => {
  await page.goto('http://localhost:8080/features');
  await expect(page).toHaveScreenshot();
});
