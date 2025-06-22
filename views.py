# Description: DCA Admin page endpoints.

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from lnbits.core.models import User
from lnbits.decorators import check_user_exists
from lnbits.helpers import template_renderer

satmachineclient_generic_router = APIRouter()


def satmachineclient_renderer():
    return template_renderer(["satmachineclient/templates"])


# DCA Admin page
@satmachineclient_generic_router.get("/", response_class=HTMLResponse)
async def index(req: Request, user: User = Depends(check_user_exists)):
    return satmachineclient_renderer().TemplateResponse(
        "satmachineclient/index.html", {"request": req, "user": user.json()}
    )
