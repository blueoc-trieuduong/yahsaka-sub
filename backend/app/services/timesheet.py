import uuid

import requests
from sqlmodel import Session, select

from app.core.config import settings
from app.models.models import Org, Package, User


class TimesheetServices:
    def create_timesheet_org(session: Session, org_id: int, package_id: uuid.UUID):
        package = session.get(Package, package_id)
        org_obj = session.get(Org, org_id)

        org_id = int(org_id)

        user_obj = session.exec(select(User).where(User.org_id == org_id)).first()

        max_employees = package.max_employees if package else 0

        org_params = {
            "organization_id": str(org_obj.id),
            "organization_name": org_obj.name,
            "phone_number": org_obj.phone_number,
            "email": org_obj.email,
            "industry": org_obj.industry,
            "company_prefix": org_obj.company_prefix,
            "country": org_obj.country,
            "address": org_obj.address or "",
            "tax_code": org_obj.tax_code or "",
            "max_employees": max_employees,
            "admin_first_name": user_obj.first_name,
            "admin_last_name": user_obj.last_name,
            "admin_email": user_obj.email,
            "password": "RandomPass123!",
            "password_confirmation": "RandomPass123!",
        }

        headers = {
            "Authorization": f"Bearer {settings.API_TOKEN}",
            "Content-Type": "application/json",
        }

        update_response = requests.post(
            f"{settings.TIMESHEET_API_URL}/organization/create",
            headers=headers,
            json=org_params,
        )

        return update_response

    def update_timesheet_org(session: Session, org_id: int, package_id: uuid.UUID):
        package = session.get(Package, package_id)
        org_obj = session.get(Org, org_id)

        headers = {
            "Authorization": f"Bearer {settings.API_TOKEN}",
            "Content-Type": "application/json",
        }

        max_employees = package.max_employees if package else 0

        update_params = {
            "organization_name": org_obj.name,
            "phone_number": org_obj.phone_number,
            "email": org_obj.email,
            "industry": org_obj.industry,
            "company_prefix": org_obj.company_prefix,
            "country": org_obj.country,
            "address": org_obj.address or "",
            "tax_code": org_obj.tax_code or "",
            "max_employees": max_employees,
        }
        update_response = requests.put(
            f"{settings.TIMESHEET_API_URL}/organization/{org_id}",
            headers=headers,
            json=update_params,
        )

        return update_response
