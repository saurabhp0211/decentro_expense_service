# Decentro SDE Intern Assignment - Expense Sharing Service

## Overview
This is a backend service for an expense-sharing application, built using **FastAPI** and **SQLAlchemy** (with SQLite). 

While the baseline requirement was to handle simple equal expense splitting, I approached this assignment with a product-first mindset. Real-world expenses are messy, so I focused on building a flexible mathematical engine that handles different split types, prioritizes database transaction safety, and returns clean, human-readable data to the frontend.

---

## 🚀 Setup & Installation

I utilized a virtual environment to keep the dependencies isolated and clean. 

**1. Clone the repository and navigate into it:**
git clone https://github.com/saurabhp0211/decentro_expense_service.git
cd decentro_expense_service

**2. Create and activate a virtual environment:**
`python3 -m venv venv`
*On Mac/Linux:* `source venv/bin/activate`
*On Windows:* `venv\Scripts\activate`

**3. Install dependencies:**
`pip install fastapi uvicorn sqlalchemy pydantic email-validator alembic`

**4. Start the server:**
`uvicorn main:app --reload`
*Note: SQLite will automatically generate the expenses.db file locally. No external database setup is required.*

**5. View the API Docs:**
Navigate to `http://127.0.0.1:8000/docs` to use the interactive Swagger UI to test the endpoints.

---

## 🗄️ Database Design

I designed the schema to clearly separate the "Master Receipt" (who swiped their card) from the "Ledger" (who owes what). 

* **`users`**: Core user details (ID, name, email, mobile).
* **`groups`**: Group metadata.
* **`group_members`**: An association table handling the Many-to-Many relationship between users and groups. 
* **`expenses`**: The master receipt. If Mohit pays ₹3000 for a hotel, it is recorded here as a single row.
* **`expense_splits`**: The individual ledger. This table holds the exact, calculated debt for every person involved in an expense. It has a Foreign Key back to the master `expenses` table.

**Data Integrity Decision:** I heavily utilized SQLAlchemy's `ondelete="CASCADE"`. If a group or master expense is ever deleted, all associated splits and member mappings are automatically wiped which makes sure there is no orphan data lying in the database. Furthermore, I added an event listener in `database.py` to enforce SQLite `PRAGMA foreign_keys=ON`, which is disabled by default in SQLite.

---

## 💡 Product Enhancements & Design Decisions

I treated this not just as an API assignment, but as a real product. Here are the core decisions I made:

### 1. The Math Engine (EXACT & PERCENT Splits)
The assignment asked for EQUAL splits, but I built `EXACT` and `PERCENT` splits as my mandatory product enhancement. 
* **The "Why":** In real life, someone always orders an expensive drink, or a bill is split 60/40. The PERCENT split type makes it convenient for users. 
* **The Guardrails:** I handled validation dynamically using Pydantic and custom FastAPI exceptions. If a user submits a percentage split that adds up to 99%, or an exact split that doesn't match the master total, the API intercepts it and throws a `400 Bad Request` before it ever touches the database. 

### 2. Global Balances vs. Group-Specific Balances
For the `GET /balances/` route, I decided to calculate the **Net Global Debt** across all groups, rather than making it group-specific.
* **The "Why":** If Rahul owes Mohit ₹500 from a Goa Trip, and Mohit owes Rahul ₹200 from a Friday Dinner, Rahul doesn't want to dig through two groups to do the math. He just wants to know his net total (₹300) so he can make a single UPI transfer. This perfectly mimics the actual UX of apps like Splitwise.

### 3. Frontend Empathy (The "Message" Field)
APIs should make life easier for frontend developers and for an end user as well. When returning the balances, sending back raw user IDs requires the frontend to make secondary database calls to fetch the names. 
* **The Fix:** I used a Python `set()` and SQLAlchemy's `in_()` operator to fetch all involved user names in a *single* optimized database query. I then formatted an f-string `message` directly into the JSON response making it coherent(e.g., `"message": "Rahul owes Mohit Rs400.0"`). 

### 4. Transaction Safety (`db.flush()`)
When creating an expense, multiple database writes happen (1 master expense + multiple splits). I used `db.flush()` to generate the master expense ID so I could assign it to the splits in the loop, but held off on `db.commit()` until the very end. If the math fails halfway through the loop, the entire transaction rolls back, preventing corrupt, half-saved financial data.

---

## 🛠️ Assumptions Made
* **Authentication:** Assumed out of scope for this task. Users are currently identified purely by passing their `user_id` in the JSON payload.
* **Currency:** Assumed single currency (INR). 
* **Rounding:** Floating-point math creates infinite decimals (e.g., 100/3 = 33.333...). I strictly enforce a 2-decimal round (`round(amount, 2)`) before saving any split to the database to prevent long-term accounting drift.

---

## 🔮 Improvements with More Time

Given the 48-hour turnaround time alongside my current full-time role, I prioritized strict database design, API routing, and mathematical correctness. With more time, I would build:

1. **Expense Categorization & Spending Analytics:** I would introduce a `category` tag (e.g., Food, Travel, Utilities) to the `expenses` table. This would allow the frontend to generate monthly spending analytics, helping users track their habits and see exactly where their money is going.
2. **Containerization (Docker):** I would write a `Dockerfile` and `docker-compose.yml` to containerize the FastAPI application and SQLite database, ensuring seamless, one-click deployments and environment consistency across any machine.