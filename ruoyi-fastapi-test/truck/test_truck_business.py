from urllib.parse import urlparse

import pytest
from playwright.async_api import Browser, BrowserContext, async_playwright

from common.config import Config
from common.login_helper import LoginHelper

METRIC_CARD_COUNT = 7
SQUAD_COUNT = 6
DEVICE_TYPE_COUNT = 2


async def authenticated_context(browser: Browser, username: str = 'admin') -> BrowserContext:
    token = LoginHelper().login(username=username, password='admin123')
    assert token, f'{username} 登录失败'
    context = await browser.new_context(viewport={'width': 1440, 'height': 900})
    host = urlparse(Config.frontend_url).hostname
    await context.add_cookies(
        [{'name': 'Admin-Token', 'value': token, 'domain': host, 'path': '/', 'httpOnly': False, 'secure': False}]
    )
    return context


@pytest.mark.asyncio
async def test_business_dashboard_and_warning_drilldown() -> None:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await authenticated_context(browser)
        page = await context.new_page()

        await page.goto(f'{Config.frontend_url}/index')
        await page.get_by_role('heading', name='松阳大队大货车业务看板').wait_for()
        await page.locator('.dept-panel tbody tr').first.wait_for()
        await page.locator('.coverage-item').first.wait_for()
        assert await page.locator('.metric-card').count() == METRIC_CARD_COUNT
        assert await page.locator('.dept-panel tbody tr').count() == SQUAD_COUNT
        assert await page.locator('.coverage-item').count() == DEVICE_TYPE_COUNT

        await page.locator('button.metric-card', has_text='一级预警').click()
        await page.wait_for_url('**/truck/warning?warningLevel=level_one')
        await page.get_by_text('重新计算预警', exact=True).wait_for()

        await context.close()
        await browser.close()


@pytest.mark.asyncio
async def test_vehicle_archive_menu_renders_list_page() -> None:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await authenticated_context(browser)
        page = await context.new_page()

        await page.goto(f'{Config.frontend_url}/truck/vehicle')
        await page.get_by_placeholder('请输入车牌号').wait_for()
        add_button = page.get_by_role('button', name='新增车辆')
        await add_button.wait_for()
        await page.get_by_role('columnheader', name='机动车所有人').wait_for()
        assert await page.get_by_role('columnheader', name='工地名称').count() == 0
        assert page.url.endswith('/truck/vehicle')

        await add_button.click()
        await page.wait_for_url('**/truck/vehicle-detail')
        await page.get_by_text('基础信息', exact=True).wait_for()
        assert await page.get_by_label('机动车所有人').count() == 1
        assert await page.get_by_label('工地名称').count() == 0
        await page.get_by_role('button', name='保存').wait_for()
        await page.get_by_role('button', name='取消').click()
        await page.wait_for_url('**/truck/vehicle')
        await page.get_by_placeholder('请输入车牌号').wait_for()

        await context.close()
        await browser.close()


@pytest.mark.asyncio
async def test_squad_admin_has_owner_and_vehicle_operations() -> None:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await authenticated_context(browser, username='xiping_admin')
        page = await context.new_page()

        await page.goto(f'{Config.frontend_url}/truck/owner')
        await page.get_by_role('button', name='新增主体').wait_for()

        await page.goto(f'{Config.frontend_url}/truck/vehicle')
        await page.get_by_role('button', name='新增车辆').wait_for()
        await page.get_by_role('button', name='批量导入').wait_for()
        await page.get_by_role('button', name='导出').wait_for()

        await context.close()
        await browser.close()


@pytest.mark.asyncio
async def test_truck_pages_have_no_mobile_horizontal_overflow() -> None:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await authenticated_context(browser)
        page = await context.new_page()
        await page.set_viewport_size({'width': 375, 'height': 812})

        for path in ('/index', '/truck/warning'):
            await page.goto(f'{Config.frontend_url}{path}')
            await page.wait_for_load_state('networkidle')
            overflow = await page.evaluate('document.documentElement.scrollWidth > document.documentElement.clientWidth')
            assert not overflow, f'{path} 存在移动端横向溢出'

        await context.close()
        await browser.close()
