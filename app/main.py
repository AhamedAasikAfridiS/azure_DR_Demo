import os

from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base, engine, get_database_info, get_db
from app.models import Employee

APP_TITLE = os.getenv("APP_TITLE", "PostgreSQL DR CRUD Demo")

app = FastAPI(title=APP_TITLE)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    info = get_database_info()

    return {
        "status": "ok" if info.get("connected") else "db_error",
        "database_connected": info.get("connected"),
        "database_host": info.get("configured_host"),
    }


@app.get("/", response_class=HTMLResponse)
def list_employees(request: Request, db: Session = Depends(get_db)):
    employees = db.scalars(select(Employee).order_by(Employee.id.desc())).all()

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": APP_TITLE,
            "employees": employees,
        },
    )


@app.get("/employees/new", response_class=HTMLResponse)
def new_employee_form(request: Request):
    return templates.TemplateResponse(
        "form.html",
        {
            "request": request,
            "title": APP_TITLE,
            "mode": "create",
            "employee": None,
        },
    )


@app.post("/employees")
def create_employee(
    name: str = Form(...),
    role: str = Form(...),
    department: str = Form("Engineering"),
    db: Session = Depends(get_db),
):
    employee = Employee(
        name=name.strip(),
        role=role.strip(),
        department=department.strip(),
    )

    db.add(employee)
    db.commit()

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/employees/{employee_id}/edit", response_class=HTMLResponse)
def edit_employee_form(
    employee_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    employee = db.get(Employee, employee_id)

    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    return templates.TemplateResponse(
        "form.html",
        {
            "request": request,
            "title": APP_TITLE,
            "mode": "edit",
            "employee": employee,
        },
    )


@app.post("/employees/{employee_id}")
def update_employee(
    employee_id: int,
    name: str = Form(...),
    role: str = Form(...),
    department: str = Form("Engineering"),
    db: Session = Depends(get_db),
):
    employee = db.get(Employee, employee_id)

    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    employee.name = name.strip()
    employee.role = role.strip()
    employee.department = department.strip()

    db.commit()

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/employees/{employee_id}/delete")
def delete_employee(employee_id: int, db: Session = Depends(get_db)):
    employee = db.get(Employee, employee_id)

    if employee:
        db.delete(employee)
        db.commit()

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/seed")
def seed_data(db: Session = Depends(get_db)):
    sample_employees = [
        Employee(name="Aasik", role="DevOps Intern", department="Cloud Team"),
        Employee(name="PITR Demo User", role="Database Admin", department="DB Team"),
        Employee(name="Geo Restore User", role="SRE Engineer", department="Platform Team"),
        Employee(name="Replica Demo User", role="Backend Engineer", department="Application Team"),
    ]

    db.add_all(sample_employees)
    db.commit()

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/delete-all")
def delete_all(db: Session = Depends(get_db)):
    """
    Use this to simulate accidental data deletion before Point-in-Time Restore demo.
    """
    db.query(Employee).delete()
    db.commit()

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/db-info", response_class=HTMLResponse)
def db_info(request: Request):
    return templates.TemplateResponse(
        "db_info.html",
        {
            "request": request,
            "title": APP_TITLE,
            "info": get_database_info(),
        },
    )   