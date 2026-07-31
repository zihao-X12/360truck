from urllib.parse import urlparse

import pytest
from playwright.async_api import Browser, BrowserContext, async_playwright

from common.config import Config
from common.login_helper import LoginHelper


async def authenticated_context(browser: Browser) -> BrowserContext:
    token = LoginHelper().login(username='admin', password='admin123')
    assert token, '管理员登录失败'
    context = await browser.new_context(viewport={'width': 1440, 'height': 900})
    host = urlparse(Config.frontend_url).hostname
    await context.add_cookies(
        [{'name': 'Admin-Token', 'value': token, 'domain': host, 'path': '/', 'httpOnly': False, 'secure': False}]
    )
    return context


@pytest.mark.asyncio
async def test_user_management_matches_truck_platform_organization() -> None:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await authenticated_context(browser)
        page = await context.new_page()

        await page.goto(f'{Config.frontend_url}/system/user')
        org_tree = page.get_by_role('tree')
        await org_tree.get_by_text('松阳大队', exact=True).wait_for()
        for squad in ('西屏中队', '古市中队', '江南中队', '象溪中队', '大东坝中队', '玉岩中队'):
            await org_tree.get_by_text(squad, exact=True).wait_for()
        await page.get_by_text('大队管理员', exact=True).first.wait_for()
        await page.get_by_text('中队管理员', exact=True).first.wait_for()
        await page.get_by_text('领导权限', exact=True).first.wait_for()
        assert await page.get_by_text('集团总公司', exact=True).count() == 0
        assert await page.get_by_role('button', name='导入').count() == 0
        assert await page.get_by_role('button', name='导出').count() == 0

        await page.get_by_role('button', name='新增账号').click()
        dialog = page.get_by_role('dialog', name='新增平台账号')
        await dialog.wait_for()
        await dialog.get_by_label('姓名').wait_for()
        await dialog.get_by_label('所属单位').wait_for()
        await dialog.get_by_label('平台角色').wait_for()
        assert await dialog.get_by_label('邮箱').count() == 0
        assert await dialog.get_by_label('岗位').count() == 0

        await page.set_viewport_size({'width': 375, 'height': 812})
        await page.goto(f'{Config.frontend_url}/system/user')
        await page.get_by_role('tree').get_by_text('松阳大队', exact=True).wait_for()
        overflow = await page.evaluate('document.documentElement.scrollWidth > document.documentElement.clientWidth')
        assert not overflow, '用户管理页面存在移动端横向溢出'

        await context.close()
        await browser.close()
