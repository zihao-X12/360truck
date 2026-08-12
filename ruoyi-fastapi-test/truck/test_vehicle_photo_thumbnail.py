from urllib.parse import urlparse

import pytest
from playwright.async_api import async_playwright, expect

from common.config import Config
from common.login_helper import LoginHelper


@pytest.mark.asyncio
async def test_vehicle_photo_renders_thumbnail_and_preview() -> None:
    token = LoginHelper().login()
    assert token, '管理员登录失败'
    file_id = '11111111-1111-1111-1111-111111111111'
    vehicle_id = 990001
    png = bytes.fromhex(
        '89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489'
        '0000000d49444154789c6360f8cfc000000301010018dd8db10000000049454e44ae426082'
    )

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1440, 'height': 900})
        await context.add_cookies(
            [{
                'name': 'Admin-Token', 'value': token, 'domain': urlparse(Config.frontend_url).hostname,
                'path': '/', 'httpOnly': False, 'secure': False,
            }]
        )
        page = await context.new_page()
        await page.route(
            f'**/truck/vehicle/{vehicle_id}',
            lambda route: route.fulfill(
                json={
                    'code': 200,
                    'data': {
                        'vehicleId': vehicle_id, 'plateNo': '浙TTEST', 'plateColor': 'yellow',
                        'deptId': 9101, 'photoFileId': file_id, 'vehicleStatus': 'normal',
                        'supervisionFlag': '0', 'devices': [],
                    },
                }
            ),
        )
        await page.route(
            f'**/common/files/{file_id}/download/**',
            lambda route: route.fulfill(status=200, body=png, content_type='image/png'),
        )

        await page.goto(f'{Config.frontend_url}/truck/vehicle-detail/{vehicle_id}?readonly=1')
        thumbnail = page.locator('.business-file-thumbnail img')
        await expect(thumbnail).to_be_visible()
        thumbnail_src = await thumbnail.get_attribute('src')
        assert thumbnail_src and thumbnail_src.startswith('blob:')
        await thumbnail.click()
        await expect(page.locator('.el-image-viewer__wrapper')).to_be_visible()
        await context.close()
        await browser.close()
