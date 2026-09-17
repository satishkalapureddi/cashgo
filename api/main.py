from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta
from dotenv import load_dotenv

import razorpay
import uuid
import os

from database import (
    create_tables,
    create_transaction,
    get_transaction,
    update_payment_status,
    dispense_cash
)


# =========================
# ENVIRONMENT
# =========================

load_dotenv()

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "").strip()
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "").strip()

PAYMENT_PROVIDER = os.getenv(
    "PAYMENT_PROVIDER",
    "demo"
)


# =========================
# RAZORPAY
# =========================

razorpay_client = None

if (
    RAZORPAY_KEY_ID
    and RAZORPAY_KEY_SECRET
    and RAZORPAY_KEY_ID != "YOUR_KEY_ID"
    and RAZORPAY_KEY_SECRET != "YOUR_KEY_SECRET"
):
    razorpay_client = razorpay.Client(
        auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
    )


# =========================
# FASTAPI
# =========================

app = FastAPI(
    title="CASHGO API",
    description="Small Cash • Instant Access",
    version="1.0.0"
)


# Create SQLite tables
create_tables()


# =========================
# CORS
# =========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# MODELS
# =========================

class WithdrawalRequest(BaseModel):
    amount: int


# =========================
# HELPERS
# =========================

ALLOWED_AMOUNTS = [10, 20, 50, 100]


def generate_transaction_id():
    date_part = datetime.now().strftime("%Y%m%d")
    random_part = uuid.uuid4().hex[:6].upper()

    return f"CG-{date_part}-{random_part}"


def calculate_payment(amount: int):
    """
    Calculate money in paise.

    9.9% service charge = 99 / 1000
    """

    cash_amount_paise = amount * 100

    service_charge_paise = round(
        cash_amount_paise * 99 / 1000
    )

    total_amount_paise = (
        cash_amount_paise +
        service_charge_paise
    )

    return (
        cash_amount_paise,
        service_charge_paise,
        total_amount_paise
    )


def paise_to_rupees(paise: int):
    return round(paise / 100, 2)


# =========================
# ROOT
# =========================

@app.get("/")
def root():

    return {
        "status": "online",
        "service": "CASHGO API"
    }


# =========================
# HEALTH
# =========================

@app.get("/api/health")
def health():

    return {
        "status": "healthy",
        "service": "CASHGO"
    }


# =========================
# CREATE WITHDRAWAL
# =========================

@app.post("/api/withdrawal/create")
def create_withdrawal(request: WithdrawalRequest):

    if request.amount not in ALLOWED_AMOUNTS:
        raise HTTPException(
            status_code=400,
            detail="Invalid withdrawal amount"
        )

    (
        cash_amount_paise,
        service_charge_paise,
        total_amount_paise
    ) = calculate_payment(request.amount)

    transaction_id = generate_transaction_id()

    expires_at = (
        datetime.now() +
        timedelta(seconds=60)
    ).isoformat()

    create_transaction(
        transaction_id=transaction_id,
        cash_amount_paise=cash_amount_paise,
        service_charge_paise=service_charge_paise,
        total_amount_paise=total_amount_paise,
        expires_at=expires_at,
        payment_provider=PAYMENT_PROVIDER
    )

    return {
        "success": True,
        "transaction_id": transaction_id,
        "cash_amount": paise_to_rupees(cash_amount_paise),
        "service_charge": paise_to_rupees(service_charge_paise),
        "total": paise_to_rupees(total_amount_paise),
        "currency": "INR",
        "status": "payment_pending",
        "expires_in": 60
    }


# =========================
# PAYMENT STATUS
# =========================

@app.get("/api/payment/status/{transaction_id}")
def payment_status(transaction_id: str):

    transaction = get_transaction(transaction_id)

    if transaction is None:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found"
        )

    return {
        "success": True,
        "transaction_id": transaction["transaction_id"],
        "cash_amount": paise_to_rupees(
            transaction["cash_amount_paise"]
        ),
        "service_charge": paise_to_rupees(
            transaction["service_charge_paise"]
        ),
        "total": paise_to_rupees(
            transaction["total_amount_paise"]
        ),
        "currency": transaction["currency"],
        "payment_status": transaction["status"],
        "cash_status": (
            "dispensed"
            if transaction["cash_dispensed"]
            else "locked"
        )
    }


