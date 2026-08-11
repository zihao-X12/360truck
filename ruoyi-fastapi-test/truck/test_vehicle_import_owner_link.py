import io
from urllib.parse import urlparse
from uuid import uuid4

import pytest
import requests
from openpyxl import Workbook
from playwright.async_api import async_playwright, expect

from common.config import Config
from common.login_helper import LoginHelper

IMPORTED_VEHICLE_COUNT = 2


def _authenticated_session(username: str = 'admin') -> tuple[requests.Session, str]:
    token = LoginHelper().login(username=username)
    assert token, f'{username} 登录失败'
    session = requests.Session()
    session.headers['Authorization'] = f'Bearer {token}'
    return session, token


def _build_workbook(plates: list[str], owner_name: str) -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(['车牌', '机动车所有人', '车主联系电话', '辖区中队'])
    worksheet.append([plates[0], owner_name, '13800000000', '西屏中队'])
    worksheet.append([plates[1], owner_name, '13800000000', '古市中队'])
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


async def _assert_owner_vehicle_ui(token: str, owner_id: int, owner_name: str) -> None:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1440, 'height': 900})
        await context.add_cookies(
            [
                {
                    'name': 'Admin-Token', 'value': token, 'domain': urlparse(Config.frontend_url).hostname,
                    'path': '/', 'httpOnly': False, 'secure': False,
                }
            ]
        )
        page = await context.new_page()
        await page.goto(f'{Config.frontend_url}/truck/owner')
        await page.get_by_placeholder('企业或个人姓名').fill(owner_name)
        await page.get_by_role('button', name='搜索', exact=True).click()
        owner_row = page.locator('.el-table__body-wrapper tbody tr', has_text=owner_name)
        await expect(owner_row).to_have_count(1)
        await expect(owner_row.get_by_text('2 辆', exact=True)).to_be_visible()
        await owner_row.get_by_role('button', name='查看车辆', exact=True).click()
        await page.wait_for_url(f'**/truck/vehicle?ownerId={owner_id}**')
        await expect(page.get_by_text(f'{owner_name}名下车辆', exact=True)).to_be_visible()
        await expect(page.locator('.el-table__body-wrapper tbody tr')).to_have_count(IMPORTED_VEHICLE_COUNT)
        await page.set_viewport_size({'width': 375, 'height': 812})
        has_overflow = await page.evaluate(
            'document.documentElement.scrollWidth > document.documentElement.clientWidth'
        )
        assert not has_overflow
        await page.get_by_role('button', name='新增车辆', exact=True).click()
        await page.wait_for_url(f'**/truck/vehicle-detail?ownerId={owner_id}**')
        await expect(page.get_by_label('机动车所有人')).to_have_value(owner_name)
        await expect(
            page.locator('.el-form-item', has_text='归属主体').get_by_text(owner_name, exact=True)
        ).to_be_visible()
        await expect(
            page.locator('.el-form-item', has_text='所属中队').get_by_text('西屏中队', exact=True)
        ).to_be_visible()
        await context.close()
        await browser.close()


def _assert_squad_scope(username: str, owner_name: str, owner_id: int, dept_id: int) -> None:
    session, _token = _authenticated_session(username)
    response = session.get(
        f'{Config.backend_url}/truck/owner/list',
        params={'pageNum': 1, 'pageSize': 10, 'ownerName': owner_name},
        timeout=10,
    )
    response.raise_for_status()
    owners = response.json().get('rows') or []
    assert len(owners) == 1
    assert owners[0]['ownerId'] == owner_id
    assert owners[0]['vehicleCount'] == 1

    response = session.get(
        f'{Config.backend_url}/truck/vehicle/list',
        params={'pageNum': 1, 'pageSize': 10, 'ownerId': owner_id},
        timeout=10,
    )
    response.raise_for_status()
    vehicles = response.json().get('rows') or []
    assert len(vehicles) == 1
    assert vehicles[0]['deptId'] == dept_id


@pytest.mark.asyncio
async def test_vehicle_import_creates_and_links_owner() -> None:
    suffix = uuid4().hex[:5].upper()
    owner_name = f'自动化联动主体{suffix}'
    plates = [f'浙T{suffix}1', f'浙T{suffix}2']
    session, token = _authenticated_session()
    workbook = _build_workbook(plates, owner_name)

    vehicle_ids: list[int] = []
    owner_id: int | None = None
    try:
        response = session.post(
            f'{Config.backend_url}/truck/vehicle/import',
            files={
                'file': (
                        'owner-link-test.xlsx',
                        workbook,
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                )
            },
            timeout=30,
        )
        response.raise_for_status()
        result = response.json().get('data') or {}
        assert (result.get('successCount'), result.get('errorCount')) == (2, 0)

        response = session.get(
            f'{Config.backend_url}/truck/vehicle/list',
            params={'pageNum': 1, 'pageSize': 100, 'plateNo': f'浙T{suffix}'},
            timeout=10,
        )
        response.raise_for_status()
        rows = response.json().get('rows') or []
        assert len(rows) == IMPORTED_VEHICLE_COUNT
        vehicle_ids = [row['vehicleId'] for row in rows]
        owner_ids = {row.get('ownerId') for row in rows}
        assert None not in owner_ids and len(owner_ids) == 1
        assert {row.get('ownerType') for row in rows} == {'individual'}
        assert {row.get('deptId') for row in rows} == {9101, 9102}
        owner_id = owner_ids.pop()

        response = session.get(f'{Config.backend_url}/truck/owner/{owner_id}', timeout=10)
        response.raise_for_status()
        owner = response.json().get('data') or {}
        assert (
            owner.get('ownerName'),
            owner.get('ownerType'),
            owner.get('deptId'),
            owner.get('contactPhone'),
        ) == (owner_name, 'individual', 9101, '13800000000')

        _assert_squad_scope('xiping_admin', owner_name, owner_id, 9101)
        await _assert_owner_vehicle_ui(token, owner_id, owner_name)
    finally:
        if vehicle_ids:
            response = session.delete(
                f"{Config.backend_url}/truck/vehicle/{','.join(map(str, vehicle_ids))}", timeout=10
            )
            response.raise_for_status()
        if owner_id:
            response = session.delete(f'{Config.backend_url}/truck/owner/{owner_id}', timeout=10)
            response.raise_for_status()
