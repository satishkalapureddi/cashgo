import { useEffect, useState } from "react";
import axios from "axios";
import {
  ArrowLeft,
  ShieldCheck,
  Wifi,
  QrCode,
  CheckCircle,
  Banknote,
} from "lucide-react";
import "./App.css";

const API_URL = import.meta.env.VITE_API_URL;

const AMOUNTS = [10, 20, 50, 100];
const SERVICE_RATE = 0.099;

function App() {
  const [selectedAmount, setSelectedAmount] = useState(10);
  const [screen, setScreen] = useState("home");

  const [timeLeft, setTimeLeft] = useState(60);

  const [transactionId, setTransactionId] = useState("");

  const [paymentAmount, setPaymentAmount] = useState(0);

  const [paymentStatus, setPaymentStatus] = useState("pending");

  const [qrImageUrl, setQrImageUrl] = useState(null);

  const [dispenseStatus, setDispenseStatus] = useState("idle");

  const [errorMessage, setErrorMessage] = useState("");

  const serviceCharge = selectedAmount * SERVICE_RATE;
  const total = selectedAmount + serviceCharge;


  // =========================================================
  // QR TIMER
  // =========================================================

  useEffect(() => {
    if (screen !== "payment") {
      return;
    }

    if (dispenseStatus !== "idle") {
      return;
    }

    setTimeLeft(60);

    const timer = setInterval(() => {
      setTimeLeft((previous) => {
        if (previous <= 1) {
          clearInterval(timer);
          return 0;
        }

        return previous - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [screen, dispenseStatus]);


  // =========================================================
  // PAYMENT STATUS POLLING
  // =========================================================

  useEffect(() => {
    if (
      screen !== "payment" ||
      !transactionId ||
      dispenseStatus !== "idle"
    ) {
      return;
    }

    const checkPayment = async () => {
      try {
        const response = await axios.get(
          `${API_URL}/api/payment/status/${transactionId}`
        );

        console.log(
          "PAYMENT STATUS:",
          response.data
        );

        if (
          response.data.payment_status ===
          "payment_verified"
        ) {
          setPaymentStatus("verified");
        }

      } catch (error) {
        console.error(
          "PAYMENT STATUS ERROR:",
          error
        );
      }
    };

    checkPayment();

    const pollingTimer = setInterval(
      checkPayment,
      3000
    );

    return () => clearInterval(pollingTimer);

  }, [
    screen,
    transactionId,
    dispenseStatus,
  ]);


  // =========================================================
  // AUTOMATIC CASH DISPENSING
  // =========================================================

  useEffect(() => {
    if (
      paymentStatus !== "verified" ||
      !transactionId ||
      dispenseStatus !== "idle"
    ) {
      return;
    }

    const dispenseCash = async () => {

      try {

        console.log(
          "PAYMENT VERIFIED → DISPENSING CASH"
        );

        setDispenseStatus("dispensing");

        const response = await axios.post(
          `${API_URL}/api/cash/dispense/${transactionId}`
        );

        console.log(
          "DISPENSE RESPONSE:",
          response.data
        );

        if (response.data.success) {

          setDispenseStatus("dispensed");

        } else {

          setDispenseStatus("error");

          setErrorMessage(
            "Unable to dispense cash."
          );
        }

      } catch (error) {

        console.error(
          "CASH DISPENSE ERROR:",
          error
        );

        setDispenseStatus("error");

        setErrorMessage(
          error.response?.data?.detail ||
          "Cash dispensing failed."
        );
      }
    };

    dispenseCash();

  }, [
    paymentStatus,
    transactionId,
    dispenseStatus,
  ]);


  // =========================================================
  // CREATE PAYMENT
  // =========================================================

  const goToPayment = async () => {

    try {

      setErrorMessage("");

      setDispenseStatus("idle");

      const response = await axios.post(
        `${API_URL}/api/payment/create-qr`,
        {
          amount: selectedAmount,
        }
      );

      console.log(
        "CASHGO PAYMENT:",
        response.data
      );

      if (!response.data.success) {

        alert(
          "Unable to create payment."
        );

        return;
      }

      setTransactionId(
        response.data.transaction_id
      );

      setPaymentAmount(
        response.data.total
      );

      setPaymentStatus(
        response.data.payment_status
      );

      setQrImageUrl(
        response.data.qr_image_url
      );

      setTimeLeft(60);

      setScreen("payment");

    } catch (error) {

      console.error(
        "PAYMENT CREATION ERROR:",
        error
      );

      alert(
        "Unable to connect to CASHGO payment server."
      );
    }
  };


  // =========================================================
  // GO BACK
  // =========================================================

  const goBack = () => {

    setScreen("home");

    setTransactionId("");

    setPaymentAmount(0);

    setPaymentStatus("pending");

    setQrImageUrl(null);

    setTimeLeft(60);

    setDispenseStatus("idle");

    setErrorMessage("");
  };


  // =========================================================
  // DEMO PAYMENT
  // =========================================================

  const demoPayment = async () => {

    try {

      setErrorMessage("");

      await axios.post(
        `${API_URL}/api/payment/demo-success/${transactionId}`
      );

    } catch (error) {

      console.error(
        "DEMO PAYMENT ERROR:",
        error
      );

      setErrorMessage(
        error.response?.data?.detail ||
        "Demo payment failed."
      );
    }
  };


  // =========================================================
  // HOME SCREEN
  // =========================================================

  if (screen === "home") {

    return (
      <div className="app">

        <div className="machine">

          <header className="header">

            <div className="brand">

              <div className="brand-name">
                CASHGO
              </div>

              <div className="brand-tagline">
                SMALL CASH • INSTANT ACCESS
              </div>

            </div>

            <div className="status">
              <Wifi size={18} />
              <span>ONLINE</span>
            </div>

          </header>


          <main className="main">

            <div className="welcome">

              <h1>
                GET CASH
              </h1>

              <p>
                Select the amount you need
              </p>

            </div>


            <div className="amount-grid">

              {AMOUNTS.map((amount) => (

                <button
                  key={amount}
                  className={`amount-button ${
                    selectedAmount === amount
                      ? "selected"
                      : ""
                  }`}
                  onClick={() =>
                    setSelectedAmount(amount)
                  }
                >

                  <span>₹</span>

                  {amount}

                </button>

              ))}

            </div>


            <div className="summary">

              <div className="summary-row">

                <span>
                  Cash Amount
                </span>

                <strong>
                  ₹{selectedAmount.toFixed(2)}
                </strong>

              </div>


              <div className="summary-row">

                <span>
                  Service Charge (9.9%)
                </span>

                <strong>
                  ₹{serviceCharge.toFixed(2)}
                </strong>

              </div>


              <div className="summary-divider"></div>


              <div className="summary-row total-row">

                <span>
                  TOTAL PAYMENT
                </span>

                <strong>
                  ₹{total.toFixed(2)}
                </strong>

              </div>

            </div>


            <button
              className="payment-button"
              onClick={goToPayment}
            >
              CONTINUE TO PAYMENT
            </button>


            <div className="security">

              <ShieldCheck size={18} />

              <span>
                Secure UPI Payment
              </span>

            </div>

          </main>


          <footer className="footer">

            <span>
              CASHGO • DIGITAL CASH ACCESS
            </span>

            <span>
              SECURE • FAST • SIMPLE
            </span>

          </footer>

        </div>

      </div>
    );
  }


  // =========================================================
  // PAYMENT SCREEN
  // =========================================================

  return (

    <div className="app">

      <div className="machine">

        <header className="header">

          <div className="brand">

            <div className="brand-name">
              CASHGO
            </div>

            <div className="brand-tagline">
              SMALL CASH • INSTANT ACCESS
            </div>

          </div>

          <div className="status">
            <Wifi size={18} />
            <span>ONLINE</span>
          </div>

        </header>


        <main className="main payment-screen">


          {/* BACK BUTTON */}

          {dispenseStatus === "idle" && (
            <button
              className="back-button"
              onClick={goBack}
            >

              <ArrowLeft size={20} />

              BACK

            </button>
          )}


          {/* PAYMENT TITLE */}

          {dispenseStatus === "idle" && (

            <div className="payment-title">

              <QrCode size={34} />

              <h1>
                SCAN & PAY
              </h1>

              <p>
                Scan the QR code using any UPI app
              </p>

            </div>

          )}


          {/* =================================================
              DISPENSING SCREEN
          ================================================= */}

          {dispenseStatus === "dispensing" && (

            <div className="cash-process-screen">

              <div className="cash-process-icon spinning">

                <Banknote size={48} />

              </div>

              <h1>
                DISPENSING CASH
              </h1>

              <div className="dispense-amount">
                ₹{selectedAmount}
              </div>

              <p>
                Please wait...
              </p>

              <div className="dispense-loader"></div>

            </div>

          )}


          {/* =================================================
              CASH DISPENSED SCREEN
          ================================================= */}

          {dispenseStatus === "dispensed" && (

            <div className="cash-process-screen">

              <div className="cash-process-icon">

                <CheckCircle size={55} />

              </div>

              <h1>
                COLLECT YOUR CASH
              </h1>

              <div className="dispense-amount">
                ₹{selectedAmount}
              </div>

              <p>
                Transaction completed successfully.
              </p>

              <button
                className="payment-button"
                onClick={goBack}
              >
                DONE
              </button>

            </div>

          )}


          {/* =================================================
              ERROR SCREEN
          ================================================= */}

          {dispenseStatus === "error" && (

            <div className="cash-process-screen">

              <div className="cash-process-icon error-icon">
                !
              </div>

              <h1>
                DISPENSING FAILED
              </h1>

              <p>
                {errorMessage}
              </p>

              <button
                className="payment-button"
                onClick={goBack}
              >
                RETURN TO HOME
              </button>

            </div>

          )}


          {/* =================================================
              PAYMENT CARD
          ================================================= */}

          {dispenseStatus === "idle" && (

            <>

              <div className="payment-card">

                <div className="payment-amount">

                  ₹{paymentAmount.toFixed(2)}

                </div>


                <div className="transaction-id">

                  TRANSACTION: {transactionId}

                </div>


                <div className="qr-container">

                  {qrImageUrl ? (

                    <img
                      src={qrImageUrl}
                      alt="CASHGO UPI QR"
                      className="qr-image"
                    />

                  ) : (

                    <div className="qr-placeholder">

                      <QrCode
                        size={150}
                        strokeWidth={1.5}
                      />

                      <span>
                        DEMO MODE
                      </span>

                    </div>

                  )}

                </div>


                <div className="timer">

                  QR EXPIRES IN

                  <strong>

                    00:
                    {timeLeft
                      .toString()
                      .padStart(2, "0")}

                  </strong>

                </div>


                {/* DEMO PAYMENT BUTTON */}

                {paymentStatus !== "verified" &&
                  timeLeft > 0 && (

                    <button
                      className="demo-payment-button"
                      onClick={demoPayment}
                    >
                      DEMO: MARK PAYMENT AS PAID
                    </button>

                  )}


                {/* VERIFIED */}

                {paymentStatus === "verified" ? (

                  <div className="payment-success">

                    <div className="success-icon">
                      ✓
                    </div>

                    <strong>
                      PAYMENT VERIFIED
                    </strong>

                    <span>
                      Preparing your cash...
                    </span>

                  </div>

                ) : timeLeft > 0 ? (

                  <div className="waiting">

                    <div className="loading-dot"></div>

                    WAITING FOR PAYMENT...

                  </div>

                ) : (

                  <div className="expired">
                    QR CODE EXPIRED
                  </div>

                )}

              </div>


              <div className="payment-info">

                <ShieldCheck size={18} />

                <span>
                  Payment must be completed before
                  cash is dispensed.
                </span>

              </div>

            </>

          )}

        </main>


        <footer className="footer">

          <span>
            CASHGO • DIGITAL CASH ACCESS
          </span>

          <span>
            SECURE • FAST • SIMPLE
          </span>

        </footer>

      </div>

    </div>

  );
}

export default App;