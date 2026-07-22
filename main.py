from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

import models
from database import engine
from routers import users, groups, expenses


models.Base.metadata.create_all(bind=engine)

# to initialize the application
app=FastAPI(title="Decentro Expense Sharing API")


#global handler for database conflicts
@app.exception_handler(IntegrityError)
async def sqlalchemy_integrity_error_handler(request:Request, exc:IntegrityError):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": "Database Conflict",
            "message": "This record already exists. For example, this email might already be registered"
        }
    )


@app.get("/")
def health_check():
    return {"status": "Decentro Expense Engine Active"}


# Include all routers
app.include_router(users.router)
app.include_router(groups.router)
app.include_router(expenses.router)


