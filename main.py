# main.py
from fastapi import FastAPI
from dotenv import load_dotenv
load_dotenv()


from routers import ai_router

from database import engine
import models
from routers import auth_router, category_router, incomes_router, expenses_router, summary_router, transactions_router

# Create tables (temporary quick start). Remove if you use migrations.
models.Base = models  # not used but keep
models.Base = None
models  # silence lint

from database import Base
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Finance API (advanced starter)",  redirect_slashes=False)

app.include_router(auth_router.router)
app.include_router(category_router.router)
app.include_router(incomes_router.router)
app.include_router(expenses_router.router)
app.include_router(summary_router.router)
app.include_router(ai_router.router)
app.include_router(transactions_router.router)