# =========================
# CREATE PAYMENT QR
# =========================

@app.post("/api/payment/create-qr")
def create_payment_qr(request: WithdrawalRequest):

    if request.amount not in ALLOWED_AMOUNTS:
        raise HTTPException(
            status_code=400,
            detail="Invalid withdrawal amount"
        )

    (
        cash_amount_paise,
        service_charge_paise,
        total_amount_paise
    ) = calculate_payment(request.amount)

    transaction_id = generate_transaction_id()

    expires_at = (
        datetime.now() +
        timedelta(seconds=60)
    ).isoformat()


    # =========================
    # DEMO MODE
    # =========================

    if razorpay_client is None:

        create_transaction(
            transaction_id=transaction_id,
            cash_amount_paise=cash_amount_paise,
            service_charge_paise=service_charge_paise,
            total_amount_paise=total_amount_paise,
            expires_at=expires_at,
            payment_provider="demo"
        )

        return {
            "success": True,
            "mode": "demo",
            "transaction_id": transaction_id,
            "cash_amount": paise_to_rupees(
                cash_amount_paise
            ),
            "service_charge": paise_to_rupees(
                service_charge_paise
            ),
            "total": paise_to_rupees(
                total_amount_paise
            ),
            "currency": "INR",
            "payment_status": "payment_pending",
            "qr_image_url": None,
            "message": "Payment provider is not configured yet"
        }


    # =========================
    # LIVE RAZORPAY QR
    # =========================

    qr_data = {
        "type": "upi_qr",
        "name": "CASHGO",
        "usage": "single_use",
        "fixed_amount": True,
        "payment_amount": total_amount_paise,
        "description": f"CASHGO {transaction_id}",
        "notes": {
            "transaction_id": transaction_id,
            "cash_amount": str(request.amount)
        }
    }

    try:

        qr = razorpay_client.qr_code.create(
            data=qr_data
        )

    except Exception as error:

        print("RAZORPAY QR ERROR:", error)

        raise HTTPException(
            status_code=500,
            detail="Unable to create payment QR"
        )


    qr_id = qr.get("id")

    create_transaction(
        transaction_id=transaction_id,
        cash_amount_paise=cash_amount_paise,
        service_charge_paise=service_charge_paise,
        total_amount_paise=total_amount_paise,
        expires_at=expires_at,
        payment_provider="razorpay",
        qr_id=qr_id
    )


    return {
        "success": True,
        "mode": "live",
        "transaction_id": transaction_id,
        "cash_amount": paise_to_rupees(
            cash_amount_paise
        ),
        "service_charge": paise_to_rupees(
            service_charge_paise
        ),
        "total": paise_to_rupees(
            total_amount_paise
        ),
        "currency": "INR",
        "payment_status": "payment_pending",
        "qr_id": qr_id,
        "qr_image_url": qr.get("image_url")
    }


@app.post("/api/payment/demo-success/{transaction_id}")
def demo_payment_success(transaction_id: str):

    transaction = get_transaction(transaction_id)

    if transaction is None:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found"
        )

    if transaction["status"] == "payment_verified":
        return {
            "success": True,
            "message": "Payment already verified",
            "transaction_id": transaction_id,
            "payment_status": "payment_verified"
        }

    if transaction["cash_dispensed"]:
        raise HTTPException(
            status_code=400,
            detail="Cash already dispensed"
        )

    update_payment_status(
        transaction_id,
        "payment_verified"
    )

    return {
        "success": True,
        "message": "Demo payment verified successfully",
        "transaction_id": transaction_id,
        "payment_status": "payment_verified"
    }



@app.post("/api/cash/dispense/{transaction_id}")
def dispense(transaction_id: str):

    result = dispense_cash(transaction_id)

    if not result["success"]:
        raise HTTPException(
            status_code=400,
            detail=result["message"]
        )

    return result