# Description: DCA Admin page endpoints.

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from lnbits.core.models import User
from lnbits.decorators import check_user_exists
from lnbits.helpers import template_renderer

myextension_generic_router = APIRouter()


def myextension_renderer():
    return template_renderer(["myextension/templates"])


# DCA Admin page
@myextension_generic_router.get("/", response_class=HTMLResponse)
async def index(req: Request, user: User = Depends(check_user_exists)):
    return myextension_renderer().TemplateResponse(
        "myextension/index.html", {"request": req, "user": user.json()}
    )
