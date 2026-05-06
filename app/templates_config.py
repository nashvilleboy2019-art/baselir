from fastapi.templating import Jinja2Templates
import os
from app import theme_cache

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
templates.env.globals["theme"] = theme_cache.get
